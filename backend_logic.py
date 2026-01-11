"""Checkpoint generation and validation logic using Gemini with backend-driven RAG."""

import json
import math
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import google.generativeai as genai

DEFAULT_MODEL = "gemini-2.5-flash"
EMBED_MODEL = "models/text-embedding-004"
CHUNK_SIZE = 1200
CHUNK_OVERLAP = 150
RETRIEVAL_TOP_K = 4
MAX_CONTEXT_CHARS = 20000
CONTEXT_STORE_PATH = Path(os.getenv("CONTEXT_STORE_PATH", "data/context_store.json"))
CONTEXT_SOURCE_DIR = Path(os.getenv("CONTEXT_SOURCE_DIR", "data/context_sources"))
REFRESH_CONTEXT_ON_START = os.getenv("REFRESH_CONTEXT_ON_START", "false").lower() == "true"
ALLOWED_SOURCE_SUFFIXES = {".txt", ".md", ".ipynb", ".json", ".pdf"}

REQUIRED_FIELDS = {
    "title": "Untitled checkpoint",
    "objective": "Define the goal for this step.",
    "concept": "Key concept involved.",
    "function_signature": "function(arg: type) -> return_type",
    "rules": [],
    "expected_output": "Describe expected behavior or result.",
    "hints": [],
    "test_inputs": [],
    "expected_outputs": [],
    "validation_type": "custom",
}


def _get_api_key(api_key: Optional[str]) -> str:
    key = api_key or os.getenv("GEMINI_API_KEY") or ""
    if not key:
        raise ValueError("GEMINI_API_KEY is required. Set env var or pass api_key.")
    return key


def _ensure_store_dir() -> None:
    CONTEXT_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)


def _read_local_file_text(path: Path) -> str:
    raw_bytes = path.read_bytes()
    if not raw_bytes:
        return ""

    suffix = path.suffix.lower()
    if suffix == ".pdf":
        try:
            from pypdf import PdfReader
            reader = PdfReader(path)
            pages = []
            for page in reader.pages:
                text = page.extract_text() or ""
                if text.strip():
                    pages.append(text)
            if pages:
                return "\n".join(pages)
        except Exception:
            return raw_bytes.decode("utf-8", errors="ignore")

    if suffix == ".ipynb":
        try:
            payload = json.loads(raw_bytes)
            cells = payload.get("cells", [])
            parts = []
            for cell in cells:
                source = cell.get("source", [])
                if isinstance(source, list):
                    parts.append("".join(source))
                elif isinstance(source, str):
                    parts.append(source)
            return "\n".join(parts)
        except Exception:
            return raw_bytes.decode("utf-8", errors="ignore")

    return raw_bytes.decode("utf-8", errors="ignore")


def _coerce_str(value: Any, default: str) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return default


