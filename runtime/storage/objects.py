"""MinIO object storage facade."""

from __future__ import annotations

import hashlib
import io
import threading
from pathlib import Path

from loguru import logger

from runtime.config.settings import get_settings


class ObjectStore:
    """Thin facade. Imports MinIO lazily so tests without infra still pass.

    横切准则: lazy init is thread-safe (防止并发 caller 重复建桶).
    """

    _lock = threading.Lock()

    def __init__(self) -> None:
        s = get_settings()
        self.endpoint = s.minio_endpoint
        self.bucket = s.minio_bucket
        self.access = s.minio_access_key
        self.secret = s.minio_secret_key
        self.secure = s.minio_secure
        self._client = None

    def _conn(self):
        if self._client is not None:
            return self._client
        with ObjectStore._lock:
            if self._client is not None:
                return self._client
            try:
                from minio import Minio
            except ImportError as e:
                raise RuntimeError("minio not installed; pip install minio") from e
            client = Minio(self.endpoint, access_key=self.access, secret_key=self.secret, secure=self.secure)
            if not client.bucket_exists(self.bucket):
                client.make_bucket(self.bucket)
                logger.info("minio bucket created: {}", self.bucket)
            self._client = client
        return self._client

    def put_bytes(self, key: str, data: bytes, *, content_type: str = "application/octet-stream") -> str:
        sha = hashlib.sha256(data).hexdigest()
        self._conn().put_object(self.bucket, key, io.BytesIO(data), length=len(data), content_type=content_type)
        return sha

    def put_file(self, key: str, path: Path) -> str:
        data = path.read_bytes()
        return self.put_bytes(key, data)

    def get_bytes(self, key: str) -> bytes:
        resp = self._conn().get_object(self.bucket, key)
        try:
            return resp.read()
        finally:
            resp.close()
            resp.release_conn()
