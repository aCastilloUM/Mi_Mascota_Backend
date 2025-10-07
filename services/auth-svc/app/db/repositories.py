# services/auth-svc/app/db/repositories.py
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from .models import User, UserSession

class EmailAlreadyExists(Exception):
    ...

class UserRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, user_id: str) -> Optional[User]:
        res = await self.session.execute(select(User).where(User.id == user_id))
        return res.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        res = await self.session.execute(select(User).where(User.email == email))
        return res.scalar_one_or_none()

    async def create(self, email: str, password_hash: str, full_name: str | None = None) -> User:
        user = User(email=email, password_hash=password_hash, full_name=full_name)
        self.session.add(user)
        try:
            await self.session.flush()      # obtiene el id
            await self.session.commit()     # confirma la transacción
        except IntegrityError as e:
            await self.session.rollback()
            raise EmailAlreadyExists from e
        return user

    # ==================== EMAIL VERIFICATION ====================
    async def get_by_verification_token(self, token: str) -> Optional[User]:
        res = await self.session.execute(
            select(User).where(User.email_verification_token == token)
        )
        return res.scalar_one_or_none()

    async def update_email_verification_token(self, user_id, token: str) -> None:
        await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                email_verification_token=token,
                email_verification_sent_at=datetime.now(timezone.utc)
            )
        )
        await self.session.commit()

    async def verify_email(self, user_id) -> None:
        await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                email_verified=True,
                email_verification_token=None,
                email_verification_sent_at=None
            )
        )
        await self.session.commit()

    # ==================== PASSWORD RESET ====================
    async def get_by_password_reset_token(self, token: str) -> Optional[User]:
        res = await self.session.execute(
            select(User).where(User.password_reset_token == token)
        )
        return res.scalar_one_or_none()

    async def update_password_reset_token(self, user_id, token: str) -> None:
        await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                password_reset_token=token,
                password_reset_sent_at=datetime.now(timezone.utc)
            )
        )
        await self.session.commit()

    async def clear_password_reset_token(self, user_id) -> None:
        await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                password_reset_token=None,
                password_reset_sent_at=None
            )
        )
        await self.session.commit()

    async def update_password(self, user_id, password_hash: str) -> None:
        await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(password_hash=password_hash)
        )
        await self.session.commit()

    # ==================== ACCOUNT LOCKING ====================
    async def increment_failed_attempts(self, user_id) -> int:
        """Incrementa el contador de intentos fallidos y retorna el nuevo valor"""
        user = await self.get_by_id(user_id)
        if not user:
            return 0
        
        new_count = (user.failed_login_attempts or 0) + 1
        await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(failed_login_attempts=new_count)
        )
        await self.session.commit()
        return new_count

    async def reset_failed_attempts(self, user_id) -> None:
        await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(failed_login_attempts=0, locked_until=None)
        )
        await self.session.commit()

    async def lock_account(self, user_id, until: datetime) -> None:
        await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(locked_until=until)
        )
        await self.session.commit()

class UserSessionRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, session_id: str) -> Optional[UserSession]:
        res = await self.session.execute(
            select(UserSession)
            .where(UserSession.id == session_id)
            .execution_options(populate_existing=True)  # forzar recarga desde BD
        )
        return res.scalar_one_or_none()

    async def create(
        self,
        user_id: str,
        refresh_token_hash: str,
        user_agent: str | None,
        ip: str | None,
        expires_at: datetime,
    ) -> UserSession:
        sess = UserSession(
            user_id=user_id,
            refresh_token_hash=refresh_token_hash,
            user_agent=user_agent,
            ip=ip,
            expires_at=expires_at,
        )
        self.session.add(sess)
        await self.session.flush()   # para obtener el id
        await self.session.commit()
        return sess

    async def rotate_token(self, session_id: str, new_hash: str, new_expires_at: datetime) -> None:
        await self.session.execute(
            update(UserSession)
            .where(UserSession.id == session_id)
            .values(refresh_token_hash=new_hash, expires_at=new_expires_at)
        )
        await self.session.commit()

    async def revoke(self, session_id: str) -> None:
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[REPO] Revocando sesión: {session_id}")
        
        now = datetime.now(timezone.utc)
        stmt = (
            update(UserSession)
            .where(UserSession.id == session_id)
            .values(revoked_at=now)
        )
        result = await self.session.execute(stmt)
        logger.info(f"[REPO] UPDATE ejecutado. Rows affected: {result.rowcount}")
        
        await self.session.flush()  # flush antes de commit
        logger.info(f"[REPO] Flush ejecutado")
        
        await self.session.commit()
        logger.info(f"[REPO] Commit ejecutado")


# ==================== 2FA TOTP METHODS (UserRepo extension) ====================
class TwoFactorRepo:
    """Repository methods for 2FA TOTP"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def enable_2fa(
        self,
        user_id: str,
        secret: str,
        backup_codes_hashed: list[str]
    ) -> None:
        """Habilita 2FA para un usuario"""
        await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                two_factor_enabled=True,
                two_factor_secret=secret,
                two_factor_backup_codes=backup_codes_hashed,
                two_factor_enabled_at=datetime.now(timezone.utc)
            )
        )
        await self.session.commit()
    
    async def disable_2fa(self, user_id: str) -> None:
        """Deshabilita 2FA para un usuario"""
        await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                two_factor_enabled=False,
                two_factor_secret=None,
                two_factor_backup_codes=None,
                two_factor_enabled_at=None
            )
        )
        await self.session.commit()
    
    async def update_backup_codes(
        self,
        user_id: str,
        backup_codes_hashed: list[str]
    ) -> None:
        """Actualiza códigos de respaldo"""
        await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(two_factor_backup_codes=backup_codes_hashed)
        )
        await self.session.commit()
    
    async def remove_backup_code(
        self,
        user_id: str,
        remaining_codes: list[str]
    ) -> None:
        """Remueve un código de respaldo usado"""
        await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(two_factor_backup_codes=remaining_codes)
        )
        await self.session.commit()
