"""
Repositorios - Patrón Repository para acceso a datos
"""
import logging
from typing import List, Optional

from clockcontrol.database.connection import DatabaseConnection
from clockcontrol.database.models import Clock, ConnectionLog
from clockcontrol.core.attendance import AttendanceMark

logger = logging.getLogger(__name__)


class ClockRepository:
    """
    Repositorio para operaciones con relojes biométricos.
    
    Ejemplo:
        repo = ClockRepository(db_connection)
        clock = repo.get_by_ip("192.168.1.201")
        all_clocks = repo.get_all_active()
    """
    
    def __init__(self, db: DatabaseConnection):
        self.db = db
    
    def get_by_ip(self, ip: str) -> Optional[Clock]:
        """
        Obtiene un reloj por su IP.
        
        Args:
            ip: Dirección IP del reloj
            
        Returns:
            Clock si existe y está activo, None en caso contrario
        """
        with self.db.get_cursor() as cur:
            query = """
                SELECT * FROM rrhh.reloj_biometrico 
                WHERE activo = %s AND ip_reloj = %s
            """
            cur.execute(query, (1, ip))
            row = cur.fetchone()
            
            if row:
                logger.info(f"Reloj encontrado: {ip}")
                return Clock.from_db_row(row)
            
            logger.warning(f"Reloj no encontrado o inactivo: {ip}")
            return None
    
    def get_all_active(self) -> List[Clock]:
        """
        Obtiene todos los relojes activos.
        
        Returns:
            Lista de Clock activos
        """
        with self.db.get_cursor() as cur:
            query = "SELECT * FROM rrhh.reloj_biometrico WHERE activo = 1"
            cur.execute(query)
            rows = cur.fetchall()
            
            clocks = [Clock.from_db_row(row) for row in rows]
            logger.info(f"Relojes activos encontrados: {len(clocks)}")
            return clocks


class AttendanceRepository:
    """
    Repositorio para operaciones con marcajes de asistencia.
    
    Ejemplo:
        repo = AttendanceRepository(db_connection)
        repo.log_connection("192.168.1.1", True, "Conexión exitosa")
        saved = repo.save_marks(marks_json)
    """
    
    def __init__(self, db: DatabaseConnection):
        self.db = db
    
    def log_connection(
        self,
        ip: str,
        available: bool,
        observation: str,
    ) -> None:
        """
        Registra un intento de conexión a un reloj.
        
        Args:
            ip: IP del reloj
            available: True si la conexión fue exitosa
            observation: Descripción del resultado
        """
        with self.db.get_cursor() as cur:
            query = """
                INSERT INTO rrhh.clock_conn (ip_clock, available, obs) 
                VALUES (%s, %s, %s)
            """
            cur.execute(query, (ip, available, observation[:255]))
            logger.debug(f"Log de conexión: {ip} - {'OK' if available else 'FAIL'}")
    
    def save_marks(self, marks_json: str) -> int:
        """
        Guarda marcajes usando el stored procedure.
        
        Args:
            marks_json: JSON con los marcajes
            
        Returns:
            Cantidad de registros insertados
        """
        with self.db.get_cursor() as cur:
            # El stored procedure espera: (id_in, obj_marks)
            # id_in parece ser fijo en 4570 según código original
            cur.callproc("rrhh.set_attendance_info_clock", ([4570, marks_json],))
            result = cur.fetchone()
            
            if result:
                inserted = result[2] if len(result) > 2 else 0
                logger.info(f"Marcajes guardados: {inserted} nuevos")
                return inserted
            
            return 0
