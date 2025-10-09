# upload_again.py
import requests
from pathlib import Path

PROFILE_ID = "ID_DEL_PERFIL"         # reemplazalo con el UUID real
IMAGE_PATH = Path("rdjavi.jpg")      # o la imagen que quieras subir

if not IMAGE_PATH.exists():
    raise SystemExit(f"No se encuentra la imagen {IMAGE_PATH}")

files = {
    "file": (IMAGE_PATH.name, IMAGE_PATH.read_bytes(), "image/jpeg"),
}

resp = requests.post(
    f"http://localhost:8082/profiles/{PROFILE_ID}/photo",
    files=files,
)
print(resp.status_code)
print(resp.json())
