# UDAAN
Carbon-aware airline disruption decision support system

## ML model status

`src/ml/model.pkl` is a deterministic integration model trained on three
synthetic examples. Its artifact records the feature contract, scikit-learn
version, schema version, and training-data provenance so incompatible models
fail at startup. It is not validated for real airline operations and must be
replaced with a model trained and evaluated on representative historical data
before production use.

✔ Never work on main
✔ One feature = one branch
✔ One folder per person
✔ Always pull before coding
