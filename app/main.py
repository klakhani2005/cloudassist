"""CloudAssist API: upload documents, ask questions, get cited answers.

Runs locally with uvicorn, or on AWS Lambda behind API Gateway via app.lambda_api.
"""
from __future__ import annotations

import logging
import threading
import time

from fastapi import FastAPI, File, HTTPException, UploadFile

from app.bedrock import generate_answer
from app.config import get_settings
from app.ingest import InvalidDocument, validate_document
from app.schemas import AskRequest, AskResponse, Source
from app.store import make_store

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
log = logging.getLogger("cloudassist")

settings = get_settings()
store = make_store(settings)
_lock = threading.Lock()
_state = {"retriever": store.load(), "version": store.version()}

app = FastAPI(title="CloudAssist", version="2.0.0")


def retriever():
    """Reload the index if another process (e.g. the ingest Lambda) changed it."""
    with _lock:
        if store.is_stale(_state["version"]):
            _state["retriever"] = store.load()
            _state["version"] = store.version()
        return _state["retriever"]


@app.get("/health")
def health():
    r = retriever()
    return {
        "status": "ok",
        "chunks_indexed": r.count(),
        "documents": len(r.sources()),
        "mode": "bedrock" if settings.use_bedrock else "local",
    }


@app.get("/documents")
def list_documents():
    return {"documents": retriever().sources()}


@app.post("/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    raw = await file.read()
    try:
        name, text = validate_document(file.filename, raw, settings.max_upload_bytes)
    except InvalidDocument as exc:
        log.warning("upload rejected file=%s reason=%s", file.filename, exc)
        raise HTTPException(exc.status, str(exc))
    with _lock:
        r = _state["retriever"]
        added = r.add_text(name, text)
        store.save(r)
        _state["version"] = store.version()
    log.info("indexed file=%s chunks=%d total=%d", name, added, r.count())
    return {"filename": name, "chunks_added": added, "total_chunks": r.count()}


@app.delete("/documents/{name}")
def delete_document(name: str):
    with _lock:
        r = _state["retriever"]
        removed = r.remove_source(name)
        if not removed:
            raise HTTPException(404, "Document not found")
        store.save(r)
        _state["version"] = store.version()
    return {"filename": name, "chunks_removed": removed}


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    started = time.perf_counter()
    matches = retriever().search(req.question, req.top_k)
    mode = "bedrock" if settings.use_bedrock else "local"
    if not matches:
        return AskResponse(answer="I couldn't find a relevant passage in the uploaded documents.",
                           sources=[], mode=mode)
    sources = [{"source": c.source, "chunk_index": c.index, "score": round(score, 4), "text": c.text}
               for c, score in matches]
    if settings.use_bedrock:
        try:
            answer = generate_answer(req.question, sources, settings.bedrock_model_id, settings.aws_region)
        except Exception as exc:  # surface a clean error, details go to CloudWatch
            log.exception("bedrock call failed")
            raise HTTPException(502, f"Bedrock request failed ({type(exc).__name__})")
    else:
        answer = "Relevant passages (local extractive mode):\n\n" + "\n\n".join(
            f"[Source {i + 1}: {s['source']}]\n{s['text']}" for i, s in enumerate(sources))
    log.info("ask mode=%s top_k=%d hits=%d latency_ms=%.1f",
             mode, req.top_k, len(sources), (time.perf_counter() - started) * 1000)
    public = [Source(**{**s, "text": s["text"][:350] + ("…" if len(s["text"]) > 350 else "")}) for s in sources]
    return AskResponse(answer=answer, sources=public, mode=mode)
