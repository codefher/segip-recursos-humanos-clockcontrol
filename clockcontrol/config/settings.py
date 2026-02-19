"""
Configuración centralizada del sistema
"""
import logging
import os
from configparser import ConfigParser
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional

from clockcontrol.core.exceptions import ConfigurationError


@dataclass
class DatabaseConfig:
    """Configuración de base de datos"""
    host: str
    port: int
    database: str
    user: str
    password: str

    def to_dict(self) -> dict:
        """Convierte a diccionario para psycopg2"""
        return {
            "host": self.host,
            "port": self.port,
            "database": self.database,
            "user": self.user,
            "password": self.password,
        }


@dataclass
class LoggingConfig:
    """Configuración de logging"""
    level: str = "INFO"
    file: str = "clockcontrol.log"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


@dataclass
class DeviceConfig:
    """Configuración por defecto de dispositivos ZK"""
    default_port: int = 4370
    default_timeout: int = 10
    default_password: str = "0"
    ping_attempts: int = 2


class Settings:
    """Configuración principal del sistema"""
    
    def __init__(
        self,
        config_file: str = "database.ini",
        section: str = "postgresql"
    ):
        self.config_file = self._find_config_file(config_file)
        self.section = section
        self._db_config: Optional[DatabaseConfig] = None
        self.logging = LoggingConfig()
        self.device = DeviceConfig()
        
        # Configurar logging
        self._setup_logging()
    
    def _find_config_file(self, filename: str) -> Path:
        """Busca el archivo de configuración en rutas posibles"""
        possible_paths = [
            Path(filename),
            Path(__file__).parent.parent.parent / filename,
            Path(__file__).parent.parent.parent / "config" / filename,
            Path.cwd() / filename,
        ]
        
        for path in possible_paths:
            if path.exists():
                return path
        
        raise ConfigurationError(
            f"Archivo de configuración '{filename}' no encontrado. "
            f"Crear desde 'tmp.database.ini'"
        )
    
    def _setup_logging(self) -> None:
        """Configura el sistema de logging con rotacion de archivos"""
        from logging.handlers import RotatingFileHandler

        logging.basicConfig(
            level=getattr(logging, self.logging.level),
            format=self.logging.format,
            handlers=[
                RotatingFileHandler(
                    self.logging.file,
                    maxBytes=10 * 1024 * 1024,  # 10 MB
                    backupCount=5,
                ),
            ],
        )
    
    @property
    def database(self) -> DatabaseConfig:
        """Obtiene la configuración de base de datos (lazy loading)"""
        if self._db_config is None:
            self._db_config = self._load_database_config()
        return self._db_config
    
    def _load_database_config(self) -> DatabaseConfig:
        """Carga la configuración de base de datos desde el archivo"""
        parser = ConfigParser()
        parser.read(self.config_file)
        
        if not parser.has_section(self.section):
            raise ConfigurationError(
                f"Sección '{self.section}' no encontrada en {self.config_file}"
            )
        
        try:
            return DatabaseConfig(
                host=parser.get(self.section, "host"),
                port=parser.getint(self.section, "port", fallback=5432),
                database=parser.get(self.section, "database"),
                user=parser.get(self.section, "user"),
                password=parser.get(self.section, "password"),
            )
        except Exception as e:
            raise ConfigurationError(f"Error leyendo configuración: {e}")


@lru_cache()
def get_settings() -> Settings:
    """Obtiene instancia singleton de Settings"""
    return Settings()
