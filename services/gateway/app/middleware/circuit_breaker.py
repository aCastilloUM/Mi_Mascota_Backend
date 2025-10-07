# services/gateway/app/middleware/circuit_breaker.py
"""
Circuit Breaker Middleware
Previene cascada de fallos cuando un servicio backend está caído
"""
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from datetime import datetime, timedelta
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Estados del Circuit Breaker"""
    CLOSED = "closed"       # Normal - requests pasan
    OPEN = "open"          # Bloqueado - requests fallan inmediatamente
    HALF_OPEN = "half_open"  # Probando - permite algunas requests


class CircuitBreaker:
    """
    Circuit Breaker por servicio
    
    Estados:
    - CLOSED: Normal, todas las requests pasan
    - OPEN: Servicio caído, requests fallan rápido (no se intenta llamar)
    - HALF_OPEN: Probando recuperación, permite requests limitadas
    
    Configuración:
    - failure_threshold: Cantidad de fallos antes de abrir el circuito
    - timeout: Tiempo en OPEN antes de intentar HALF_OPEN
    - success_threshold: Éxitos necesarios en HALF_OPEN para CLOSED
    """
    
    def __init__(
        self,
        service_name: str,
        failure_threshold: int = 5,
        timeout_seconds: int = 60,
        success_threshold: int = 2,
    ):
        self.service_name = service_name
        self.failure_threshold = failure_threshold
        self.timeout = timedelta(seconds=timeout_seconds)
        self.success_threshold = success_threshold
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.opened_at = None
    
    def call(self, func, *args, **kwargs):
        """
        Ejecuta la función si el circuito lo permite
        """
        # Si está OPEN, verificar si es momento de probar
        if self.state == CircuitState.OPEN:
            if datetime.now() - self.opened_at >= self.timeout:
                logger.info(
                    f"circuit_breaker_half_open",
                    extra={"service": self.service_name}
                )
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
            else:
                # Todavía bloqueado
                logger.warning(
                    f"circuit_breaker_blocked",
                    extra={
                        "service": self.service_name,
                        "state": self.state.value
                    }
                )
                raise HTTPException(
                    status_code=503,
                    detail={
                        "code": "SERVICE_UNAVAILABLE",
                        "message": f"Service {self.service_name} is temporarily unavailable",
                        "service": self.service_name
                    }
                )
        
        # Intentar llamada
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
    
    async def call_async(self, func, *args, **kwargs):
        """
        Versión async de call()
        """
        # Si está OPEN, verificar si es momento de probar
        if self.state == CircuitState.OPEN:
            if datetime.now() - self.opened_at >= self.timeout:
                logger.info(
                    f"circuit_breaker_half_open",
                    extra={"service": self.service_name}
                )
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
            else:
                # Todavía bloqueado
                logger.warning(
                    f"circuit_breaker_blocked",
                    extra={
                        "service": self.service_name,
                        "state": self.state.value
                    }
                )
                raise HTTPException(
                    status_code=503,
                    detail={
                        "code": "SERVICE_UNAVAILABLE",
                        "message": f"Service {self.service_name} is temporarily unavailable",
                        "service": self.service_name
                    }
                )
        
        # Intentar llamada
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
    
    def _on_success(self):
        """Registra éxito"""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            logger.info(
                f"circuit_breaker_success_in_half_open",
                extra={
                    "service": self.service_name,
                    "success_count": self.success_count,
                    "threshold": self.success_threshold
                }
            )
            
            if self.success_count >= self.success_threshold:
                # Recuperado!
                logger.info(
                    f"circuit_breaker_closed",
                    extra={"service": self.service_name}
                )
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.success_count = 0
        elif self.state == CircuitState.CLOSED:
            # Reset contador de fallos en CLOSED
            self.failure_count = 0
    
    def _on_failure(self):
        """Registra fallo"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        logger.warning(
            f"circuit_breaker_failure",
            extra={
                "service": self.service_name,
                "failure_count": self.failure_count,
                "threshold": self.failure_threshold,
                "state": self.state.value
            }
        )
        
        if self.state == CircuitState.HALF_OPEN:
            # En HALF_OPEN, cualquier fallo vuelve a OPEN
            logger.error(
                f"circuit_breaker_opened_from_half_open",
                extra={"service": self.service_name}
            )
            self.state = CircuitState.OPEN
            self.opened_at = datetime.now()
            self.failure_count = 0
            self.success_count = 0
        
        elif self.failure_count >= self.failure_threshold:
            # En CLOSED, abrir si supera threshold
            logger.error(
                f"circuit_breaker_opened",
                extra={
                    "service": self.service_name,
                    "failures": self.failure_count
                }
            )
            self.state = CircuitState.OPEN
            self.opened_at = datetime.now()
            self.failure_count = 0
    
    def get_state(self) -> dict:
        """Retorna estado actual para observabilidad"""
        return {
            "service": self.service_name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "opened_at": self.opened_at.isoformat() if self.opened_at else None,
        }


# Circuit Breakers globales por servicio
_circuit_breakers = {}


def get_circuit_breaker(service_name: str) -> CircuitBreaker:
    """Obtiene o crea un Circuit Breaker para un servicio"""
    if service_name not in _circuit_breakers:
        _circuit_breakers[service_name] = CircuitBreaker(
            service_name=service_name,
            failure_threshold=5,      # 5 fallos seguidos
            timeout_seconds=60,       # 60s antes de probar
            success_threshold=2,      # 2 éxitos para cerrar
        )
    return _circuit_breakers[service_name]


def get_all_circuit_breakers() -> dict:
    """Retorna estado de todos los circuit breakers"""
    return {
        name: cb.get_state()
        for name, cb in _circuit_breakers.items()
    }


class CircuitBreakerMiddleware(BaseHTTPMiddleware):
    """
    Middleware que agrega Circuit Breaker a las requests
    
    No bloquea aquí directamente, pero expone la funcionalidad
    para que proxy.py la use en las llamadas a backends
    """
    
    async def dispatch(self, request: Request, call_next):
        # El middleware solo pasa la request
        # El Circuit Breaker se aplica en proxy_request()
        response = await call_next(request)
        return response
