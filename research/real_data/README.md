# Real CI failure prediction — first verified experiment

The experiment was executed on the user's uploaded `final_research_dataset_MASTER.csv`. `results/evaluation.json` and the serialized model are generated outputs, not illustrative numbers. A 60,000-row chronological sample was used for fast turnaround. The full dataset contains 303,079 rows. Target labels were restricted to success/passed versus failure/failed; other conclusions were excluded. Model selection was by holdout PR-AUC, not accuracy.

## Run on Mac

```bash
cd /path/to/real_data_implementation
python3 -m venv .venv
source .venv/bin/activate
pip install pandas numpy scikit-learn joblib
python train_real_model.py --csv /path/to/final_research_dataset_MASTER.csv --out results --max-rows 60000
python predict_real.py --model results/real_ci_failure_model.joblib --input example_input.json
```

## Critical limitations

- Target is **CI workflow failure**, NOT production deployment failure.
- Feature timing and source provenance must be independently checked before claims of real-world deployability.
- The current split is chronological and excludes overlapping repository+commit identifiers across train/test, but the same commit can have multiple workflow outcomes. This may cause label ambiguity. Cross-repository validation is still required.
- Features from historical records may be absent for a new commit; model input requires explicit fields. Do not silently substitute unknown values with zero.
- The selected Random Forest has PR-AUC ~0.1105 on the holdout, with failure prevalence ~0.0433. It is a weak exploratory predictor, **not a validated release gate**. The false-positive rate at threshold 0.5 is substantial.
- The `is_merge` column is represented as a string category in training. Input must match the trained representation.
- The report should present this as an initial reproducible experiment, not as production-validated AI.

## Next steps for live demo

Copy this folder into a new `research/real_data/` subfolder in your repository; do not commit the 186 MB raw CSV or personal author fields. Integrate inference as a distinct `/api/real-risk` endpoint, keeping existing mandatory CI gates intact. Run unit tests and capture screenshots of actual local UI and GitHub Actions run IDs. No repository files have been modified by this package.
