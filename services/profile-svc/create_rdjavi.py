# -*- coding: utf-8 -*-
import requests
from uuid import uuid4
from pathlib import Path

API = "http://localhost:8082"
IMAGE_PATH = Path("rdjavi.jpg")  # asegurate que el archivo exista aquí

if not IMAGE_PATH.exists():
    raise SystemExit(f"Imagen no encontrada: {IMAGE_PATH}")

profile_uuid = uuid4()
profile_payload = {
    "user_id": f"rdjavi-{profile_uuid}",
    "role": "provider",
    "display_name": "RDjavi",
    "email": f"rdjavi.{profile_uuid}@example.com",
    "city": "Montevideo",
    "services": {"walks": True, "training": ["obediencia"]},
    "bio": "Paseador joven, 20 años, amante de los autos y las mascotas.",
    "birth_date": "2005-05-20",
}

resp = requests.post(f"{API}/profiles", json=profile_payload)
resp.raise_for_status()
profile = resp.json()
print("Perfil creado:", profile["id"])

files = {"file": (IMAGE_PATH.name, IMAGE_PATH.read_bytes(), "image/jpeg")}
resp = requests.post(f"{API}/profiles/{profile['id']}/photo", files=files)
resp.raise_for_status()
updated = resp.json()
print("Foto subida:", updated["photo_url"])
