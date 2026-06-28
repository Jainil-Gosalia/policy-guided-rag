#!/bin/bash
# Run all reproducible Policy-Guided RAG experiments in sequence.
# Results are written to timestamped run directories under results/.
set -e

echo "======================================"
echo "Policy-Guided RAG — full experiment suite"
echo "======================================"

echo ""
echo "[1/4] Manual benchmark (15 queries)..."
python scripts/run_experiment.py manual_test

echo ""
echo "[2/4] Synthetic benchmark (150 queries)..."
python scripts/run_experiment.py synthetic_test --dataset synthetic

echo ""
echo "[3/6] Cross-encoder reranker comparison..."
python scripts/run_experiment.py cross_encoder_comparison

echo ""
echo "[4/6] Information-leakage verification..."
python experiments/verification/leakage_test.py

echo ""
echo "[5/6] Governance experiment (non-card: corporate KB + hidden schedule)..."
python scripts/make_governance_dataset.py
python experiments/governance_test.py

echo ""
echo "[6/6] Catalog-drift robustness (predicate vs. frozen ID list)..."
python scripts/governance_drift_demo.py

echo ""
echo "======================================"
echo "All experiments complete. See results/."
echo "======================================"
