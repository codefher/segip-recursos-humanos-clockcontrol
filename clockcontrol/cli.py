"""
Interface de línea de comandos para clockControl
"""
import logging
import sys
import time
from dataclasses import dataclass
from typing import List, Optional

from clockcontrol.config.settings import Settings, get_settings
from clockcontrol.core.attendance import AttendanceProcessor, AttendanceMark
from clockcontrol.core.device import ZKDeviceManager
from clockcontrol.core.exceptions import (
    ClockControlError,
    ConfigurationError,
    DeviceConnectionError,
)
from clockcontrol.database.connection import DatabaseConnection
from clockcontrol.database.repositories import ClockRepository, AttendanceRepository
from clockcontrol.database.models import Clock

logger = logging.getLogger(__name__)


@dataclass
class ProcessResult:
    """Resultado del procesamiento de un reloj"""
    clock_ip: str
    success: bool
    marks_processed: int = 0
    marks_saved: int = 0
    error: Optional[str] = None
    elapsed_time: float = 0.0


class ClockControlApp:
    """
    Aplicación principal de clockControl.
    
    Orquesta el flujo de obtención de marcajes desde relojes biométricos.
    """
    
    def __init__(self, settings: Optional[Settings] = None):
        """
        Args:
            settings: Configuración de la aplicación (usa default si no se provee)
        """
        self.settings = settings or get_settings()
        self.db = DatabaseConnection(self.settings.database.to_dict())
        self.clock_repo = ClockRepository(self.db)
        self.attendance_repo = AttendanceRepository(self.db)
        self.processor = AttendanceProcessor(days_back=1)
    
    def initialize(self) -> None:
        """Inicializa la aplicación (crea tablas si no existen)"""
        logger.info("Inicializando clockControl...")
        self.db.ensure_tables_exist()
        logger.info("Inicialización completada")
    
    def process_single_clock(
        self,
        ip: str,
        port: int = 4370,
        password: int = 0,
    ) -> ProcessResult:
        """
        Procesa marcajes de un solo reloj.
        
        Args:
            ip: IP del reloj
            port: Puerto del reloj
            password: Contraseña del reloj
            
        Returns:
            ProcessResult con el resultado del procesamiento
        """
        start_time = time.time()
        result = ProcessResult(clock_ip=ip, success=False)
        
        try:
            # Verificar que el reloj existe en DB
            clock = self.clock_repo.get_by_ip(ip)
            if not clock:
                result.error = f"Reloj {ip} no encontrado o inactivo en DB"
                self.attendance_repo.log_connection(ip, False, result.error)
                return result
            
            # Verificar conectividad
            device = ZKDeviceManager(ip, port=port, password=password)
            if not device.is_reachable():
                result.error = "Sin respuesta a ping"
                self.attendance_repo.log_connection(ip, False, result.error)
                return result
            
            self.attendance_repo.log_connection(ip, True, "Ping exitoso")
            
            # Conectar y obtener marcajes
            with device.connect() as conn:
                device_info = device.get_device_info(conn)
                raw_attendances = device.get_attendance(conn)
                
                if not raw_attendances:
                    result.success = True
                    result.elapsed_time = time.time() - start_time
                    return result
                
                # Procesar marcajes
                marks = self.processor.process(
                    raw_attendances,
                    device_info.ip,
                    clock.id,
                )
                result.marks_processed = len(marks)
                
                # Guardar en DB
                if marks:
                    json_data = AttendanceProcessor.to_json(marks)
                    result.marks_saved = self.attendance_repo.save_marks(json_data)
                
                result.success = True
                
        except DeviceConnectionError as e:
            result.error = str(e)
            self.attendance_repo.log_connection(ip, False, str(e)[:255])
        except ClockControlError as e:
            result.error = str(e)
            logger.error(f"Error procesando {ip}: {e}")
        except Exception as e:
            result.error = f"Error inesperado: {e}"
            logger.exception(f"Error inesperado procesando {ip}")
        
        result.elapsed_time = time.time() - start_time
        return result
    
    def process_all_clocks(self) -> List[ProcessResult]:
        """
        Procesa marcajes de todos los relojes activos.
        
        Returns:
            Lista de ProcessResult con resultados de cada reloj
        """
        clocks = self.clock_repo.get_all_active()
        
        if not clocks:
            logger.warning("No hay relojes activos configurados")
            return []
        
        logger.info(f"Procesando {len(clocks)} relojes activos")
        results = []
        
        for i, clock in enumerate(clocks, 1):
            logger.info(f"[{i}/{len(clocks)}] Procesando reloj: {clock.ip}")
            result = self.process_single_clock(
                ip=clock.ip,
                port=clock.port,
                password=clock.password,
            )
            results.append(result)
        
        return results


