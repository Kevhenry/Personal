# Notes -> local LLM

Step 1: convert Evernote `.enex` exports to Markdown (Python 3, no dependencies).

Run on a COPY of the exports (the originals are OneDrive-synced), e.g. in PowerShell:

    python convert_enex.py D:\notes-md `
      "$env:USERPROFILE\OneDrive\Documents\Evernote Export" `
      "$env:USERPROFILE\OneDrive\Old Evernote" `
      --exclude PhotoAlbum --attachments docs

- `--exclude` takes notebook (file) names to skip, e.g. Bank Healthcare Insurance.
- `--attachments none|docs|all` (default `docs`: pdf/office/text only, not images).
- Duplicate notes across both exports are skipped.
- Output: `OUT/<notebook>/<title>-<hash>.md` plus `OUT/_attachments/...`.

Next: index with Ollama (qwen2.5:14b + nomic-embed-text) via Open WebUI or AnythingLLM.

## Pipeline
1. `python convert_enex.py D:\notes-md <enex folders> --exclude PhotoAlbum`
2. `pip install pypdf` then `python extract_pdfs.py D:\notes-md "<Old Evernote>" D:\notes-md\_attachments`
3. `python bundle_notes.py D:\notes-md` -> `D:\notes-md\_bundles\*.md`
4. Upload `_bundles` to an Open WebUI Knowledge collection (drag the folder in).
