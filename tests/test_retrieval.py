from app.retrieval import Retriever


def test_finds_relevant_source():
    r = Retriever()
    r.add_text("logging.md", "Send structured application logs to CloudWatch.")
    r.add_text("security.md", "Use IAM roles and rotate credentials.")
    results = r.search("Where do application logs go?", 1)
    assert results and results[0][0].source == "logging.md"


def test_punctuation_or_stopword_query_returns_empty():
    r = Retriever()
    r.add_text("guide.md", "A simple guide.")
    assert r.search("!!!", 3) == []
    assert r.search("what is the", 3) == []


def test_reupload_replaces_chunks():
    r = Retriever()
    r.add_text("a.md", "old content about lambdas")
    r.add_text("a.md", "new content about buckets")
    assert r.count() == 1
    assert r.search("lambdas", 3) == []
    assert r.search("buckets", 3)[0][0].source == "a.md"


def test_long_text_is_chunked_with_overlap():
    r = Retriever()
    text = " ".join(f"word{i}" for i in range(1000))
    n = r.add_text("long.md", text, chunk_chars=200, overlap=40)
    assert n > 1
    # neighbouring chunks share some text
    assert set(r.chunks[0].text.split()) & set(r.chunks[1].text.split())


def test_roundtrip_serialization():
    r = Retriever()
    r.add_text("a.md", "alpha beta gamma")
    r2 = Retriever.from_dict(r.to_dict())
    assert r2.search("gamma", 1)[0][0].source == "a.md"


def test_bad_overlap_rejected():
    import pytest
    with pytest.raises(ValueError):
        Retriever().add_text("a.md", "text", chunk_chars=10, overlap=10)
