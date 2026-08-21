MODEL_SCHEMA_VERSION = 1
TRAINING_DATA_SOURCE = "synthetic_demo"

REQUIRED_ARTIFACT_KEYS = frozenset({
    "schema_version",
    "feature_names",
    "sklearn_version",
    "training_data_source",
    "model",
})
