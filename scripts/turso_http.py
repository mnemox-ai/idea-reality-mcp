"""Minimal Turso HTTP client (/v2/pipeline) — bypasses the libsql sync client,
which hangs on this machine. Used by the embedding backfill and ad-hoc analysis.

Env: TURSO_DATABASE_URL (libsql://… or https://…), TURSO_AUTH_TOKEN.
Arg types follow Hrana: {"type": "integer|float|text|null|blob", ...}.
"""

from __future__ import annotations

import base64
import os
from typing import Any, Sequence

import httpx


def _http_url() -> str:
    url = os.environ["TURSO_DATABASE_URL"]
    return url.replace("libsql://", "https://", 1) if url.startswith("libsql://") else url


def _to_arg(v: Any) -> dict:
    if v is None:
        return {"type": "null"}
    if isinstance(v, bool):
        return {"type": "integer", "value": str(int(v))}
    if isinstance(v, int):
        return {"type": "integer", "value": str(v)}
    if isinstance(v, float):
        return {"type": "float", "value": v}
    if isinstance(v, (bytes, bytearray)):
        return {"type": "blob", "base64": base64.b64encode(bytes(v)).decode("ascii")}
    return {"type": "text", "value": str(v)}


def _from_val(cell: dict) -> Any:
    t = cell.get("type")
    if t == "null":
        return None
    if t == "integer":
        return int(cell["value"])
    if t == "float":
        return float(cell["value"])
    if t == "blob":
        return base64.b64decode(cell["base64"])
    return cell.get("value")


def execute(sql: str, args: Sequence[Any] | None = None, *, timeout: float = 60.0) -> list[dict]:
    """Run one SQL statement. Returns a list of row dicts (empty for writes/DDL)."""
    stmt: dict = {"sql": sql}
    if args:
        stmt["args"] = [_to_arg(a) for a in args]
    payload = {"requests": [{"type": "execute", "stmt": stmt}, {"type": "close"}]}
    with httpx.Client(timeout=timeout) as client:
        resp = client.post(
            f"{_http_url()}/v2/pipeline",
            headers={"Authorization": f"Bearer {os.environ['TURSO_AUTH_TOKEN']}"},
            json=payload,
        )
    resp.raise_for_status()
    result = resp.json()["results"][0]
    if result.get("type") == "error":
        raise RuntimeError(f"Turso error: {result['error']}")
    res = result["response"]["result"]
    cols = [c["name"] for c in res["cols"]]
    return [{cols[i]: _from_val(cell) for i, cell in enumerate(row)} for row in res["rows"]]


def execute_many(statements: list[tuple[str, Sequence[Any]]], *, timeout: float = 120.0) -> None:
    """Run many write statements in a single pipeline request (batched UPDATEs)."""
    reqs: list[dict] = []
    for sql, args in statements:
        stmt: dict = {"sql": sql}
        if args:
            stmt["args"] = [_to_arg(a) for a in args]
        reqs.append({"type": "execute", "stmt": stmt})
    reqs.append({"type": "close"})
    with httpx.Client(timeout=timeout) as client:
        resp = client.post(
            f"{_http_url()}/v2/pipeline",
            headers={"Authorization": f"Bearer {os.environ['TURSO_AUTH_TOKEN']}"},
            json={"requests": reqs},
        )
    resp.raise_for_status()
    for r in resp.json()["results"]:
        if r.get("type") == "error":
            raise RuntimeError(f"Turso error: {r['error']}")


if __name__ == "__main__":
    import sys

    rows = execute(sys.argv[1] if len(sys.argv) > 1 else "SELECT 1 AS ok")
    print(rows)
