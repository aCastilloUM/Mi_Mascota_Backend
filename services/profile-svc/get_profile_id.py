import base64
from uuid import uuid4

from pathlib import Path
import requests

API = "http://localhost:8082"
profiles = requests.get(f"{API}/profiles").json()
if profiles["items"]:
    profile = profiles["items"][0]
else:
    payload = {
        "user_id": f"rdjavi-{uuid4()}",
        "role": "provider",
        "display_name": "RDjavi",
        "email": "rdjavi@example.com",
    }
    profile = requests.post(f"{API}/profiles", json=payload).json()

print("Use PROFILE_ID=", profile["id"])
