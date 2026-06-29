# TMLR submission build (anonymized, double-blind)

This folder produces the **anonymized** TMLR submission PDF from the author-named preprint
(`../paper.tex`, which remains the version on Zenodo). It uses the official TMLR style files
(`tmlr.sty`, `tmlr.bst`, `fancyhdr.sty`, `math_commands.tex` from the JMLR TMLR repo).

## Build

```bash
python build_tmlr.py            # regenerate policy_guided_rag.tex from ../paper.tex
tectonic policy_guided_rag.tex  # -> policy_guided_rag.pdf   (or: latexmk -pdf)
```

`tmlr.sty`'s default option renders the author block as "Anonymous authors / Paper under
double-blind review", so the build is anonymized automatically. `build_tmlr.py` also replaces
the GitHub URL with an anonymized placeholder and asserts no author-named repo leaks in.

## Pre-submission checklist

1. **Leak contrast number.** Configure an LLM endpoint and run the contrast, then paste the
   measured system-prompt leak rate into the "Contrast with system-prompt policies" paragraph
   in `../paper.tex` (remove the `% TODO(author)` line) and rebuild:
   ```bash
   export OPENAI_API_KEY=... OPENAI_BASE_URL=... LEAK_CONTRAST_MODEL=...
   python ../../experiments/leak_contrast.py
   ```
2. **Anonymized code repo.** Create an `anonymous.4open.science` mirror of the GitHub repo and
   replace the placeholder URL (`https://anonymous.4open.science/r/policy-guided-rag`) in
   `build_tmlr.py` with the real anonymized link; rebuild.
3. **Verify anonymity.** Confirm the PDF body and metadata contain no author name/affiliation
   (`grep -c "Gosalia" policy_guided_rag.tex` → 0). Check `pdfinfo` metadata too.
4. **Zenodo.** Ensure the corrected v2 is the public version (done).
5. **Length.** TMLR has no hard limit but reviewers aren't obligated past ~12 pages of main
   text; trim if needed.
6. **Submit** on OpenReview (TMLR is rolling — no deadline). Include the anonymized repo link
   and a reproducibility statement.

## On acceptance (camera-ready)

De-anonymize: in `build_tmlr.py`, change `\usepackage{tmlr}` to `\usepackage[accepted]{tmlr}`
and set the real `\author{\name ... \email ... \addr ...}`, then rebuild.
