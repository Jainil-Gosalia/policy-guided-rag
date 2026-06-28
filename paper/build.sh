#!/bin/bash
# Build paper.pdf from paper.tex (requires a LaTeX distribution: MiKTeX / TeX Live).
# Runs the standard pdflatex -> bibtex -> pdflatex x2 sequence.
set -e
cd "$(dirname "$0")"

if command -v latexmk >/dev/null 2>&1; then
  latexmk -pdf -interaction=nonstopmode paper.tex
else
  pdflatex -interaction=nonstopmode paper.tex
  bibtex paper || true
  pdflatex -interaction=nonstopmode paper.tex
  pdflatex -interaction=nonstopmode paper.tex
fi

echo "Built paper.pdf"
