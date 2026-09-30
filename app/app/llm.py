from __future__ import annotations

import json
import logging
import re
from typing import Any

import httpx

from . import config

log = logging.getLogger("cpl.llm")

SYSTEM = """You are a Canadian public-accountability analyst. Use ONLY the one source bundle given.

Rules:
- Follow money, promises, contradictions, lobbying, contracts, ethics.
- Only elected officials, parties, registered lobbyists, public institutions, contract vendors.
- No doxing.
- Do not invent. Thin source → low confidence.
- Cite only URLs that appear in the input.
- A contradiction requires the SAME Canadian official and TWO dated statements.
- If this is just a homepage, stock quote, or encyclopedia stub, return {"findings": []}.
- Output JSON only.

JSON schema:
{"findings":[{
  "title":"headline",
  "category":"finance|promise|contradiction|lobbying|contract|ethics|other",
  "summary":"2-4 sentences",
  "claim":"the political claim or promise",
  "evidence":"what THIS source shows",
  "entities":["public names"],
  "money":{"amount":"string or null","currency":"CAD"},
  "promise_status":"kept|broken|partial|unverified|n/a",
  "confidence":0.0,
  "severity":"low|medium|high",
  "source_date":"YYYY-MM-DD or null",
  "sources":[{"url":"...","title":"..."}]
}]}
"""


def _extract_json(text: str) -> dict[str, Any]:
    text = (text or "").strip()
    if not text:
        return {"findings": []}
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        return {"findings": []}
    try:
        data = json.loads(match.group(0))
        return data if isinstance(data, dict) else {"findings": []}
    except json.JSONDecodeError:
        return {"findings": []}


async def model_ready() -> tuple[bool, str]:
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            resp = await client.get(f"{config.OLLAMA_URL}/api/tags")
            resp.raise_for_status()
            names = [m.get("name") for m in (resp.json().get("models") or [])]
            if config.OLLAMA_MODEL in names or any(
                (n or "").startswith(config.OLLAMA_MODEL) for n in names
            ):
                return True, config.OLLAMA_MODEL
            return False, f"present={names}" if names else "no models pulled yet"
    except Exception as exc:
        return False, str(exc)


async def pull_model() -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=600) as client:
        resp = await client.post(
            f"{config.OLLAMA_URL}/api/pull",
            json={"name": config.OLLAMA_MODEL, "stream": False},
        )
        resp.raise_for_status()
        return resp.json()


async def translate_query(text: str, target: str) -> str:
    """Short query translation. Empty string if the model does not answer."""
    text = (text or "").strip()
    if not text:
        return ""
    dest = "French (Canada)" if target == "fr" else "English (Canada)"
    prompt = (
        f"Translate this search query to {dest}. "
        "Return only the translated query, no quotes, no extra words.\n\n"
        f"{text}"
    )
    try:
        async with httpx.AsyncClient(timeout=12) as client:
            resp = await client.post(
                f"{config.OLLAMA_URL}/api/generate",
                json={
                    "model": config.OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "think": False,
                    "keep_alive": "2h",
                    "options": {"temperature": 0.0, "num_ctx": 1024, "num_predict": 60},
                },
            )
            resp.raise_for_status()
            out = (resp.json().get("response") or "").strip().strip('"').strip("'")
            out = out.splitlines()[0].strip() if out else ""
            if not out or out.lower() == text.lower() or len(out) > 200:
                return ""
            return out[:200]
    except Exception as exc:
        log.info("query translate skipped: %s", exc)
        return ""


async def analyze_story(doc: dict[str, Any], claims: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    url = doc.get("url") or ""
    claim_blob = ""
    if claims:
        claim_blob = "\nKNOWN PROMISES:\n" + "\n".join(
            f"- [{c.get('status')}] {c.get('minister')}: {c.get('title')}" for c in claims[:8]
        )
    prompt = (
        f"{SYSTEM}\n\nSOURCE:\ntitle={doc.get('title')}\nurl={url}\n"
        f"date={doc.get('source_date') or ''}\nsnippet={doc.get('snippet')}\n"
        f"text={(doc.get('text') or '')[:3500]}\n{claim_blob}\nReturn JSON only."
    )
    try:
        async with httpx.AsyncClient(timeout=180) as client:
            resp = await client.post(
                f"{config.OLLAMA_URL}/api/generate",
                json={
                    "model": config.OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "think": False,
                    "keep_alive": "2h",
                    "options": {
                        "temperature": 0.1,
                        "num_ctx": config.NUM_CTX,
                        "num_predict": 700,
                    },
                },
            )
            resp.raise_for_status()
            payload = resp.json()
    except Exception as exc:
        log.warning("llm generate failed: %s", exc)
        return []
    data = _extract_json(payload.get("response") or "")
    findings = data.get("findings")
    if not isinstance(findings, list):
        return []
    cleaned: list[dict[str, Any]] = []
    for item in findings:
        if not isinstance(item, dict):
            continue
        sources = []
        for src in item.get("sources") or []:
            if not isinstance(src, dict):
                continue
            src_url = (src.get("url") or "").strip()
            if src_url == url:
                sources.append({"url": src_url, "title": (src.get("title") or doc.get("title") or "")[:200]})
        if not sources:
            # Do not invent a cite. If the model omitted the only legal URL, attach it only when it is this story.
            sources = [{"url": url, "title": doc.get("title") or ""}] if url else []
        if not sources:
            continue
        item["sources"] = sources
        item["origin"] = "model"
        item["language"] = doc.get("language") or "en"
        if not item.get("source_date"):
            item["source_date"] = doc.get("source_date")
        cleaned.append(item)
    return cleaned
