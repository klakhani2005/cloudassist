"""Where the chunk index lives: a local JSON file, or an object in S3.

Lambda instances are stateless, so in the cloud the index is persisted to S3
and reloaded when it changes (checked via the object's ETag).
"""
from __future__ import annotations

import json
from pathlib import Path

from app.config import Settings
from app.retrieval import Retriever


class LocalStore:
    def __init__(self, path: str):
        self.path = Path(path)

    def load(self) -> Retriever:
        if not self.path.exists():
            return Retriever()
        return Retriever.from_dict(json.loads(self.path.read_text(encoding="utf-8")))

    def save(self, retriever: Retriever) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(retriever.to_dict()), encoding="utf-8")
        tmp.replace(self.path)  # atomic on the same filesystem

    def is_stale(self, _version) -> bool:
        return False

    def version(self):
        return None


class S3Store:
    def __init__(self, bucket: str, key: str, region: str, client=None):
        import boto3
        self.bucket, self.key = bucket, key
        self.s3 = client or boto3.client("s3", region_name=region)

    def version(self):
        try:
            return self.s3.head_object(Bucket=self.bucket, Key=self.key)["ETag"]
        except self.s3.exceptions.ClientError:
            return None

    def is_stale(self, version) -> bool:
        return self.version() != version

    def load(self) -> Retriever:
        try:
            body = self.s3.get_object(Bucket=self.bucket, Key=self.key)["Body"].read()
        except self.s3.exceptions.NoSuchKey:
            return Retriever()
        return Retriever.from_dict(json.loads(body))

    def save(self, retriever: Retriever) -> None:
        self.s3.put_object(
            Bucket=self.bucket, Key=self.key,
            Body=json.dumps(retriever.to_dict()).encode("utf-8"),
            ContentType="application/json",
        )


def make_store(settings: Settings):
    if settings.index_bucket:
        return S3Store(settings.index_bucket, settings.index_key, settings.aws_region)
    return LocalStore(settings.local_index_path)
