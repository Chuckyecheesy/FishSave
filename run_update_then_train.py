"""
One-command pipeline: run update_pipeline.py (if needed) then train_model.py.

If train_features_updated.csv, val_features_updated.csv, and test_features_updated.csv
exist and are newer than country_features.csv and forecast_2019_2025.csv, the update
step is skipped. Otherwise update_pipeline.py is run first, then the model is trained.

Usage: python run_update_then_train.py
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
UPDATE_SCRIPT = os.path.join(ROOT, "update_pipeline.py")
TRAIN_SCRIPT = os.path.join(ROOT, "train_model.py")

UPDATED_CSVS = [
    os.path.join(ROOT, "train_features_updated.csv"),
    os.path.join(ROOT, "val_features_updated.csv"),
    os.path.join(ROOT, "test_features_updated.csv"),
]
DEPS = [
    os.path.join(ROOT, "country_features.csv"),
    os.path.join(ROOT, "forecast_2019_2025.csv"),
]


def run_script(path):
    """Run a Python script in the project root. Exit on failure."""
    result = subprocess.run([sys.executable, path], cwd=ROOT)
    if result.returncode != 0:
        sys.exit(result.returncode)


def main():
    need_update = False
    if not all(os.path.isfile(p) for p in UPDATED_CSVS):
        need_update = True
    else:
        try:
            updated_min_mtime = min(os.path.getmtime(p) for p in UPDATED_CSVS)
            deps_max_mtime = max(os.path.getmtime(p) for p in DEPS if os.path.isfile(p))
            if deps_max_mtime > updated_min_mtime:
                need_update = True
        except OSError:
            need_update = True

    if need_update:
        print("Running update_pipeline.py ...")
        run_script(UPDATE_SCRIPT)
    else:
        print("Updated CSVs present and newer than deps; skipping update_pipeline.py")

    print("Running train_model.py ...")
    run_script(TRAIN_SCRIPT)
    print("Done.")


if __name__ == "__main__":
    main()
