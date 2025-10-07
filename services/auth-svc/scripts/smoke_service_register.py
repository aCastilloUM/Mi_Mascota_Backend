import sys, asyncio, uuid

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from app.core.config import settings
from app.db.base import SessionLocal
from app.db.repositories import UserRepo
from app.services.auth_service import AuthService, InvalidRegistration
from app.api.v1.schemas import RegisterRequest, BaseUserIn, ClientIn, Ubication

async def main():
    # usamos un email aleatorio para evitar choque de unique
    rnd = uuid.uuid4().hex[:6]
    email = f"smoke{rnd}@example.com"

    payload = RegisterRequest(
        baseUser=BaseUserIn(
            name="Ana",
            secondName="García",
            email=email,
            documentType="CI",
            document="51234567",
            ubication=Ubication(
                department="Montevideo",
                city="Montevideo",
                postalCode="11000",
                street="Ejemplo",
                number="1234",
                apartment="3B",
            ),
            # Cumple las reglas del front (≥10, mayús, minús, número, símbolo)
            password="Passw0rd!X",
        ),
        # El front manda dd/MM/yyyy — lo aceptamos así
        client=ClientIn(birthDate="01/01/1990"),
    )

    print("DATABASE_URL ->", settings.database_url)

    async with SessionLocal() as session:
        repo = UserRepo(session)
        svc = AuthService(repo)
        try:
            user = await svc.register(payload)
            print("✅ Registro OK")
            print(" id:       ", user.id)
            print(" email:    ", user.email)
            print(" full_name:", user.full_name)
            print(" status:   ", user.status)
        except InvalidRegistration as e:
            print("❌ Registro rechazado:", e.message)

if __name__ == "__main__":
    asyncio.run(main())
