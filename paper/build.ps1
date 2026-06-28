# Build paper.pdf from paper.tex on Windows (PowerShell).
# Requires a LaTeX distribution (MiKTeX). If pdflatex is not on PATH, set $env:PATH
# to include the MiKTeX bin dir, e.g.:
#   $env:PATH += ";$env:LOCALAPPDATA\Programs\MiKTeX\miktex\bin\x64"
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (Get-Command latexmk -ErrorAction SilentlyContinue) {
    latexmk -pdf -interaction=nonstopmode paper.tex
} else {
    pdflatex -interaction=nonstopmode paper.tex
    bibtex paper
    pdflatex -interaction=nonstopmode paper.tex
    pdflatex -interaction=nonstopmode paper.tex
}

Write-Output "Built paper.pdf"
