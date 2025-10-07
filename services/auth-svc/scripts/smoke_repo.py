import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import asyncio
from app.db.base import SessionLocal
from app.db.repositories import UserRepo, EmailAlreadyExists

async def main():
    
    async with SessionLocal() as session:
        repo = UserRepo(session)

        # Probar creación
        try:
            user = await repo.create(
                email="test@example.com",
                password_hash="fakehash123"
            )
            print("Usuario creado:", user.id, user.email)
        except EmailAlreadyExists:
            print("El usuario ya existe, probando get_by_email...")

        # Probar búsqueda
        user = await repo.get_by_email("test@example.com")
        if user:
            print("Usuario encontrado:", user.id, user.email)
        else:
            print("ERROR: no se encontró el usuario recién creado")

if __name__ == "__main__":
    asyncio.run(main())
