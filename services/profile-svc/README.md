# profiles-svc

Servicio FastAPI responsable de los perfiles de Mi Mascota.

> **Integración con Auth:** las operaciones de escritura (`POST /profiles`, `PUT /profiles/{id}`, `DELETE /profiles/{id}`, `POST /profiles/{id}/photo`, `GET /profiles/{id}/history`) requieren un `Authorization: Bearer <token>` válido. El backend toma el `user_id` desde el token; ya no se envía en el payload.

## Dependencias locales

```bash
python -m pip install -r requirements.txt
```

Para habilitar MinIO y Kafka cuando corras el servicio fuera de Docker, ajustá tu `.env`:

```
KAFKA_ENABLED=true
MINIO_ENABLED=true
MINIO_ENDPOINT=localhost:9000
MINIO_PUBLIC_URL=http://localhost:9000/profiles-media
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
```

## Stack de infraestructura (docker-compose)

Desde `Mi_Mascota_Backend/`:

```bash
cd deploy
# Levanta Postgres, Kafka, Redis, MinIO, Elasticsearch/Kibana, Adminer,
# además de auth-svc, profiles-svc y el gateway.
docker compose --env-file .env up -d
```

Servicios expuestos:

- Auth API: `http://localhost:8006` (`/docs`)
- Profiles API directa: `http://localhost:8082` (`/docs`)
- Gateway (proxy Auth + Profiles): `http://localhost:8080`
- Postgres: `localhost:5432` (usuario/clave `app`)
- Kafka broker: `localhost:9092`
- MinIO API/Console: `http://localhost:9000` / `http://localhost:9001` (credenciales `minioadmin/minioadmin`)
- Adminer: `http://localhost:8081`
- Elasticsearch/Kibana: `http://localhost:9200` / `http://localhost:5601`

Para detener:

```bash
docker compose down
```

## Pruebas

```bash
python -m pytest
```

## Upload de fotos

`POST /profiles/{profile_id}/photo` acepta un `multipart/form-data` con el campo `file`. Almacena el archivo en MinIO (`profiles-media`), actualiza `photo_url` y elimina el archivo anterior si existía.

## Eventos Kafka

`POST /profiles` emite `profiles.client.registered.v1`. Si necesitás desactivar Kafka localmente, seteá `KAFKA_ENABLED=false` en `.env`; el endpoint seguirá respondiendo pero omite el publish.
