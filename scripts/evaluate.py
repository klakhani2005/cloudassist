"""Measure retrieval quality on a labeled question set.

Usage:
    python scripts/evaluate.py                       # sample_docs + eval/questions.jsonl
    python scripts/evaluate.py --docs my_docs --questions my_questions.jsonl --k 5

Each JSONL line: {"question": "...", "expected": "file.md"}  (expected=null means
the answer is NOT in the corpus; we report how often nothing scores above
--min-score for those).

Metrics:
    hit@k  - share of answerable questions whose expected file appears in the top k
    MRR    - mean reciprocal rank of the expected file (1.0 = always ranked first)
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.ingest import InvalidDocument, validate_document  # noqa: E402
from app.retrieval import Retriever  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--docs", default=ROOT / "sample_docs", type=Path)
    p.add_argument("--questions", default=ROOT / "eval" / "questions.jsonl", type=Path)
    p.add_argument("--k", default=5, type=int)
    p.add_argument("--min-score", default=2.0, type=float,
                   help="top score below this counts as 'no answer found'")
    p.add_argument("--verbose", action="store_true")
    args = p.parse_args()

    r = Retriever()
    ingested = rejected = 0
    for path in sorted(args.docs.iterdir()):
        if not path.is_file():
            continue
        try:
            name, text = validate_document(path.name, path.read_bytes(), 2_000_000)
            r.add_text(name, text)
            ingested += 1
        except InvalidDocument as exc:
            rejected += 1
            print(f"skipped {path.name}: {exc}")

    cases = [json.loads(line) for line in args.questions.read_text(encoding="utf-8").splitlines() if line.strip()]
    answerable = [c for c in cases if c.get("expected")]
    unanswerable = [c for c in cases if not c.get("expected")]

    hits, rr = 0, 0.0
    for c in answerable:
        ranked = [chunk.source for chunk, _ in r.search(c["question"], args.k)]
        rank = ranked.index(c["expected"]) + 1 if c["expected"] in ranked else None
        hits += rank is not None
        rr += 1 / rank if rank else 0
        if args.verbose or rank is None:
            print(f"{'PASS' if rank else 'MISS'} rank={rank} expected={c['expected']} got={ranked[:3]} | {c['question']}")

    abstain = 0
    for c in unanswerable:
        results = r.search(c["question"], 1)
        top = results[0][1] if results else 0.0
        abstain += top < args.min_score
        if args.verbose:
            print(f"UNANSWERABLE top_score={top:.2f} | {c['question']}")

    print(f"\nDocuments ingested: {ingested} (rejected {rejected}), chunks: {r.count()}")
    if answerable:
        print(f"Answerable questions: {len(answerable)}")
        print(f"  hit@{args.k}: {hits}/{len(answerable)} = {hits / len(answerable):.1%}")
        print(f"  MRR: {rr / len(answerable):.3f}")
    if unanswerable:
        print(f"Unanswerable questions correctly given no strong match: {abstain}/{len(unanswerable)}")


if __name__ == "__main__":
    main()
