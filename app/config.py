"""Settings read from environment variables (same names locally and on Lambda)."""
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    use_bedrock: bool
    bedrock_model_id: str
    aws_region: str
    index_bucket: str      # if set, the index is stored in S3 instead of a local file
    index_key: str
    local_index_path: str
    max_upload_bytes: int = 2_000_000


def get_settings() -> Settings:
    return Settings(
        use_bedrock=os.getenv("USE_BEDROCK", "false").lower() == "true",
        bedrock_model_id=os.getenv("BEDROCK_MODEL_ID", "").strip(),
        aws_region=os.getenv("AWS_REGION", "us-east-1"),
        index_bucket=os.getenv("INDEX_BUCKET", "").strip(),
        index_key=os.getenv("INDEX_KEY", "index/chunks.json"),
        local_index_path=os.getenv("LOCAL_INDEX_PATH", "data/index.json"),
    )
