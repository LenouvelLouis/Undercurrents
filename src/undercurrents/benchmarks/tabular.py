"""MLP against the logistic regression already in production, on the same task and features.

Same 10 features, same rows, same chronological split, same metric. The point is to find
out whether the extra capacity buys anything on a dataset this size, and the expected
answer is no: with roughly eight thousand rows and ten hand-built features that already
encode the useful structure, a small network has little left to discover. Running it is
still worth it, because "we measured it" beats "we assumed it".
"""

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler

from undercurrents.prediction import features as prediction_features
from undercurrents.prediction.model import FEATURE_ORDER

SEED = 42
HIDDEN_LAYERS = (64, 32)
MAX_ITER = 600


def _matrix(rows: list[dict]) -> np.ndarray:
    return np.array([[row[name] for name in FEATURE_ORDER] for row in rows], dtype=np.float64)


def run(conn, split_date) -> dict:
    """`split_date` separates training rows from scored rows. Both models are fitted only on
    rows built from shows strictly before it, so neither sees the evaluation period."""
    train_rows, train_labels = prediction_features.build_training_rows(conn, before_date=split_date)
    all_rows, all_labels = prediction_features.build_training_rows(conn, before_date=None)

    if not train_rows or len(set(train_labels)) < 2:
        raise ValueError("Not enough labelled rows before the split date to train")

    # Rows built with the full history minus those available at the split = the held-out part.
    test_rows = all_rows[len(train_rows):]
    test_labels = all_labels[len(train_labels):]
    if not test_rows or len(set(test_labels)) < 2:
        raise ValueError("Not enough held-out rows to score")

    x_train, y_train = _matrix(train_rows), np.array(train_labels)
    x_test, y_test = _matrix(test_rows), np.array(test_labels)

    scaler = StandardScaler().fit(x_train)
    x_train_s, x_test_s = scaler.transform(x_train), scaler.transform(x_test)

    logistic = LogisticRegression(max_iter=1000).fit(x_train, y_train)
    mlp = MLPClassifier(
        hidden_layer_sizes=HIDDEN_LAYERS, max_iter=MAX_ITER, random_state=SEED
    ).fit(x_train_s, y_train)

    def summarise(model, x, positive_from_scaled: bool) -> dict:
        probabilities = model.predict_proba(x)[:, list(model.classes_).index(1)]
        predictions = (probabilities >= 0.5).astype(int)
        true_positive = int(((predictions == 1) & (y_test == 1)).sum())
        predicted_positive = int((predictions == 1).sum())
        actual_positive = int((y_test == 1).sum())
        precision = true_positive / predicted_positive if predicted_positive else 0.0
        recall = true_positive / actual_positive if actual_positive else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        return {
            "accuracy": round(float((predictions == y_test).mean()), 4),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
        }

    baseline = summarise(logistic, x_test, False)
    neural = summarise(mlp, x_test_s, True)
    delta = round(neural["f1"] - baseline["f1"], 4)

    return {
        "task": "will a given song appear in the next show (the model already in production)",
        "features": list(FEATURE_ORDER),
        "train_rows": len(train_rows),
        "test_rows": len(test_rows),
        "baseline": {"name": "logistic regression (in production)", **baseline},
        "model": {"name": f"MLP {HIDDEN_LAYERS}, standardised inputs", **neural},
        "f1_delta": delta,
        "winner": "model" if delta > 0 else ("tie" if delta == 0 else "baseline"),
    }
