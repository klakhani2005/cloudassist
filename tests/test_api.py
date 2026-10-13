import importlib

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCAL_INDEX_PATH", str(tmp_path / "index.json"))
    monkeypatch.delenv("INDEX_BUCKET", raising=False)
    monkeypatch.setenv("USE_BEDROCK", "false")
    import app.main
    importlib.reload(app.main)
    return TestClient(app.main.app)


def upload(client, name, text):
    return client.post("/documents/upload", files={"file": (name, text.encode(), "text/plain")})


def test_upload_and_ask(client):
    assert upload(client, "logs.md", "Logs are shipped to CloudWatch with 14 day retention.").status_code == 200
    resp = client.post("/ask", json={"question": "Where are logs shipped?"})
    body = resp.json()
    assert resp.status_code == 200
    assert body["mode"] == "local"
    assert body["sources"][0]["source"] == "logs.md"


def test_rejects_bad_files(client):
    assert upload(client, "x.pdf", "hi").status_code == 415
    assert upload(client, "x.md", "   ").status_code == 400
    r = client.post("/documents/upload", files={"file": ("x.md", b"\xff\xfe\xfa", "text/plain")})
    assert r.status_code == 400


def test_validation_errors(client):
    assert client.post("/ask", json={"question": "hi"}).status_code == 422
    assert client.post("/ask", json={"question": "valid question", "top_k": 50}).status_code == 422


def test_index_persists_across_restart(client, tmp_path):
    upload(client, "a.md", "persistent alpha content")
    import app.main
    importlib.reload(app.main)  # simulate a new process
    fresh = TestClient(app.main.app)
    assert fresh.get("/health").json()["chunks_indexed"] == 1


def test_delete(client):
    upload(client, "a.md", "delete me")
    assert client.delete("/documents/a.md").status_code == 200
    assert client.delete("/documents/a.md").status_code == 404


def test_no_match(client):
    upload(client, "a.md", "alpha beta")
    body = client.post("/ask", json={"question": "zebra giraffe"}).json()
    assert body["sources"] == []


def test_bedrock_mode_uses_generator(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCAL_INDEX_PATH", str(tmp_path / "index.json"))
    monkeypatch.setenv("USE_BEDROCK", "true")
    monkeypatch.setenv("BEDROCK_MODEL_ID", "test-model")
    import app.main
    importlib.reload(app.main)
    monkeypatch.setattr(app.main, "generate_answer", lambda q, s, m, r: f"Answer from {m} [Source 1]")
    c = TestClient(app.main.app)
    upload(c, "a.md", "bedrock grounding content")
    body = c.post("/ask", json={"question": "grounding content"}).json()
    assert body["mode"] == "bedrock" and "test-model" in body["answer"]
