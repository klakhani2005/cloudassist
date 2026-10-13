"""AWS Lambda triggered by S3 uploads under docs/. Validates and indexes each file.

Pipeline: S3 PutObject (docs/*.md|txt) -> this Lambda -> index saved to S3.
Reserved concurrency is 1 in template.yaml so two uploads can't overwrite each
other's index update.
"""
from __future__ import annotations

import logging
import urllib.parse

import boto3

from app.config import get_settings
from app.ingest import InvalidDocument, validate_document
from app.store import S3Store

log = logging.getLogger("cloudassist.ingest")
log.setLevel(logging.INFO)


def handler(event, context=None, s3_client=None):
    settings = get_settings()
    s3 = s3_client or boto3.client("s3", region_name=settings.aws_region)
    store = S3Store(settings.index_bucket, settings.index_key, settings.aws_region, client=s3)
    retriever = store.load()

    results = {"indexed": [], "rejected": []}
    for record in event.get("Records", []):
        bucket = record["s3"]["bucket"]["name"]
        key = urllib.parse.unquote_plus(record["s3"]["object"]["key"])
        raw = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
        try:
            name, text = validate_document(key, raw, settings.max_upload_bytes)
        except InvalidDocument as exc:
            log.warning("rejected key=%s reason=%s", key, exc)
            results["rejected"].append({"key": key, "reason": str(exc)})
            continue
        chunks = retriever.add_text(name, text)
        log.info("indexed key=%s chunks=%d", key, chunks)
        results["indexed"].append({"key": key, "chunks": chunks})

    if results["indexed"]:
        store.save(retriever)
    log.info("ingest summary indexed=%d rejected=%d total_chunks=%d",
             len(results["indexed"]), len(results["rejected"]), retriever.count())
    return results
