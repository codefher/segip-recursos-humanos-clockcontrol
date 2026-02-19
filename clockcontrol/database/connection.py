"""
Gestión de conexiones a base de datos
"""
import logging
from contextlib import contextmanager
from typing import Any, Generator

import psycopg2

from clockcontrol.core.exceptions import DatabaseError

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """
    Gestor de conexiones a PostgreSQL.
    
    Ejemplo de uso:
        db = DatabaseConnection(config.database.to_dict())
        
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM tabla")
    """
    
    def __init__(self, params: dict):
        """
        Args:
            params: Diccionario con parámetros de conexión
                   (host, port, database, user, password)
        """
        self.params = params
    
    @contextmanager
    def get_connection(self) -> Generator[Any, None, None]:
        """
        Context manager para obtener una conexión.
        
        Yields:
            Conexión a PostgreSQL
            
        Raises:
            DatabaseError: Si hay error de conexión
        """
        conn = None
        try:
            conn = psycopg2.connect(**self.params)
            logger.debug("Conexión a base de datos establecida")
            yield conn
            conn.commit()
        except psycopg2.Error as e:
            if conn:
                conn.rollback()
            logger.error(f"Error de base de datos: {e}")
            raise DatabaseError(f"Error de base de datos: {e}") from e
        finally:
            if conn:
                conn.close()
                logger.debug("Conexión a base de datos cerrada")
    
    @contextmanager
    def get_cursor(self) -> Generator[Any, None, None]:
        """
        Context manager para obtener cursor directamente.
        
        Yields:
            Cursor de PostgreSQL
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                yield cur
    
    def ensure_tables_exist(self) -> None:
        """Verifica que las tablas necesarias existan"""
        with self.get_cursor() as cur:
            cur.execute("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'rrhh'
                  AND table_name IN ('person_marks', 'clock_conn')
            """)
            existing = {row[0] for row in cur.fetchall()}

            missing = {'person_marks', 'clock_conn'} - existing
            if missing:
                logger.warning(
                    f"Tablas faltantes en esquema rrhh: {missing}. "
                    "Contacte al DBA para crearlas."
                )
            else:
                logger.info("Tablas verificadas correctamente")


def get_connection(params: dict) -> DatabaseConnection:
    """Factory function para crear DatabaseConnection"""
    return DatabaseConnection(params)
