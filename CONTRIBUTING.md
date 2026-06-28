# Contributing

Thanks for your interest in Policy-Guided RAG. This is a research repository; the priority
is **reproducibility and clarity**.

## Development setup

```bash
python -m venv venv && source venv/bin/activate
pip install -e ".[dev]"
```

## Before opening a PR

- Run the fast unit suite: `pytest` (no model downloads required).
- If you change the pipeline, re-run the affected experiment under `scripts/run_experiment.py`
  and commit the new `results/<experiment>/run_<ts>/results.json`.
- Keep claims honest: if a change alters the headline numbers, update `README.md`,
  `docs/RESEARCH_PAPER.md`, and `paper/paper.tex` together.

## Code style

- Follow PEP 8. Public classes/functions get docstrings (see existing modules).
- Library code lives in `src/`; runnable experiments in `experiments/` and `scripts/`.

## Scope

Larger research directions (multi-seed evaluation, guardrails/jailbreak suite, additional
domains) are tracked in the Future Work section of `docs/RESEARCH_PAPER.md`. Issues and PRs
that move those forward are very welcome.
