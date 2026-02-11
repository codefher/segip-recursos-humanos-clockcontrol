"""
Modelos de datos
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Clock:
    """Modelo de reloj biométrico"""
    id: int
    ip: str
    port: int
    password: int
    active: bool = True
    name: Optional[str] = None
    location: Optional[str] = None
    
    @classmethod
    def from_db_row(cls, row: tuple) -> "Clock":
        """
        Crea instancia desde fila de base de datos.
        
        La estructura de rrhh.reloj_biometrico:
        - row[0]: id
        - row[4]: ip_reloj
        - row[6]: password
        - row[12]: puerto
        """
        return cls(
            id=row[0],
            ip=row[4],
            port=row[12] if len(row) > 12 else 4370,
            password=row[6] if len(row) > 6 else 0,
            active=True,
        )


@dataclass
class ConnectionLog:
    """Modelo de log de conexión"""
    ip_clock: str
    available: bool
    observation: str
    timestamp: Optional[datetime] = None
