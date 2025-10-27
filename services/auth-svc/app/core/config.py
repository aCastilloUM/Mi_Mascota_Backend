# app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
import os

class Settings(BaseSettings):
    app_name: str = Field(default="auth-svc", alias="APP_NAME")
    env: str = Field(default="development", alias="ENV")
    log_level: str = Field(default="info", alias="LOG_LEVEL")

    database_url: str = Field(alias="DATABASE_URL")
    db_schema: str = Field(default="auth", alias="DB_SCHEMA")

    # JWT 
    jwt_secret: str = Field(alias="JWT_SECRET")
    jwt_issuer: str = Field(alias="JWT_ISSUER")
    jwt_audience: str = Field(alias="JWT_AUDIENCE")
    access_token_ttl_seconds: int = Field(default=900, alias="ACCESS_TOKEN_TTL_SECONDS")

    refresh_token_ttl_seconds: int = Field(default=1209600, alias="REFRESH_TOKEN_TTL_SECONDS")
    refresh_cookie_name: str = Field(default="refresh_token", alias="REFRESH_COOKIE_NAME")
    refresh_cookie_secure: bool = Field(default=False, alias="REFRESH_COOKIE_SECURE")
    refresh_cookie_samesite: str = Field(default="Lax", alias="REFRESH_COOKIE_SAMESITE")
    refresh_cookie_domain: str = Field(default="", alias="REFRESH_COOKIE_DOMAIN")

    # CORS
    cors_allowed_origins: str = Field(default="", alias="CORS_ALLOWED_ORIGINS")
    cors_allowed_headers: str = Field(default="", alias="CORS_ALLOWED_HEADERS")
    cors_allowed_methods: str = Field(default="", alias="CORS_ALLOWED_METHODS")

    # Request ID
    request_id_header: str = Field(default="X-Request-Id", alias="REQUEST_ID_HEADER")

    # Redis
    redis_url: str = Field(alias="REDIS_URL")
    
    # Anti-brute-force (login) - Redis based
    login_max_attempts: int = Field(default=5, alias="LOGIN_MAX_ATTEMPTS")
    login_window_seconds: int = Field(default=900, alias="LOGIN_WINDOW_SECONDS")
    login_block_seconds: int = Field(default=900, alias="LOGIN_BLOCK_SECONDS")

    # Kafka
    kafka_bootstrap_servers: str = Field(alias="KAFKA_BOOTSTRAP_SERVERS")
    user_registered_topic: str = Field(default="user.registered.v1", alias="USER_REGISTERED_TOPIC")
    # Topic published when a user verifies their email
    user_verified_topic: str = Field(default="user.verified.v1", alias="USER_VERIFIED_TOPIC")
    # Optional profile service URL used for immediate sync (internal endpoint). If unset, auth-svc will only publish the event.
    profile_svc_url: str = Field(default="", alias="PROFILE_SVC_URL")
    # Whether to include the verification_token in the register response for development convenience.
    expose_dev_verification_token: bool = Field(default=False, alias="EXPOSE_DEV_VERIFICATION_TOKEN")
    
    # Email configuration
    smtp_host: str = Field(default="smtp.gmail.com", alias="SMTP_HOST")
    smtp_port: int = Field(default=587, alias="SMTP_PORT")
    smtp_user: str = Field(default="", alias="SMTP_USER")
    smtp_password: str = Field(default="", alias="SMTP_PASSWORD")
    smtp_from_email: str = Field(default="noreply@mimascota.com", alias="SMTP_FROM_EMAIL")
    smtp_from_name: str = Field(default="Mi Mascota", alias="SMTP_FROM_NAME")
    
    # Frontend URL for email links (dev default points to Vite dev server)
    frontend_url: str = Field(default="http://localhost:5173", alias="FRONTEND_URL")
    # Gateway (reverse proxy) URL used in email links to call backend via gateway
    gateway_url: str = Field(default="http://localhost:8080", alias="GATEWAY_URL")
    
    # Token expiration times (in minutes)
    email_verification_token_ttl_minutes: int = Field(default=1440, alias="EMAIL_VERIFICATION_TOKEN_TTL_MINUTES")  # 24 hours
    password_reset_token_ttl_minutes: int = Field(default=60, alias="PASSWORD_RESET_TOKEN_TTL_MINUTES")  # 1 hour
    
    # Account locking
    account_lock_threshold: int = Field(default=10, alias="ACCOUNT_LOCK_THRESHOLD")  # Lock after 10 failed attempts
    account_lock_duration_minutes: int = Field(default=30, alias="ACCOUNT_LOCK_DURATION_MINUTES")

    # OTP (email) settings
    otp_length: int = Field(default=6, alias="OTP_LENGTH")
    otp_ttl_seconds: int = Field(default=300, alias="OTP_TTL_SECONDS")
    otp_resend_cooldown: int = Field(default=60, alias="OTP_RESEND_COOLDOWN")
    max_otp_attempts: int = Field(default=5, alias="MAX_OTP_ATTEMPTS")

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

settings = Settings()
