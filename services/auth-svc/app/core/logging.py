# services/auth-svc/app/core/logging.py
import logging
import os
from logging.config import dictConfig

def setup_logging():
    use_json = True
    try:
        import pythonjsonlogger  # noqa: F401
    except Exception:
        use_json = False

    handlers = {
        "default": {
            "class": "logging.StreamHandler",
            "level": os.getenv("LOG_LEVEL", "INFO").upper(),
        }
    }

    if use_json:
        handlers["default"]["formatter"] = "json"
        formatters = {
            "json": {
                "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
                "fmt": "%(levelname)s %(name)s %(message)s %(asctime)s %(process)d",
            }
        }
    else:
        handlers["default"]["formatter"] = "kv"
        formatters = {
            "kv": {
                "format": "%(levelname)s name=%(name)s msg=%(message)s time=%(asctime)s pid=%(process)d"
            }
        }

    dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "handlers": handlers,
        "formatters": formatters,
        "root": {"level": os.getenv("LOG_LEVEL", "INFO").upper(), "handlers": ["default"]},
    })

def client_ip_from_scope(scope) -> str:
    """Extrae la IP del cliente desde el scope de ASGI"""
    client = scope.get("client")
    return client[0] if client else "-"
