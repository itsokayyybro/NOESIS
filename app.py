import json
import os
import threading
import webbrowser
import uuid
from io import BytesIO
from importlib import reload
from typing import Any, Dict, List

from pypdf import PdfReader

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify

import backend_logic as bl

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key-noesis-2024")

# In-memory session store (use Redis/DB in production)
sessions_store: Dict[str, Dict[str, Any]] = {}


def get_generator() -> Any:
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
            checkpoints, retrieval_info = result
        else:
            checkpoints = result

        if retrieval_info:
            retrieved_context = retrieval_info.get("joined")
            retrieval_chunks = retrieval_info.get("display") or []
    except Exception as exc:
        error = f"Failed to generate checkpoints: {exc}"

    # Create session
    session_id = str(uuid.uuid4())
    sessions_store[session_id] = {
        "problem": problem,
        "checkpoints": checkpoints,
        "retrieval_chunks": retrieval_chunks,
        "retrieved_context": retrieved_context,
        "code_submissions": {},
        "completed": set(),
    }

    if error:
        return render_template(
            "checkpoints.html",
            problem=problem,
            checkpoints=[],
            retrieval_chunks=[],
            error=error,
            session_id=session_id,
        )

    return redirect(url_for("view_checkpoints", session_id=session_id))


@app.route("/checkpoints/<session_id>", methods=["GET"])
def view_checkpoints(session_id: str):
    sess = sessions_store.get(session_id)
    if not sess:
        flash("Session not found. Please start a new learning path.")
        return redirect(url_for("index"))

    return render_template(
        "checkpoints.html",
        problem=sess["problem"],
        checkpoints=sess["checkpoints"],
        retrieval_chunks=sess.get("retrieval_chunks", []),
        retrieved_context=sess.get("retrieved_context"),
        session_id=session_id,
        completed=sess.get("completed", set()),
        error=None,
    )


@app.route("/editor/<session_id>/<int:checkpoint_id>", methods=["GET"])
def editor(session_id: str, checkpoint_id: int):
    sess = sessions_store.get(session_id)
    if not sess:
        flash("Session not found. Please start a new learning path.")
        return redirect(url_for("index"))

    checkpoints = sess.get("checkpoints", [])
    if checkpoint_id < 0 or checkpoint_id >= len(checkpoints):
        flash("Invalid checkpoint.")
        return redirect(url_for("view_checkpoints", session_id=session_id))

    checkpoint = checkpoints[checkpoint_id]
    previous_code = sess.get("code_submissions", {}).get(str(checkpoint_id), "")

    return render_template(
        "editor.html",
        session_id=session_id,
        checkpoint_id=checkpoint_id,
        checkpoint=checkpoint,
        previous_code=previous_code,
        total_checkpoints=len(checkpoints),
    )


@app.route("/validate", methods=["POST"])
def validate():
    data = request.get_json()
    session_id = data.get("session_id")
    checkpoint_id = data.get("checkpoint_id")
    code = data.get("code", "")

    sess = sessions_store.get(session_id)
    if not sess:
        return jsonify({"pass": False, "message": "Session not found."})

    checkpoints = sess.get("checkpoints", [])
    if checkpoint_id < 0 or checkpoint_id >= len(checkpoints):
        return jsonify({"pass": False, "message": "Invalid checkpoint."})

    # Store the code submission
    if "code_submissions" not in sess:
        sess["code_submissions"] = {}
    sess["code_submissions"][str(checkpoint_id)] = code

    # Import and run validator
    try:
        import validator
        checkpoint = checkpoints[checkpoint_id]
        result = validator.validate_code(code, checkpoint)
        
        if result.get("pass"):
            if "completed" not in sess:
                sess["completed"] = set()
            sess["completed"].add(checkpoint_id)
        
        return jsonify(result)
    except Exception as e:
        return jsonify({
            "pass": False,
            "message": "Validation error",
            "details": str(e)
        })


@app.route("/admin", methods=["GET", "POST"])
def admin_context():
    message = None
    error = None
    
    if request.method == "POST":
        context_name = request.form.get("context_name", "").strip()
        context_file = request.files.get("context_file")
        
        if not context_name or not context_file:
            error = "Please provide both a name and a file."
        else:
            try:
                content = _read_uploaded_context(context_file)
                # Save to data directory
                data_dir = os.path.join(os.path.dirname(__file__), "data", "context_sources")
                os.makedirs(data_dir, exist_ok=True)
                
                safe_name = "".join(c for c in context_name if c.isalnum() or c in " -_").strip()
                filepath = os.path.join(data_dir, f"{safe_name}.txt")
                
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)
                
                message = f"Successfully ingested '{context_name}'"
            except Exception as e:
                error = f"Failed to ingest context: {e}"
    
    return render_template("admin.html", message=message, error=error)


if __name__ == "__main__":
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        threading.Timer(1.0, _open_browser, args=["http://localhost:5000"]).start()

    app.run(debug=True, host="0.0.0.0", port=5000)