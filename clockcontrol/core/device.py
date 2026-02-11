"""
Gestión de dispositivos ZKTeco
"""
import logging
import os
import platform
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Generator, List, Optional

from clockcontrol.core.exceptions import DeviceConnectionError

# Intentar importar pyzk
try:
    from zk import ZK
except ImportError:
    ZK = None

logger = logging.getLogger(__name__)


@dataclass
class DeviceInfo:
    """Información del dispositivo ZK"""
    ip: str
    mac: str = ""
    serial: str = ""
    platform: str = ""


class ZKDeviceManager:
    """
    Gestiona la conexión y comunicación con dispositivos ZKTeco.
    
    Ejemplo de uso:
        manager = ZKDeviceManager("192.168.1.201")
        
        if manager.is_reachable():
            with manager.connect() as conn:
                attendances = manager.get_attendance(conn)
    """
    
    def __init__(
        self,
        ip: str,
        port: int = 4370,
        timeout: int = 10,
        password: int = 0,
        force_udp: bool = False,
    ):
        if ZK is None:
            raise DeviceConnectionError(
                "Biblioteca pyzk no instalada. Ejecutar: pip install pyzk"
            )
        
        self.ip = ip
        self.port = port
        self.timeout = timeout
        self.password = password
        self.force_udp = force_udp
        self._zk = ZK(
            ip,
            port=port,
            timeout=timeout,
            password=password,
            force_udp=force_udp,
        )
    
    def is_reachable(self, attempts: int = 2) -> bool:
        """
        Verifica si el dispositivo es alcanzable vía ping.
        
        Args:
            attempts: Número de intentos de ping
            
        Returns:
            True si hay respuesta, False en caso contrario
        """
        param = "-n" if platform.system().lower() == "windows" else "-c"
        filter_cmd = (
            ' | findstr /i "TTL"'
            if platform.system().lower() == "windows"
            else ' | grep "ttl"'
        )
        silent = (
            " > NUL 2>&1"
            if platform.system().lower() == "windows"
            else " >/dev/null 2>&1"
        )
        
        command = f"ping {param} {attempts} {self.ip}{filter_cmd}{silent}"
        result = os.system(command)
        
        reachable = result == 0
        logger.info(
            f"Ping a {self.ip}: {'OK' if reachable else 'FALLIDO'}"
        )
        return reachable
    
    @contextmanager
    def connect(self) -> Generator[Any, None, None]:
        """
        Context manager para conexión con el dispositivo.
        
        Yields:
            Conexión activa al dispositivo ZK
            
        Raises:
            DeviceConnectionError: Si no se puede conectar
            
        Ejemplo:
            with manager.connect() as conn:
                data = conn.get_attendance()
        """
        conn = None
        try:
            logger.info(f"Conectando a {self.ip}:{self.port}...")
            conn = self._zk.connect()
            logger.info(f"Conexión exitosa a {self.ip}")
            yield conn
            
        except Exception as e:
            logger.error(f"Error conectando a {self.ip}: {e}")
            raise DeviceConnectionError(
                f"No se pudo conectar a {self.ip}:{self.port} - {e}"
            )
        finally:
            if conn:
                try:
                    conn.disconnect()
                    logger.debug(f"Desconectado de {self.ip}")
                except Exception:
                    pass
    
    def get_device_info(self, conn: Any) -> DeviceInfo:
        """
        Obtiene información del dispositivo.
        
        Args:
            conn: Conexión activa al dispositivo
            
        Returns:
            DeviceInfo con datos del dispositivo
        """
        try:
            network = conn.get_network_params()
            return DeviceInfo(
                ip=network.get("ip", self.ip),
                mac=network.get("mac", ""),
            )
        except Exception as e:
            logger.warning(f"No se pudo obtener info del dispositivo: {e}")
            return DeviceInfo(ip=self.ip)
    
    def get_attendance(self, conn: Any) -> List[Any]:
        """
        Obtiene los marcajes de asistencia del dispositivo.
        
        Args:
            conn: Conexión activa al dispositivo
            
        Returns:
            Lista de objetos de asistencia
        """
        try:
            logger.info(f"Obteniendo marcajes de {self.ip}...")
            attendances = conn.get_attendance()
            count = len(attendances) if attendances else 0
            logger.info(f"Marcajes obtenidos de {self.ip}: {count}")
            return attendances if attendances else []
        except Exception as e:
            logger.error(f"Error obteniendo marcajes de {self.ip}: {e}")
            return []
