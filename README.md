# Noesis_gdg

Generate learning checkpoints with Gemini. You can now ground outputs on your own syllabus or notebook using retrieval.

## Setup
- Install deps: `pip install -r requirements.txt`
- Export API key: `export GEMINI_API_KEY=your_key`
- Run locally: `python app.py` then open http://localhost:5000

## RAG workflows
- Backend corpus (default): place files in `data/context_sources` (supported: `.txt`, `.md`, `.ipynb`, `.json`, `.pdf`). On first request—or if `REFRESH_CONTEXT_ON_START=true`—the backend rebuilds `data/context_store.json` and serves all users.
- Ad-hoc context (per request): on `/`, optionally paste text or upload a file; that request will be grounded on what you provide. If you leave it empty, the backend corpus is used.

## Notes
- Keep the uploaded file reasonably small; large files are trimmed before chunking.
- Ensure `FLASK_SECRET_KEY` is set in production.