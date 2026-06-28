# Synthetic Test Data

Large-scale generated dataset for validation at scale.

## Files

- `cards.json` - 50 credit card products (generated)
- `guidance.json` - 25 policy rules (generated)
- `queries.json` - 150 test queries across difficulty levels (generated)
- `metadata.json` - Generation parameters and statistics

## Generation Method

Generated using GPT-4 via the data generation pipeline in `src/data_generation/`.

## Difficulty Distribution

- Easy: ~30% of queries
- Medium: ~35% of queries  
- Hard: ~25% of queries
- Expert: ~10% of queries
