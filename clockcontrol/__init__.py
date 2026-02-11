"""
clockControl - Sistema de Control de Asistencia SEGIP

Sistema para obtener marcajes de relojes biométricos ZKTeco y 
almacenarlos en base de datos PostgreSQL.
"""

__version__ = "2.0.0"
__author__ = "SEGIP"

# API pública del paquete
from clockcontrol.core.attendance import AttendanceProcessor, AttendanceMark
from clockcontrol.core.device import ZKDeviceManager
from clockcontrol.core.exceptions import (
    ClockControlError,
    DeviceConnectionError,
    DatabaseError,
    ConfigurationError,
)
from clockcontrol.database.connection import DatabaseConnection
from clockcontrol.database.repositories import ClockRepository, AttendanceRepository
from clockcontrol.config.settings import Settings, get_settings
from clockcontrol.cli import ClockControlApp

__all__ = [
    # Version
    "__version__",
    # Core
    "AttendanceProcessor",
    "AttendanceMark",
    "ZKDeviceManager",
    # Exceptions
    "ClockControlError",
    "DeviceConnectionError",
    "DatabaseError",
    "ConfigurationError",
    # Database
    "DatabaseConnection",
    "ClockRepository",
    "AttendanceRepository",
    # Config
    "Settings",
    "get_settings",
    # App
    "ClockControlApp",
]
