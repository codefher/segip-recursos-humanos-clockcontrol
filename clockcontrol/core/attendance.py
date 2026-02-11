"""
Procesamiento de marcajes de asistencia
"""
import json
import logging
from dataclasses import dataclass, asdict
from datetime import date, datetime, timedelta
from typing import Any, List, Optional

from clockcontrol.core.exceptions import ValidationError

logger = logging.getLogger(__name__)


@dataclass
class AttendanceMark:
    """Representa un marcaje de asistencia"""
    carnet: str
    date_mark: str
    time_mark: str
    ip_clock: str
    id_reloj_bio: int
    
    def to_db_dict(self) -> dict:
        """Convierte a diccionario para DB (con prefijo 'in')"""
        return {
            "incarnet": self.carnet,
            "indate_mark": self.date_mark,
            "intime_mark": self.time_mark,
            "inip_clock": self.ip_clock,
            "inid_reloj_bio": self.id_reloj_bio,
        }


class AttendanceProcessor:
    """
    Procesa y filtra marcajes de asistencia.
    
    Ejemplo de uso:
        processor = AttendanceProcessor(days_back=1)
        marks = processor.process(raw_attendances, "192.168.1.1", 42)
    """
    
    def __init__(self, days_back: int = 1):
        """
        Args:
            days_back: Días hacia atrás para filtrar (default 1 = ayer y hoy)
        """
        self.days_back = days_back
    
    def process(
        self,
        raw_attendances: List[Any],
        ip_clock: str,
        clock_id: int,
    ) -> List[AttendanceMark]:
        """
        Procesa marcajes crudos del dispositivo ZK.
        
        Args:
            raw_attendances: Lista de objetos de asistencia del dispositivo
            ip_clock: IP del reloj
            clock_id: ID del reloj en la base de datos
            
        Returns:
            Lista de AttendanceMark filtrados y procesados
        """
        if not raw_attendances:
            logger.info("No hay marcajes para procesar")
            return []
        
        today = date.today()
        start_date = today - timedelta(days=self.days_back)
        
        processed = []
        for attendance in raw_attendances:
            if attendance is None:
                continue
            
            try:
                mark = self._parse_attendance(attendance, ip_clock, clock_id)
                if mark and self._is_in_date_range(mark.date_mark, start_date, today):
                    processed.append(mark)
            except Exception as e:
                logger.warning(f"Error procesando marcaje: {e}")
                continue
        
        logger.info(
            f"Marcajes procesados: {len(processed)} de {len(raw_attendances)}"
        )
        return processed
    
    def _parse_attendance(
        self,
        attendance: Any,
        ip_clock: str,
        clock_id: int,
    ) -> Optional[AttendanceMark]:
        """
        Parsea un objeto de asistencia del dispositivo ZK.
        
        El formato esperado de str(attendance) es:
        "Attendance <carnet> : <YYYY-MM-DD> <HH:MM:SS> <status>"
        """
        try:
            data_str = str(attendance)
            parts = data_str.split()
            
            if len(parts) < 5:
                logger.warning(f"Formato de marcaje inválido: {data_str}")
                return None
            
            return AttendanceMark(
                carnet=parts[1],
                date_mark=parts[3],
                time_mark=parts[4],
                ip_clock=ip_clock,
                id_reloj_bio=clock_id,
            )
        except Exception as e:
            logger.error(f"Error parseando marcaje: {e}")
            return None
    
    def _is_in_date_range(
        self,
        date_str: str,
        start_date: date,
        end_date: date,
    ) -> bool:
        """Verifica si la fecha está en el rango permitido"""
        try:
            mark_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            return start_date <= mark_date <= end_date
        except ValueError:
            logger.warning(f"Fecha inválida: {date_str}")
            return False
    
    @staticmethod
    def to_json(marks: List[AttendanceMark]) -> str:
        """
        Convierte lista de marcajes a JSON para stored procedure.
        
        Args:
            marks: Lista de AttendanceMark
            
        Returns:
            String JSON formateado
        """
        data = [mark.to_db_dict() for mark in marks]
        return json.dumps(data, sort_keys=True, indent=2)
