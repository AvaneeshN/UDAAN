import joblib
import numpy as np

from ml.features import FEATURE_NAMES
from ml.model_contract import MODEL_SCHEMA_VERSION, TRAINING_DATA_SOURCE
from ml.risk_model import MLRiskPredictor
from ml.train_model import DEMO_FEATURES, train_demo_model


def test_demo_training_writes_a_versioned_compatible_artifact(tmp_path):
    output_path = tmp_path / "model.pkl"

    result_path = train_demo_model(output_path)
    artifact = joblib.load(result_path)
    predictor = MLRiskPredictor(result_path)

    assert result_path == output_path
    assert artifact["schema_version"] == MODEL_SCHEMA_VERSION
    assert artifact["feature_names"] == FEATURE_NAMES
    assert artifact["training_data_source"] == TRAINING_DATA_SOURCE
    assert predictor.metadata["training_data_source"] == "synthetic_demo"
    assert 0 <= predictor.predict_risk(DEMO_FEATURES[0]) <= 1


def test_demo_training_is_prediction_reproducible(tmp_path):
    first_path = train_demo_model(tmp_path / "first.pkl")
    second_path = train_demo_model(tmp_path / "second.pkl")
    first_predictor = MLRiskPredictor(first_path)
    second_predictor = MLRiskPredictor(second_path)

    first_predictions = [
        first_predictor.predict_risk(row)
        for row in DEMO_FEATURES
    ]
    second_predictions = [
        second_predictor.predict_risk(row)
        for row in DEMO_FEATURES
    ]

    np.testing.assert_array_equal(first_predictions, second_predictions)
