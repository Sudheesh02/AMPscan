"""Regression and edge-case tests for the AMPscan scoring pipeline and FastAPI service."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "predict_api"))

from features import featurize_one, hydrophobic_moment, hydrophobic_moment_v2  # noqa: E402
from main import app  # noqa: E402
from scoring import get_artifacts, preprocess  # noqa: E402

MAGAININ2 = "GIGKFLHSAKKFGKAFVGEIMNS"
LL37 = "LLGDFFRKSKEKIGKEFKRIVQRIKDFLRNLVPRTES"


class TestScoringAndAPI(unittest.TestCase):
    def test_preprocess_rejects_multi_fasta(self) -> None:
        multi = f">seq1\n{MAGAININ2}\n>seq2\n{LL37}\n"
        seq, errs = preprocess(multi)
        self.assertIsNone(seq)
        self.assertTrue(any("multiple FASTA" in e for e in errs), errs)

    def test_preprocess_maps_ambiguous_and_strips_stop(self) -> None:
        seq, errs = preprocess(">demo\n GIGKFL*BZUOJ \n")
        self.assertEqual(errs, [])
        self.assertEqual(seq, "GIGKFLXXXXX")

    def test_preprocess_length_bounds(self) -> None:
        self.assertIsNone(preprocess("ACDE")[0])
        self.assertEqual(preprocess("ACDEF")[0], "ACDEF")
        self.assertEqual(preprocess("A" * 100)[0], "A" * 100)
        seq_101, errs_101 = preprocess("A" * 101)
        self.assertIsNone(seq_101)
        self.assertTrue(any("/scan" in e for e in errs_101), errs_101)

    def test_api_predict_batch_scan_explain(self) -> None:
        with TestClient(app) as client:
            r_single = client.post("/predict", json={"sequence": MAGAININ2}).json()
            self.assertTrue(r_single["valid"])
            self.assertEqual(r_single["primary"]["label"], "AMP")

            r_multi = client.post(
                "/predict",
                json={"sequence": f">a\n{MAGAININ2}\n>b\n{LL37}\n"},
            ).json()
            self.assertFalse(r_multi["valid"])
            self.assertTrue(any("multiple FASTA" in e for e in r_multi["errors"]))

            r_batch = client.post(
                "/predict-batch",
                json={"sequences": [{"id": "m2", "sequence": MAGAININ2}]},
            ).json()
            self.assertEqual(r_batch["n_valid"], 1)
            self.assertLess(abs(r_batch["results"][0]["primary"]["p_amp"] - r_single["primary"]["p_amp"]), 1e-6)

            r_exp = client.post("/explain", json={"sequence": MAGAININ2}).json()
            self.assertTrue(r_exp["valid"])
            self.assertEqual(len(r_exp["residues"]), len(MAGAININ2))

    def test_rf_n_jobs_one_and_cnn_device_consistency(self) -> None:
        art = get_artifacts()
        self.assertEqual(art.rf.n_jobs, 1)
        p_single = art.rf_calibrated(MAGAININ2)[1]
        p_many = float(art.rf_calibrated_many([MAGAININ2])[0])
        self.assertLess(abs(p_single - p_many), 1e-7)

        c_single = art.cnn_calibrated(MAGAININ2)[1]
        c_many = float(art.cnn_calibrated_many([MAGAININ2])[0])
        self.assertLess(abs(c_single - c_many), 1e-6)

    def test_v2_features_and_hmoment_phase_preservation(self) -> None:
        # Without 'X', v1 and v2 hydrophobic moment must match exactly
        self.assertAlmostEqual(hydrophobic_moment(MAGAININ2), hydrophobic_moment_v2(MAGAININ2), places=12)
        # With 'X' at position 1, v2 preserves phase of downstream residues vs 'A' placeholder
        s_x = "GXGKFLHSAKK"
        self.assertNotAlmostEqual(hydrophobic_moment(s_x), hydrophobic_moment_v2(s_x), places=4)
        self.assertEqual(featurize_one(MAGAININ2, include_length=True).shape, (425,))
        self.assertEqual(featurize_one(MAGAININ2, include_length=False, v2_hmoment=True).shape, (424,))


if __name__ == "__main__":
    unittest.main(verbosity=2)
