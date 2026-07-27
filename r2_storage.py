# -*- coding: utf-8 -*-
"""Cloudflare R2 (S3 API): subida y URL pública o presignada. Variables en .env."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from urllib.parse import quote

import boto3
from botocore.config import Config


def _env(name: str) -> str:
    return (os.environ.get(name) or "").strip()


def r2_global_disabled() -> bool:
    """R2_ENABLED=false|0|no|off desactiva subidas aunque existan credenciales."""
    v = _env("R2_ENABLED").lower()
    return v in ("0", "false", "no", "off")


def r2_missing_env_vars() -> list[str]:
    """Lista de variables obligatorias no definidas (vacías)."""
    required = [
        ("R2_ENDPOINT", _env("R2_ENDPOINT")),
        ("R2_ACCESS_KEY_ID", _env("R2_ACCESS_KEY_ID")),
        ("R2_SECRET_ACCESS_KEY", _env("R2_SECRET_ACCESS_KEY")),
        ("R2_BUCKET", _env("R2_BUCKET")),
    ]
    return [n for n, val in required if not val]


def r2_ready() -> bool:
    """True si hay credenciales mínimas y R2 no está desactivado globalmente."""
    if r2_global_disabled():
        return False
    return not r2_missing_env_vars()


def build_s3_client():
    """Cliente S3 compatible con R2."""
    missing = r2_missing_env_vars()
    if missing:
        raise RuntimeError(
            "Faltan variables en .env: " + ", ".join(missing)
        )
    return boto3.client(
        "s3",
        endpoint_url=_env("R2_ENDPOINT"),
        aws_access_key_id=_env("R2_ACCESS_KEY_ID"),
        aws_secret_access_key=_env("R2_SECRET_ACCESS_KEY"),
        region_name=_env("R2_REGION") or "auto",
        config=Config(signature_version="s3v4"),
    )


def public_or_presigned_url(s3: Any, bucket: str, key: str, presign_seconds: int) -> str:
    base = _env("R2_PUBLIC_BASE_URL").rstrip("/")
    if base:
        return f"{base}/{quote(key, safe='/')}"
    return s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=max(60, int(presign_seconds)),
    )


def upload_local_file(
    local_path: str | Path,
    object_key: str,
    *,
    content_type: str | None = None,
    presign_seconds: int | None = None,
) -> tuple[str, str]:
    """
    Sube un archivo y devuelve (url_acceso, object_key).
    URL pública si R2_PUBLIC_BASE_URL; si no, presignada.
    """
    path = Path(local_path)
    if not path.is_file():
        raise FileNotFoundError(str(path))

    if not r2_ready():
        raise RuntimeError("R2 no configurado o R2_ENABLED=off")

    sec = presign_seconds
    if sec is None:
        raw = _env("R2_PRESIGN_SECONDS")
        sec = int(raw) if raw.isdigit() else 604800

    extra: dict[str, str] = {}
    if content_type:
        extra["ContentType"] = content_type
    elif path.suffix.lower() == ".mp4":
        extra["ContentType"] = "video/mp4"

    bucket = _env("R2_BUCKET")
    s3 = build_s3_client()
    key = object_key.replace("\\", "/").lstrip("/")

    kwargs = {}
    if extra:
        kwargs["ExtraArgs"] = extra
    s3.upload_file(str(path.resolve()), bucket, key, **kwargs)

    url = public_or_presigned_url(s3, bucket, key, sec)
    return url, key
