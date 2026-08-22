"""Display tables copied from locked reports. No phase numbers. Not recomputed."""

from __future__ import annotations

HOMOLOGY_TEST = [
    {
        "model": "Random Forest (primary)",
        "accuracy": 0.8734,
        "macro_f1": 0.8734,
        "roc_auc": 0.9515,
        "pr_auc": 0.9542,
    },
    {
        "model": "ESM-2 35M linear",
        "accuracy": 0.8622,
        "macro_f1": 0.8622,
        "roc_auc": 0.9450,
        "pr_auc": 0.9424,
    },
    {
        "model": "1D-CNN",
        "accuracy": 0.8650,
        "macro_f1": 0.8648,
        "roc_auc": 0.9424,
        "pr_auc": 0.9465,
    },
    {
        "model": "ESM-2 150M linear",
        "accuracy": 0.8762,
        "macro_f1": 0.8761,
        "roc_auc": 0.9521,
        "pr_auc": 0.9516,
    },
]

RANDOM_TEST = [
    {"model": "Random Forest", "accuracy": 0.9231, "roc_auc": 0.9791},
    {"model": "ESM-2 35M linear", "accuracy": 0.9009, "roc_auc": 0.9657},
    {"model": "1D-CNN", "accuracy": 0.9203, "roc_auc": 0.9749},
]

CALIBRATION_ECE = [
    {
        "model": "Random Forest",
        "method": "Platt",
        "ece_uncal": 0.0776,
        "ece_cal": 0.0235,
        "roc_auc": 0.9515,
    },
    {
        "model": "ESM-2 35M linear",
        "method": "temperature",
        "ece_uncal": 0.0376,
        "ece_cal": 0.0185,
        "roc_auc": 0.9450,
    },
    {
        "model": "1D-CNN",
        "method": "temperature",
        "ece_uncal": 0.0624,
        "ece_cal": 0.0403,
        "roc_auc": 0.9424,
    },
]

PLAIN_ENGLISH = (
    "Sequences were clustered at 30% identity so related peptides stay in one fold. "
    "The reported Random Forest ROC-AUC on that homology test is 0.9515. "
    "A random split of the same peptides scores 0.9791 because close homologs can sit in both train and test."
)

SOURCES = [
    "reports/baseline/metrics.json",
    "reports/esm2_35M/metrics.json",
    "reports/cnn1d/metrics.json",
    "reports/esm2_150M/metrics.json",
    "reports/calibration/metrics.json",
]
