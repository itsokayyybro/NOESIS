import json
import os
import threading
import webbrowser
from io import BytesIO
from importlib import reload
from typing import Any, Dict, List

from pypdf import PdfReader

from flask import Flask, render_template, request, redirect, url_for, flash

import backend_logic as bl

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret")


def get_generator() -> Any:
    # Reload on each request to pick up edits without restarting the server.
    return reload(bl).generate_checkpoints


def _read_uploaded_context(upload) -> str:
    if not upload or not getattr(upload, "filename", ""):
        return ""

    raw = upload.read()
    if not raw:
        return ""

    filename = upload.filename.lower()
    if filename.endswith(".pdf"):
        try:
            reader = PdfReader(BytesIO(raw))
            pages = []
            for page in reader.pages:
                text = page.extract_text() or ""
                if text.strip():
                    pages.append(text)
            if pages:
                return "\n".join(pages)
        except Exception:
            # Fall through to generic decode
            pass

    if filename.endswith(".ipynb"):
        try:
            payload = json.loads(raw)
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
            return raw.decode("utf-8", errors="ignore")

    return raw.decode("utf-8", errors="ignore")


def _open_browser(url: str) -> None:
    # Open the app in the default browser after the server starts.
    webbrowser.open(url)


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate():
    problem = request.form.get("problem", "").strip()
    if not problem:
        flash("Please enter a problem statement.")
        return redirect(url_for("index"))

    checkpoints: List[Dict[str, Any]] = []
    retrieved_context: str | None = None
    retrieval_chunks: List[Dict[str, Any]] = []
    retrieval_info: Dict[str, Any] | None = None
    context_text = request.form.get("context_text", "").strip()
    upload_text = _read_uploaded_context(request.files.get("context_file"))
    reference_text_parts = [part for part in (context_text, upload_text) if part]
    reference_text = "\n\n".join(reference_text_parts)
    error: str | None = None
    try:
        generator = get_generator()
        result = generator(
            problem,
            reference_text=reference_text or None,
            return_retrieval=True,
        )
        if isinstance(result, tuple):
            checkpoints, retrieval_info = result  # type: ignore[misc]
        else:
            checkpoints = result

        if retrieval_info:
            retrieved_context = retrieval_info.get("joined")
            retrieval_chunks = retrieval_info.get("display") or []
    except Exception as exc:  # pylint: disable=broad-except
        error = f"Failed to generate checkpoints: {exc}"

    return render_template(
        "checkpoints.html",
        problem=problem,
        checkpoints=checkpoints,
        retrieved_context=retrieved_context,
        retrieval_chunks=retrieval_chunks,
        error=error,
    )


if __name__ == "__main__":
    # Avoid double-opening when the reloader spawns a child process.
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        threading.Timer(1.0, _open_browser, args=["http://localhost:5000"]).start()

    app.run(debug=True, host="0.0.0.0", port=5000)