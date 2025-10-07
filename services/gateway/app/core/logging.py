"""
Configuración de logging estructurado para el Gateway.
"""
import logging
import sys


def setup_logging():
    """
    Configura logging estructurado con JSON si python-json-logger está disponible.
    Fallback a formato key=value si no está disponible.
    """
    try:
        from pythonjsonlogger import jsonlogger  # type: ignore
        
        class CustomJsonFormatter(jsonlogger.JsonFormatter):
            """Formatter JSON personalizado."""
            
            def add_fields(self, log_record, record, message_dict):
                super().add_fields(log_record, record, message_dict)
                
                # Agregar campos estándar
                log_record["levelname"] = record.levelname
                log_record["name"] = record.name
                log_record["message"] = record.getMessage()
        
        # Handler con JSON
        handler = logging.StreamHandler(sys.stdout)
        formatter = CustomJsonFormatter("%(levelname)s %(name)s %(message)s")
        handler.setFormatter(formatter)
        
    except ImportError:
        # Fallback: formato key=value
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "%(levelname)s %(name)s %(message)s"
        )
        handler.setFormatter(formatter)
    
    # Configurar root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    
    # Silenciar logs muy verbosos
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