def print_banner() -> None:
    """Imprime banner de la aplicación"""
    print("\n" + "=" * 60)
    print("  clockControl - Sistema de Control de Asistencia SEGIP")
    print("=" * 60 + "\n")


def print_result(result: ProcessResult) -> None:
    """Imprime resultado de procesamiento"""
    status = "✓" if result.success else "✗"
    print(f"  [{status}] {result.clock_ip}")
    print(f"      Marcajes procesados: {result.marks_processed}")
    print(f"      Marcajes guardados:  {result.marks_saved}")
    print(f"      Tiempo: {result.elapsed_time:.2f}s")
    if result.error:
        print(f"      Error: {result.error}")


def print_summary(results: List[ProcessResult]) -> None:
    """Imprime resumen de procesamiento"""
    successful = sum(1 for r in results if r.success)
    total_processed = sum(r.marks_processed for r in results)
    total_saved = sum(r.marks_saved for r in results)
    total_time = sum(r.elapsed_time for r in results)
    
    print("\n" + "=" * 60)
    print("  RESUMEN")
    print("=" * 60)
    print(f"  Relojes procesados: {successful}/{len(results)}")
    print(f"  Marcajes procesados: {total_processed}")
    print(f"  Marcajes guardados: {total_saved}")
    print(f"  Tiempo total: {total_time:.2f}s")
    print("=" * 60 + "\n")


def run_single(ip: str, port: int = 4370, password: int = 0) -> int:
    """
    Ejecuta modo individual (un solo reloj).
    
    Returns:
        Código de salida (0=éxito, 1=error)
    """
    print_banner()
    print(f"  Modo: Individual")
    print(f"  Reloj: {ip}:{port}")
    print()
    
    try:
        app = ClockControlApp()
        app.initialize()
        result = app.process_single_clock(ip, port, password)
        
        print_result(result)
        return 0 if result.success else 1
        
    except ConfigurationError as e:
        print(f"\n  ✗ Error de configuración: {e}")
        return 1
    except Exception as e:
        print(f"\n  ✗ Error: {e}")
        logger.exception("Error en modo individual")
        return 1


def run_all() -> int:
    """
    Ejecuta modo masivo (todos los relojes).
    
    Returns:
        Código de salida (0=éxito, 1=error parcial, 2=error total)
    """
    print_banner()
    print(f"  Modo: Masivo (todos los relojes)")
    print()
    
    try:
        app = ClockControlApp()
        app.initialize()
        results = app.process_all_clocks()
        
        if not results:
            print("  No hay relojes activos para procesar")
            return 0
        
        for result in results:
            print_result(result)
        
        print_summary(results)
        
        successful = sum(1 for r in results if r.success)
        if successful == len(results):
            return 0
        elif successful > 0:
            return 1
        else:
            return 2
        
    except ConfigurationError as e:
        print(f"\n  ✗ Error de configuración: {e}")
        return 1
    except Exception as e:
        print(f"\n  ✗ Error: {e}")
        logger.exception("Error en modo masivo")
        return 2


def main() -> None:
    """Entry point principal con argumentos CLI"""
    import argparse
    
    parser = argparse.ArgumentParser(
        prog="clockcontrol",
        description="Sistema de Control de Asistencia - SEGIP",
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Comandos disponibles")
    
    # Comando: single
    single_parser = subparsers.add_parser(
        "single",
        help="Obtener marcajes de un solo reloj",
    )
    single_parser.add_argument(
        "-a", "--address",
        required=True,
        help="IP del reloj biométrico",
    )
    single_parser.add_argument(
        "-p", "--port",
        type=int,
        default=4370,
        help="Puerto del reloj (default: 4370)",
    )
    single_parser.add_argument(
        "-P", "--password",
        type=int,
        default=0,
        help="Contraseña del reloj (default: 0)",
    )
    
    # Comando: all
    subparsers.add_parser(
        "all",
        help="Obtener marcajes de todos los relojes activos",
    )
    
    args = parser.parse_args()
    
    if args.command == "single":
        sys.exit(run_single(args.address, args.port, args.password))
    elif args.command == "all":
        sys.exit(run_all())
    else:
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
