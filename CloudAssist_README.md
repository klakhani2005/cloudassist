# CloudAssist — Serverless RAG Document Q&A on AWS

Upload `.txt`/`.md` documents, ask questions, get answers grounded in the
documents with source citations. Runs locally with no AWS account, or deploys
serverless to AWS.

```
                ┌──────────── API Gateway (HTTP API) ───────────┐
 user ──HTTPS──>│ Lambda: FastAPI app (app/lambda_api.py)       │──> Amazon Bedrock (Converse)
                └───────────────┬───────────────────────────────┘
                                │ reads index
 S3 docs/ upload ──event──> Lambda: ingest (app/lambda_ingest.py) ──writes──> S3 index/chunks.json
```
- **Retrieval:** BM25 lexical ranking over ~900-character overlapping chunks (`app/retrieval.py`)
- **Generation:** Bedrock model answers *only* from retrieved excerpts and cites `[Source N]`
- **Ingestion:** validates type, size and UTF-8; re-uploads replace old chunks; rejects are logged
- **Security:** least-privilege IAM per function, encrypted private bucket (`infra/template.yaml`)
- **Monitoring:** structured logs to CloudWatch with 14-day retention, error alarm on the API Lambda

## Run locally (no AWS needed)
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload       # http://127.0.0.1:8000/docs
pytest                              # unit + API + S3-ingest tests (S3 mocked with moto)
```
Local mode returns the retrieved passages instead of a generated answer. The index is
saved to `data/index.json`.

## Evaluate retrieval
```bash
python scripts/evaluate.py --k 5 --verbose
python scripts/evaluate.py --docs path/to/your_docs --questions your_questions.jsonl --k 5
```
Reports hit@k, MRR, and whether unanswerable questions correctly get no strong match.
The bundled `sample_docs/` and `eval/questions.jsonl` are a small demo set. Lexical
retrieval misses synonyms (e.g. "MFA" vs. "multi-factor authentication"); embeddings
are the planned next step.

## Deploy to AWS (SAM)
Prerequisites: AWS CLI + SAM CLI configured, and access to a Bedrock model enabled in your region.
```bash
sam build -t infra/template.yaml
sam deploy --guided                  # creates bucket, 2 Lambdas, HTTP API, alarm
aws s3 cp sample_docs/ s3://<DocsBucketName>/docs/ --recursive   # triggers ingestion
curl -X POST <ApiUrl>/ask -H 'Content-Type: application/json' -d '{"question":"How long are logs kept?"}'
sam delete                           # tear down when finished
```
Cost: Lambda, API Gateway and S3 are pay-per-request (near zero for a demo); Bedrock bills per token.

## Design notes
- **Why store the index in S3?** Lambdas are stateless. The API Lambda reloads the index when the S3 ETag changes.
- **Why reserved concurrency 1 on ingest?** Two simultaneous uploads could each load, modify and overwrite the index. One at a time avoids lost updates. A production version would use a database or vector store (e.g. OpenSearch Serverless) instead.
- **Why BM25 and not embeddings?** It's simple, fast and explainable. A natural next step is Bedrock Titan embeddings and comparing hit@k against this baseline.
