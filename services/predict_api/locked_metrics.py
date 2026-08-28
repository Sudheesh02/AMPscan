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

# Copied from reports/benchmarks/cohort_2b_fair_results.md. Not recomputed.
COHORT_2B = {
    "name": "Cohort 2b — length-matched DBAASP OOD",
    "locked_headline_remains": 0.9515,
    "n": 22380,
    "n_pos": 11190,
    "n_neg": 11190,
    "length_median_pos": 14,
    "length_median_neg": 14,
    "n_neg_fragment": 11012,
    "n_neg_intact": 178,
    "negatives": (
        "Mostly random windows from unused long UniProt-style non-AMPs "
        "(n_neg_fragment=11012, n_neg_intact=178). Not experimentally inactive peptides."
    ),
    "fasta_sha256": "f21747c7c69c906625f8998e87e5d6795d1a0171de13d5084a137667c0b528c2",
    "ampscan_rf": {
        "roc_auc": 0.9030,
        "pr_auc": 0.9205,
        "accuracy_at_0.5": 0.6449,
        "mcc": 0.3765,
        "ece_15": 0.2767,
        "skip": 0,
    },
    "tools": [
        {
            "model": "AMPscan RF (Platt)",
            "n": 22380,
            "skip": 0,
            "accuracy": 0.6449,
            "mcc": 0.3765,
            "roc_auc": 0.9030,
            "pr_auc": 0.9205,
            "ece_15": 0.2767,
        },
        {
            "model": "AMPscan 1D-CNN (T)",
            "n": 22380,
            "skip": 0,
            "accuracy": 0.6162,
            "mcc": 0.3235,
            "roc_auc": 0.8894,
            "pr_auc": 0.9117,
            "ece_15": 0.3044,
        },
        {
            "model": "Macrel",
            "n": 20426,
            "skip": 1954,
            "accuracy": 0.8222,
            "mcc": 0.6554,
            "roc_auc": 0.8998,
            "pr_auc": 0.9017,
            "ece_15": 0.1058,
        },
        {
            "model": "AI4AMP PC6",
            "n": 22380,
            "skip": 0,
            "accuracy": 0.8081,
            "mcc": 0.6287,
            "roc_auc": 0.8786,
            "pr_auc": 0.9031,
            "ece_15": 0.0870,
        },
        {
            "model": "AMPlify balanced",
            "n": 20426,
            "skip": 1954,
            "accuracy": 0.8216,
            "mcc": 0.6421,
            "roc_auc": 0.8991,
            "pr_auc": 0.9075,
            "ece_15": 0.0867,
        },
    ],
    "ranking": (
        "Discriminative ranking is a statistical tie at ~0.90 ROC: "
        "AMPscan RF 0.9030, Macrel 0.8998, AMPlify 0.8991, AI4AMP 0.8786. "
        "Do not rank tools by accuracy at 0.5 (Platt does not transfer)."
    ),
    "platt_transfer": (
        "Platt calibration fitted on Cohort 1 does not transfer (ECE 0.2767). "
        "Use ranking (ROC), not the 0.5 label, on short external peptides."
    ),
    "do_not_quote": {
        "value": 0.9935,
        "why": (
            "Earlier full Cohort 2 RF ROC 0.9935 used length-confounded negatives "
            "(pos median 14 vs neg 76). Not a quality claim."
        ),
    },
    "source": "reports/benchmarks/cohort_2b_fair_results.md",
    "recomputed": False,
}

SOURCES = [
    "reports/baseline/metrics.json",
    "reports/esm2_35M/metrics.json",
    "reports/cnn1d/metrics.json",
    "reports/esm2_150M/metrics.json",
    "reports/calibration/metrics.json",
    "reports/benchmarks/cohort_2b_fair_results.md",
]
