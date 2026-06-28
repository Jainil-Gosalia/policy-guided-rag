# Paper

LaTeX source for *Policy-Guided RAG: Asymmetric Visibility for Controllable Retrieval*.

- `paper.tex` — main source (arXiv-ready `article` class, self-contained, standard packages).
- `references.bib` — bibliography.
- `paper.pdf` — compiled output (committed).
- `build.sh` / `build.ps1` — build scripts.

## Build

```bash
# Linux/macOS or Git Bash (needs TeX Live or MiKTeX on PATH)
bash build.sh

# Windows PowerShell (MiKTeX)
./build.ps1
```

Or upload `paper.tex` + `references.bib` to [Overleaf](https://www.overleaf.com) and
compile there.

The build runs `pdflatex → bibtex → pdflatex → pdflatex` (or `latexmk -pdf` if available).
On MiKTeX, missing packages are fetched automatically on first build.

The Markdown counterpart with the same content lives at `../docs/RESEARCH_PAPER.md`.
