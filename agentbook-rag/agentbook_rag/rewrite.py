"""OpenAI-compatible query rewriting with a reproducible JSONL artifact."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from openai import OpenAI


REWRITE_SYSTEM_PROMPT = """你是知识库检索查询改写器。
给定用户问题，生成最多两个互补的检索查询。保留用户原意，不回答问题，不添加资料中没有的事实。
查询应分别覆盖：原问题中可能被隐含的正式术语、以及问题拆开的另一个检索方向。
只输出 JSON 对象：{\"queries\":[\"查询1\",\"查询2\"]}。如果原问题已经足够明确，queries 可以是空数组。"""


def _response_text(response: Any) -> str:
    choices = response.get("choices") if isinstance(response, dict) else response.choices
    if not choices:
        return ""
    first = choices[0]
    message = first.get("message") if isinstance(first, dict) else first.message
    content = message.get("content") if isinstance(message, dict) else message.content
    return content.strip() if isinstance(content, str) else ""


def parse_rewrite_response(text: str, *, max_rewrites: int = 2) -> list[str]:
    """Parse strict JSON while tolerating a fenced JSON response."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`").split("\n", 1)[-1].strip()
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError("rewrite model did not return valid JSON") from exc
    queries = payload.get("queries") if isinstance(payload, dict) else None
    if not isinstance(queries, list):
        raise ValueError("rewrite JSON must contain a queries array")
    values: list[str] = []
    for query in queries:
        if not isinstance(query, str):
            continue
        normalized = " ".join(query.split())
        if normalized and normalized not in values:
            values.append(normalized)
        if len(values) >= max_rewrites:
            break
    return values


def rewrite_query(
    question: str,
    *,
    client: Any | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
    max_rewrites: int = 2,
    timeout_seconds: float = 120.0,
) -> list[str]:
    """Generate bounded rewrites; caller can persist them for later runs."""
    if not question.strip():
        raise ValueError("question must not be empty")
    if max_rewrites < 0:
        raise ValueError("max_rewrites must be non-negative")
    if client is None:
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        kwargs: dict[str, str] = {"api_key": api_key}
        base_url = base_url or os.getenv("OPENAI_BASE_URL")
        if base_url:
            kwargs["base_url"] = base_url
        client = OpenAI(**kwargs, timeout=timeout_seconds)
    response = client.chat.completions.create(
        model=model or os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[
            {"role": "system", "content": REWRITE_SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ],
    )
    return parse_rewrite_response(_response_text(response), max_rewrites=max_rewrites)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question_path", type=Path)
    parser.add_argument("output_path", type=Path)
    parser.add_argument("--model", default=None)
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--max-rewrites", type=int, default=2)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    records: list[dict[str, Any]] = []
    completed: set[str] = set()
    if args.resume and args.output_path.exists():
        for line in args.output_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            completed.add(record["id"])
            records.append(record)
    else:
        args.output_path.parent.mkdir(parents=True, exist_ok=True)
        args.output_path.write_text("", encoding="utf-8")
    for line in args.question_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        question = json.loads(line)
        if question["id"] in completed:
            continue
        record = {
            "id": question["id"],
            "question": question["question"],
            "rewrites": rewrite_query(
                question["question"],
                model=args.model,
                base_url=args.base_url,
                max_rewrites=args.max_rewrites,
                timeout_seconds=args.timeout,
            ),
        }
        with args.output_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        records.append(record)
        completed.add(record["id"])
        print(json.dumps({"completed": len(completed), "id": record["id"]}, ensure_ascii=False), flush=True)
    print(json.dumps({"questions": len(records), "output": str(args.output_path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
