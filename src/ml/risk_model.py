from pathlib import Path

import joblib
import numpy as np
import sklearn

from ml.features import FEATURE_NAMES
from ml.model_contract import (
    MODEL_SCHEMA_VERSION,
    REQUIRED_ARTIFACT_KEYS,
)


DEFAULT_MODEL_PATH = Path(__file__).with_name("model.pkl")


class MLRiskPredictor:
    def __init__(self, model_path: str | Path | None = None):
        resolved_path = Path(model_path) if model_path else DEFAULT_MODEL_PATH
        artifact = joblib.load(resolved_path)
        self.model, self.metadata = self._load_artifact(artifact)
        self._validate_model()

    @staticmethod
    def _load_artifact(artifact: object) -> tuple[object, dict]:
        if not isinstance(artifact, dict):
            raise ValueError("ML model artifact must be a metadata dictionary")

        missing_keys = REQUIRED_ARTIFACT_KEYS - artifact.keys()
        if missing_keys:
            missing = ", ".join(sorted(missing_keys))
            raise ValueError(f"ML model artifact is missing: {missing}")

        if artifact["schema_version"] != MODEL_SCHEMA_VERSION:
            raise ValueError(
                "Unsupported ML model schema version: "
                f"{artifact['schema_version']}"
            )
        if tuple(artifact["feature_names"]) != FEATURE_NAMES:
            raise ValueError(
                "ML model feature names do not match the inference contract"
            )
        if artifact["sklearn_version"] != sklearn.__version__:
            raise ValueError(
                "ML model requires scikit-learn "
                f"{artifact['sklearn_version']}; running "
                f"{sklearn.__version__}"
            )
        if not artifact["training_data_source"]:
            raise ValueError(
                "ML model artifact must identify its training data source"
            )

        metadata = {
            key: value
            for key, value in artifact.items()
            if key != "model"
        }
        return artifact["model"], metadata

    def _validate_model(self) -> None:
        if not hasattr(self.model, "predict_proba"):
            raise ValueError("ML model must provide predict_proba()")

        feature_count = getattr(self.model, "n_features_in_", None)
        if feature_count != len(FEATURE_NAMES):
            raise ValueError(
                "ML model expects an incompatible number of features: "
                f"{feature_count}; expected {len(FEATURE_NAMES)}"
            )

        classes = list(getattr(self.model, "classes_", []))
        if 1 not in classes:
            raise ValueError(
                "ML model must include disruption class 1"
            )
        self.positive_class_index = classes.index(1)

    def predict_risk(self, features: np.ndarray) -> float:
        feature_vector = np.asarray(features, dtype=float)
        expected_shape = (len(FEATURE_NAMES),)

        if feature_vector.shape != expected_shape:
            raise ValueError(
                f"ML features must have shape {expected_shape}; "
                f"received {feature_vector.shape}"
            )
        if not np.isfinite(feature_vector).all():
            raise ValueError("ML features must contain only finite values")

        probabilities = self.model.predict_proba(
            feature_vector.reshape(1, -1)
        )
        probability = float(
            probabilities[0][self.positive_class_index]
        )

        if not np.isfinite(probability) or not 0 <= probability <= 1:
            raise ValueError(
                "ML model returned an invalid disruption probability"
            )

        return round(probability, 3)

