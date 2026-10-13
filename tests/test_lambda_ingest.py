import boto3
from moto import mock_aws

from app.store import S3Store


@mock_aws
def test_s3_triggered_ingest(monkeypatch):
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setenv("INDEX_BUCKET", "docs-bucket")
    monkeypatch.setenv("INDEX_KEY", "index/chunks.json")
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket="docs-bucket")
    s3.put_object(Bucket="docs-bucket", Key="docs/guide.md", Body=b"Rotate IAM credentials regularly.")
    s3.put_object(Bucket="docs-bucket", Key="docs/image.png", Body=b"\x89PNG")

    from app import lambda_ingest
    event = {"Records": [
        {"s3": {"bucket": {"name": "docs-bucket"}, "object": {"key": "docs/guide.md"}}},
        {"s3": {"bucket": {"name": "docs-bucket"}, "object": {"key": "docs/image.png"}}},
    ]}
    result = lambda_ingest.handler(event, s3_client=s3)
    assert [i["key"] for i in result["indexed"]] == ["docs/guide.md"]
    assert result["rejected"][0]["key"] == "docs/image.png"

    retriever = S3Store("docs-bucket", "index/chunks.json", "us-east-1", client=s3).load()
    assert retriever.search("rotate credentials", 1)[0][0].source == "guide.md"


def test_lambda_api_handler_imports():
    from app.lambda_api import handler
    assert callable(handler)