def _coerce_list_str(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _coerce_list_any(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


def normalize_checkpoint(raw: Dict[str, Any], idx: int) -> Dict[str, Any]:
    normalized: Dict[str, Any] = {}
    normalized["title"] = _coerce_str(raw.get("title"), REQUIRED_FIELDS["title"])
    normalized["objective"] = _coerce_str(raw.get("objective"), REQUIRED_FIELDS["objective"])
    normalized["concept"] = _coerce_str(raw.get("concept"), REQUIRED_FIELDS["concept"])
    normalized["function_signature"] = _coerce_str(raw.get("function_signature"), REQUIRED_FIELDS["function_signature"])
    normalized["rules"] = _coerce_list_str(raw.get("rules")) or REQUIRED_FIELDS["rules"]
    normalized["expected_output"] = _coerce_str(raw.get("expected_output"), REQUIRED_FIELDS["expected_output"])
    normalized["hints"] = _coerce_list_str(raw.get("hints")) or REQUIRED_FIELDS["hints"]
    normalized["test_inputs"] = _coerce_list_any(raw.get("test_inputs"))
    normalized["expected_outputs"] = _coerce_list_any(raw.get("expected_outputs"))
    normalized["validation_type"] = _coerce_str(raw.get("validation_type"), REQUIRED_FIELDS["validation_type"])
    normalized["index"] = idx
    return normalized


def normalize_checkpoints(raw: Any) -> List[Dict[str, Any]]:
    if not isinstance(raw, list):
        raw = [raw] if raw is not None else []
    normalized_list = []
    for idx, item in enumerate(raw):
        if not isinstance(item, dict):
            continue
        normalized_list.append(normalize_checkpoint(item, idx))
    return normalized_list


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    cleaned = (text or "").strip()
    if not cleaned:
        return []

    # Simple character-based chunking with overlap to preserve context between segments.
    chunks: List[str] = []
    cursor = 0
    while cursor < len(cleaned):
        end = min(len(cleaned), cursor + chunk_size)
        chunks.append(cleaned[cursor:end])
        cursor = end - overlap if end - overlap > cursor else end
    return chunks


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def embed_text(content: str, api_key: str, task_type: str) -> List[float]:
    genai.configure(api_key=api_key)
    response = genai.embed_content(model=EMBED_MODEL, content=content, task_type=task_type)
    embedding = response.get("embedding") if isinstance(response, dict) else getattr(response, "embedding", None)
    if embedding is None:
        raise RuntimeError("Failed to obtain embedding from Gemini.")
    return embedding


def _load_context_store() -> List[Dict[str, Any]]:
    if not CONTEXT_STORE_PATH.exists():
        return []
    try:
        with CONTEXT_STORE_PATH.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, list):
            return data
    except Exception:
        return []
    return []


def _save_context_store(entries: List[Dict[str, Any]]) -> None:
    _ensure_store_dir()
    with CONTEXT_STORE_PATH.open("w", encoding="utf-8") as fh:
        json.dump(entries, fh)


def ingest_context_text(source_name: str, reference_text: str, api_key: Optional[str] = None) -> Dict[str, Any]:
    capped = (reference_text or "").strip()[:MAX_CONTEXT_CHARS]
    if not capped:
        raise ValueError("No reference text provided for ingestion.")

    chunks = chunk_text(capped)
    if not chunks:
        raise ValueError("Reference text could not be chunked for ingestion.")

    key = _get_api_key(api_key)
    entries = _load_context_store()

    for chunk in chunks:
        embedding = embed_text(chunk, key, task_type="retrieval_document")
        entries.append({
            "source": source_name,
            "text": chunk,
            "embedding": embedding,
        })

    _save_context_store(entries)
    return {"added_chunks": len(chunks), "total_chunks": len(entries)}


def rebuild_context_store_from_dir(source_dir: Path = CONTEXT_SOURCE_DIR, api_key: Optional[str] = None) -> Dict[str, Any]:
    dir_path = source_dir if isinstance(source_dir, Path) else Path(source_dir)
    if not dir_path.exists() or not dir_path.is_dir():
        return {"added_chunks": 0, "total_chunks": 0, "sources": 0}

    key = _get_api_key(api_key)
    entries: List[Dict[str, Any]] = []
    sources = 0
    for file_path in sorted(dir_path.iterdir()):
        if not file_path.is_file() or file_path.suffix.lower() not in ALLOWED_SOURCE_SUFFIXES:
            continue
        text = _read_local_file_text(file_path)
        if not text.strip():
            continue
        sources += 1
        capped = text.strip()[:MAX_CONTEXT_CHARS]
        for chunk in chunk_text(capped):
            embedding = embed_text(chunk, key, task_type="retrieval_document")
            entries.append({
                "source": file_path.name,
                "text": chunk,
                "embedding": embedding,
            })

    _save_context_store(entries)
    return {"added_chunks": len(entries), "total_chunks": len(entries), "sources": sources}


def retrieve_relevant_context(
    problem_statement: str,
    reference_text: Optional[str] = None,
    api_key: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    key = _get_api_key(api_key)

    # Use ad-hoc reference text if provided (backward-compatible), otherwise use stored corpus.
    if reference_text:
        capped = reference_text.strip()[:MAX_CONTEXT_CHARS]
        chunks = chunk_text(capped)
        corpus = [
            {"text": chunk, "embedding": embed_text(chunk, key, task_type="retrieval_document"), "source": "ad-hoc"}
            for chunk in chunks
        ]
    else:
        if REFRESH_CONTEXT_ON_START or not CONTEXT_STORE_PATH.exists():
            rebuild_context_store_from_dir(CONTEXT_SOURCE_DIR, key)
        corpus = _load_context_store()
        if not corpus:
            rebuild_context_store_from_dir(CONTEXT_SOURCE_DIR, key)
            corpus = _load_context_store()

    if not corpus:
        return None

    query_embedding = embed_text(problem_statement, key, task_type="retrieval_query")

    scored: List[Tuple[float, Dict[str, Any]]] = []
    for entry in corpus:
        embedding = entry.get("embedding")
        if not isinstance(embedding, list):
            continue
        score = cosine_similarity(query_embedding, embedding)
        scored.append((score, entry))

    if not scored:
        return None

    top = sorted(scored, key=lambda item: item[0], reverse=True)[:RETRIEVAL_TOP_K]
    selected_strings: List[str] = []
    display_chunks: List[Dict[str, Any]] = []
    for rank, (score, entry) in enumerate(top, start=1):
        chunk_text_val = entry.get("text", "")
        source = entry.get("source", "uploaded")
        selected_strings.append(f"[Chunk {rank} | {source}] {chunk_text_val}")
        display_chunks.append({
            "rank": rank,
            "score": round(float(score), 3),
            "text": chunk_text_val,
            "source": source,
        })

    return {
        "joined": "\n\n".join(selected_strings),
        "display": display_chunks,
    }


def build_prompt(problem_statement: str, retrieved_context: Optional[Any] = None) -> str:
    schema = {
        "title": "Short name of the checkpoint (<= 8 words).",
        "objective": "Student-facing goal for this step.",
        "concept": "Key concept(s) applied here.",
        "function_signature": "Python function signature to implement.",
        "rules": "List of hard constraints.",
        "expected_output": "Describe the expected behavior/output.",
        "hints": "List of helpful hints (<= 3).",
        "test_inputs": "Example inputs to try.",
        "expected_outputs": "Outputs aligned to test_inputs.",
        "validation_type": "One of: structure, correctness, integration, custom.",
    }
    context_block = ""
    if retrieved_context:
        context_text = retrieved_context.get("joined") if isinstance(retrieved_context, dict) else str(retrieved_context)
        context_block = (
            "Reference context (ground checkpoints on this material first):\n"
            f"{context_text}\n"
            "Use only details present in the reference context; do not invent topics.\n"
        )

    prompt = (
        "You are an instructional designer generating programming checkpoints.\n"
        "Return ONLY valid JSON (no prose) representing a list of checkpoint objects.\n"
        "Each checkpoint must follow this JSON schema: " + json.dumps(schema, indent=2) + "\n"
        + context_block +
        "Rules:\n"
        "- 3 to 6 checkpoints total.\n"
        "- Keep titles concise.\n"
        "- Provide actionable rules and hints.\n"
        "- Prefer Pythonic, beginner-friendly guidance.\n"
        "- If reference context exists, align objectives, concepts, and tests to it.\n"
        "Problem statement:\n" + problem_statement.strip() + "\n"
        "Respond with JSON array only.\n"
    )
    return prompt


def extract_json(text: str) -> Any:
    cleaned = (text or "").strip()
    if not cleaned:
        raise ValueError("Gemini response was empty; no JSON to parse.")
    fenced = re.search(r"```json\s*(.*?)```", cleaned, re.DOTALL)
    candidate = fenced.group(1) if fenced else cleaned
    candidate = candidate.strip()
    if not candidate:
        raise ValueError("Gemini response missing JSON payload.")
    try:
        return json.loads(candidate)
    except json.JSONDecodeError as exc:
        snippet = candidate[:300].replace("\n", " ")
        raise ValueError(f"Failed to parse Gemini JSON: {exc}; snippet: {snippet}") from exc


def call_gemini(prompt: str, api_key: Optional[str] = None, model_name: str = DEFAULT_MODEL) -> str:
    key = _get_api_key(api_key)
    genai.configure(api_key=key)
    model = genai.GenerativeModel(model_name, generation_config={"temperature": 0.2})
    response = model.generate_content(prompt)
    if not response or not response.text:
        raise RuntimeError("Empty response from Gemini.")
    return response.text


def generate_checkpoints(
    problem_statement: str,
    api_key: Optional[str] = None,
    model_name: str = DEFAULT_MODEL,
    reference_text: Optional[str] = None,
    return_retrieval: bool = False,
) -> List[Dict[str, Any]] | Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
    retrieved_context = retrieve_relevant_context(problem_statement, reference_text, api_key)
    prompt = build_prompt(problem_statement, retrieved_context=retrieved_context)
    raw_text = call_gemini(prompt, api_key=api_key, model_name=model_name)
    parsed = extract_json(raw_text)
    checkpoints = normalize_checkpoints(parsed)
    if not checkpoints:
        raise ValueError("Gemini returned no checkpoints after parsing.")
    if return_retrieval:
        return checkpoints, retrieved_context
    return checkpoints


# Example (will call the API if GEMINI_API_KEY is set).
# problem = "Build a simple to-do list CLI with add, list, and complete commands."
# checkpoints = generate_checkpoints(problem)
# print(json.dumps(checkpoints, indent=2))