"""
Train RandomForestClassifier to predict risk category (low/medium/high) from risk score
components. Bands: low [0, 0.45), medium [0.45, 0.55), high [0.55, 1.0].
Targets: overfitting proxy (val errors / gap) < 100, underfitting (train errors) < 25.
"""
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, confusion_matrix, classification_report

# Risk bands (from risk_score_5y)
BANDS = [(0.0, 0.45, "low"), (0.45, 0.55, "medium"), (0.55, 1.0, "high")]

FEATURE_COLS = [
    "slope_OFR_change_5y", "slope_Inflation_pct_5y",
    "sum_OFR_change_5y", "sum_Inflation_pct_5y",
]
TARGET_COL = "risk_category"

# Regularization to limit overfitting (tune if needed)
MAX_DEPTH = 6
MIN_SAMPLES_LEAF = 4
RANDOM_STATE = 42


def score_to_category(s):
    """Map risk_score_5y to low / medium / high (rounded to 3 decimal places)."""
    if pd.isna(s):
        return "medium"
    s = round(float(s), 3) # Match UI rounding
    for lo, hi, label in BANDS:
        if lo <= s < hi:
            return label
    return "high" if s >= 0.55 else "medium"


def main():
    df = pd.read_csv("risk_score.csv")
    df[TARGET_COL] = df["risk_score_5y"].apply(score_to_category)

    X = df[FEATURE_COLS].fillna(0.0)
    y = df[TARGET_COL]

    # Stratified 60/20/20 train / val / test
    X_train, X_rest, y_train, y_rest = train_test_split(
        X, y, test_size=0.4, stratify=y, random_state=RANDOM_STATE
    )
    X_val, X_test, y_val, y_test = train_test_split(
        X_rest, y_rest, test_size=0.5, stratify=y_rest, random_state=RANDOM_STATE
    )

    clf = RandomForestClassifier(
        max_depth=MAX_DEPTH,
        min_samples_leaf=MIN_SAMPLES_LEAF,
        random_state=RANDOM_STATE,
        n_estimators=100,
    )
    clf.fit(X_train, y_train)

    y_train_pred = clf.predict(X_train)
    y_val_pred = clf.predict(X_val)
    y_test_pred = clf.predict(X_test)

    train_acc = accuracy_score(y_train, y_train_pred)
    val_acc = accuracy_score(y_val, y_val_pred)
    test_acc = accuracy_score(y_test, y_test_pred)

    n_train_errors = int((y_train != y_train_pred).sum())
    n_val_errors = int((y_val != y_val_pred).sum())
    n_test_errors = int((y_test != y_test_pred).sum())

    # Overfitting: train much better than val (per-project style: keep val errors and gap in check)
    overfitting_gap = train_acc - val_acc
    # Underfitting: too many train errors (target: < 25)
    underfitting_count = n_train_errors

    # Predict on full set for output CSV
    df["risk_category"] = y
    df["risk_category_pred"] = clf.predict(X)
    df[["Country", "risk_score_5y", "risk_score_10y", "risk_category", "risk_category_pred"]].to_csv(
        "risk_score_with_category.csv", index=False
    )

    # Metrics file
    with open("risk_classifier_metrics.txt", "w") as f:
        f.write("Risk classifier (low/medium/high)\n")
        f.write("Train accuracy: {:.4f}\n".format(train_acc))
        f.write("Val   accuracy: {:.4f}\n".format(val_acc))
        f.write("Test  accuracy: {:.4f}\n".format(test_acc))
        f.write("Train errors: {} (underfitting target: < 25)\n".format(n_train_errors))
        f.write("Val   errors: {} (overfitting proxy: val errors)\n".format(n_val_errors))
        f.write("Test  errors: {}\n".format(n_test_errors))
        f.write("Overfitting gap (train_acc - val_acc): {:.4f}\n".format(overfitting_gap))
        f.write("\nConfusion matrix (val):\n")
        f.write(str(confusion_matrix(y_val, y_val_pred, labels=["low", "medium", "high"])))
        f.write("\n\nClassification report (val):\n")
        f.write(classification_report(y_val, y_val_pred, labels=["low", "medium", "high"], zero_division=0))

    print("Risk classifier trained.")
    print("Train acc: {:.4f}, Val acc: {:.4f}, Test acc: {:.4f}".format(train_acc, val_acc, test_acc))
    print("Underfitting count (train errors): {} (target < 25: {})".format(n_train_errors, "OK" if n_train_errors < 25 else "FAIL"))
    print("Overfitting count (val errors): {} (target < 100: {})".format(n_val_errors, "OK" if n_val_errors < 100 else "FAIL"))
    print("Overfitting gap (train - val acc): {:.4f}".format(overfitting_gap))
    print("Saved: risk_score_with_category.csv, risk_classifier_metrics.txt")


if __name__ == "__main__":
    main()
