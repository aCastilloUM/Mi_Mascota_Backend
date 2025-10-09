from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    # Servicios backend
    auth_service_url: str = Field(alias="AUTH_SERVICE_URL")
    # Otros servicios se agregarán cuando se implementen
    
    # JWT (debe coincidir con auth-svc)
    jwt_secret: str = Field(alias="JWT_SECRET")
    jwt_issuer: str = Field(alias="JWT_ISSUER")
    jwt_audience: str = Field(alias="JWT_AUDIENCE")
    
    # CORS - Permite localhost y conexiones desde la red local (puertos 5173 y 5174)
    cors_origins: str = Field(default="http://localhost:3000,http://localhost:5173,http://localhost:5174,http://*:5173,http://*:5174", alias="CORS_ORIGINS")
    
    # Gateway config
    gateway_port: int = Field(default=8080, alias="GATEWAY_PORT")
    log_level: str = Field(default="info", alias="LOG_LEVEL")
    
    # Redis (para cache y rate limiting)
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    
    # Circuit Breaker
    circuit_breaker_failure_threshold: int = Field(default=5, alias="CIRCUIT_BREAKER_FAILURE_THRESHOLD")
    circuit_breaker_timeout_seconds: int = Field(default=60, alias="CIRCUIT_BREAKER_TIMEOUT_SECONDS")
    circuit_breaker_success_threshold: int = Field(default=2, alias="CIRCUIT_BREAKER_SUCCESS_THRESHOLD")
    
    # Cache
    cache_default_ttl: int = Field(default=60, alias="CACHE_DEFAULT_TTL")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()
