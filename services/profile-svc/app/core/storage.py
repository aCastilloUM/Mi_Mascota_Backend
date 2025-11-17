from __future__ import annotations

import asyncio
import logging
import mimetypes
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from typing import Optional
from uuid import UUID, uuid4

from minio import Minio
from minio.error import S3Error
from datetime import timedelta


# Removed presigned URL generation: this service uses MinIO public URLs (via
# MINIO_PUBLIC_URL or direct endpoint) instead of generating temporary
# presigned links. Keeping object storage interactions minimal and focused on
# MinIO; avoid references to S3/AWS signing in the codebase.

from app.core.config import settings

logger = logging.getLogger(__name__)

_bucket_ready: bool = False


@lru_cache(maxsize=1)
def get_minio_client() -> Minio:
    if not settings.MINIO_ENABLED:
        raise RuntimeError("MinIO is disabled")
    if not settings.MINIO_ENDPOINT:
        raise RuntimeError("MINIO_ENDPOINT is not configured")
    if not (settings.MINIO_ACCESS_KEY and settings.MINIO_SECRET_KEY):
        raise RuntimeError("MinIO credentials are not configured")

    return Minio(
        settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY.get_secret_value(),
        secret_key=settings.MINIO_SECRET_KEY.get_secret_value(),
        secure=settings.MINIO_SECURE,
    )


async def _ensure_bucket(client: Minio) -> None:
    global _bucket_ready
    if _bucket_ready:
        return

    exists = await asyncio.to_thread(client.bucket_exists, settings.MINIO_BUCKET)
    if not exists:
        await asyncio.to_thread(client.make_bucket, settings.MINIO_BUCKET)
        logger.info("MinIO bucket '%s' created", settings.MINIO_BUCKET)
    else:
        logger.debug("MinIO bucket '%s' already exists", settings.MINIO_BUCKET)

    _bucket_ready = True


def _build_public_url(object_prefix: str) -> str:
    if settings.MINIO_PUBLIC_URL:
        base = settings.MINIO_PUBLIC_URL.rstrip("/")
        return f"{base}/{object_prefix}"

    scheme = "https" if settings.MINIO_SECURE else "http"
    endpoint = settings.MINIO_ENDPOINT.rstrip("/")
    return f"{scheme}://{endpoint}/{settings.MINIO_BUCKET}/{object_prefix}"


async def store_profile_photo(
    profile_id: UUID,
    data: bytes,
    *,
    filename: Optional[str] = None,
    content_type: Optional[str] = None,
    object_prefix: Optional[str] = None,
) -> str:
    if not data:
        raise ValueError("Empty payload for profile photo")

    client = get_minio_client()
    await _ensure_bucket(client)

    guessed_type, _ = mimetypes.guess_type(filename or "")
    resolved_content_type = content_type or guessed_type or "application/octet-stream"

    extension = Path(filename).suffix if filename and Path(filename).suffix else mimetypes.guess_extension(resolved_content_type) or ""

    if object_prefix:
        base_name = object_prefix.rstrip("/") + f"-{uuid4().hex}"
    else:
        base_name = f"profiles/{profile_id}/{uuid4().hex}"

    logger.debug("store_profile_photo base=%s extension=%s", base_name, extension)
    if extension and not base_name.endswith(extension):
        object_key = f"{base_name}{extension}"
    else:
        object_key = base_name

    logger.debug("store_profile_photo final_key=%s", object_key)
    await asyncio.to_thread(
        client.put_object,
        settings.MINIO_BUCKET,
        object_key,
        BytesIO(data),
        length=len(data),
        content_type=resolved_content_type,
    )

    logger.debug("Stored profile photo in MinIO | profile_id=%s object=%s", profile_id, object_key)
    # Return a public URL for the object. The application expects the
    # frontend to be able to GET this URL; make sure MinIO bucket policy is
    # configured (download/read) or that `MINIO_PUBLIC_URL` points to a proxy
    # that can serve objects.
    return _build_public_url(object_key)


async def delete_profile_photo(object_prefix: str) -> None:
    if not settings.MINIO_ENABLED:
        return

    client = get_minio_client()
    try:
        await asyncio.to_thread(client.remove_object, settings.MINIO_BUCKET, object_prefix)
    except S3Error:
        logger.warning("Failed to delete MinIO object %s", object_prefix, exc_info=True)

