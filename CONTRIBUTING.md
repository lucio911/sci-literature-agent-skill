# Contributing

This repository is a conservative research-citation assistant. Changes that improve evidence validity, deterministic LaTeX editing, BibTeX compatibility, and Windows Codex integration are welcome.

1. Keep `skill/SKILL.md` aligned with implemented scripts; do not promise search or PDF access beyond the actual MCP connectors.
2. Add unit tests to `tests/` for fixes and edge cases.
3. Run `python -X utf8 -m unittest discover -s tests -v` before submitting a pull request.
4. Never commit API keys, local manuscripts, private PDFs, unpublished research results, or author contact details.
5. Do not fabricate DOI metadata or claim support. Metadata verification and content verification must remain separate.
6. Treat publisher templates and generated Zotero Better BibTeX exports as user-owned input. Avoid destructive rewrites.

The license is MIT; this project does not include or redistribute the Paper Search MCP package.
