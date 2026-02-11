"""
Excepciones personalizadas del sistema
"""


class ClockControlError(Exception):
    """Excepción base para todos los errores del sistema"""
    pass


class DeviceConnectionError(ClockControlError):
    """Error al conectar con dispositivo ZKTeco"""
    pass


class DatabaseError(ClockControlError):
    """Error en operaciones de base de datos"""
    pass


class ConfigurationError(ClockControlError):
    """Error en configuración del sistema"""
    pass


class ValidationError(ClockControlError):
    """Error de validación de datos"""
    pass
