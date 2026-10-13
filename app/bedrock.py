"""Answer generation with Amazon Bedrock (Converse API), grounded in retrieved chunks."""
from __future__ import annotations

import boto3

PROMPT = (
    "Answer the question using ONLY the excerpts below. If they do not contain the "
    "answer, say you don't know. Cite the excerpts you used like [Source 1].\n\n"
    "EXCERPTS:\n{excerpts}\n\nQUESTION: {question}"
)


def build_prompt(question: str, sources: list[dict]) -> str:
    excerpts = "\n\n".join(
        f"[Source {i + 1}: {s['source']} chunk {s['chunk_index']}]\n{s['text']}"
        for i, s in enumerate(sources)
    )
    return PROMPT.format(excerpts=excerpts, question=question)


def generate_answer(question: str, sources: list[dict], model_id: str, region: str, client=None) -> str:
    if not model_id:
        raise RuntimeError("BEDROCK_MODEL_ID is not configured")
    client = client or boto3.client("bedrock-runtime", region_name=region)
    response = client.converse(
        modelId=model_id,
        messages=[{"role": "user", "content": [{"text": build_prompt(question, sources)}]}],
        inferenceConfig={"temperature": 0.1, "maxTokens": 700},
    )
    blocks = response.get("output", {}).get("message", {}).get("content", [])
    return "\n".join(b["text"] for b in blocks if "text" in b).strip()
