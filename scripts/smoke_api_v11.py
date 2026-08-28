#!/usr/bin/env python3
"""Smoke AMPscan API v1.1. Does not write models or splits."""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "predict_api"))

from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402
from scoring import MAP, VERSION, get_artifacts, get_train_index  # noqa: E402

MAGAININ2 = "GIGKFLHSAKKFGKAFVGEIMNS"
LL37 = "LLGDFFRKSKEKIGKEFKRIVQRIKDFLRNLVPRTES"
WIN25 = "IVGGVEAVPGVWPYQAALFIIDMYF"  # first window in scan_smoke_test.csv


def _load_hcap() -> str:
    text = (ROOT / "reports/benchmarks/hcap18_test.fasta").read_text(encoding="utf-8")
    lines = [ln.strip() for ln in text.splitlines() if ln.strip() and not ln.startswith(">")]
    return "".join(lines)


def fail(msg: str) -> None:
    print("FAIL:", msg, flush=True)
    raise SystemExit(1)


def main() -> None:
    assert VERSION == "ampscan-api-1.1", VERSION
    with TestClient(app) as client:
        _run(client)


def _run(client: TestClient) -> None:
    h = client.get("/health").json()
    if not h.get("ok") or h.get("version") != VERSION:
        fail(f"health {h}")
    if h["train_index"]["n"] < 10000:
        fail(f"train index too small: {h['train_index']}")
    print("health ok", h["version"], "n_train", h["train_index"]["n"], flush=True)

    m = client.get("/metrics").json()
    if m["headline"]["quote"] != 0.9515:
        fail(f"headline mutated: {m['headline']}")
    c2 = m.get("cohort_2b") or {}
    rf2 = c2.get("ampscan_rf") or {}
    if rf2.get("roc_auc") != 0.9030 or rf2.get("pr_auc") != 0.9205:
        fail(f"cohort_2b payload wrong: {rf2}")
    if c2.get("do_not_quote", {}).get("value") != 0.9935:
        fail("missing 0.9935 do-not-quote")
    if m.get("recomputed") is not False:
        fail("metrics.recomputed must stay false")
    print("metrics ok  0.9515 + 2b 0.9030", flush=True)

    r = client.post("/predict", json={"sequence": MAGAININ2}).json()
    if not r["valid"] or r["primary"]["label"] != "AMP":
        fail(f"magainin predict {r}")
    nt = r.get("nearest_train") or {}
    if nt.get("identity") != 1.0 or nt.get("train_id") != "POS_DRAMP_DRAMP02271":
        fail(f"magainin nearest {nt}")
    if not nt.get("exact_match"):
        fail("magainin should be exact train match")
    p_single = r["primary"]["p_amp"]
    print("predict magainin-2 p=", p_single, "nearest", nt["train_id"], flush=True)

    # G→A magainin is itself in train; use a double terminal swap that is not.
    mut = "W" + MAGAININ2[1:-1] + "W"
    rmut = client.post("/predict", json={"sequence": mut}).json()
    nt_mut = rmut.get("nearest_train") or {}
    ident = nt_mut.get("identity")
    if nt_mut.get("exact_match"):
        fail(f"synthetic mutant should not be an exact train hit: {nt_mut}")
    if ident is None or ident >= 1.0 or ident < 0.85:
        fail(f"mutated magainin identity {ident} {nt_mut}")
    print("predict mutant identity", ident, "train_id", nt_mut.get("train_id"), flush=True)

    long_seq = "A" * 140
    rlong = client.post("/predict", json={"sequence": long_seq}).json()
    if rlong["valid"]:
        fail("length 140 should fail /predict")
    joined = " ".join(rlong["errors"])
    if "/scan" not in joined:
        fail(f"length>100 should point at /scan: {rlong['errors']}")
    print("predict >100 points at /scan", flush=True)

    batch = client.post(
        "/predict-batch",
        json={
            "sequences": [
                {"id": "m2", "sequence": MAGAININ2},
                {"id": "short", "sequence": "ACDE"},
                {"sequence": LL37},
            ]
        },
    ).json()
    if batch["n"] != 3 or batch["n_valid"] != 2 or batch["n_invalid"] != 1:
        fail(f"batch counts {batch}")
    by_id = {row["id"]: row for row in batch["results"]}
    if abs(by_id["m2"]["primary"]["p_amp"] - p_single) > 1e-6:
        fail(f"batch vs single magainin {by_id['m2']['primary']['p_amp']} vs {p_single}")
    if by_id["short"]["valid"]:
        fail("short peptide should be invalid in batch")
    if by_id["item_3"]["nearest_train"]["train_id"] != "POS_DRAMP_DRAMP03571":
        fail(f"LL-37 nearest {by_id['item_3']['nearest_train']}")
    print("predict-batch mixed ok", flush=True)

    over = client.post(
        "/predict-batch",
        json={"sequences": [{"sequence": MAGAININ2} for _ in range(501)]},
    )
    if over.status_code != 422:
        fail(f"cap 500 expected 422, got {over.status_code}")
    print("batch cap 500 -> 422", flush=True)

    art = get_artifacts()
    _, p_seq = art.rf_calibrated(WIN25)
    scan_win = client.post("/scan", json={"sequence": WIN25, "window": 25, "step": 1}).json()
    if not scan_win["valid"] or scan_win["n_windows"] != 1:
        fail(f"scan 25-mer {scan_win}")
    if abs(scan_win["windows"][0]["p_amp"] - round(p_seq, 6)) > 1e-6:
        fail(f"scan window != rf_calibrated {scan_win['windows'][0]['p_amp']} vs {p_seq}")
    print("scan 25-mer matches rf_calibrated", scan_win["windows"][0]["p_amp"], flush=True)

    hcap = _load_hcap().upper().translate(MAP)
    scan = client.post("/scan", json={"sequence": hcap, "window": 25, "step": 5}).json()
    if not scan["valid"] or scan["protein_level_call"] is not False:
        fail(f"hCAP-18 scan {scan}")
    if scan["summary"]["max_p_amp"] is None or scan["summary"]["max_p_amp"] < 0.8:
        fail(f"expected LL-37-containing windows high P: {scan['summary']}")
    print(
        "scan hCAP-18 windows",
        scan["n_windows"],
        "max_p",
        scan["summary"]["max_p_amp"],
        "at",
        scan["summary"]["max_start"],
        flush=True,
    )

    index = get_train_index()
    index.nearest(MAGAININ2)  # warmup
    t0 = time.perf_counter()
    n_rep = 20
    for _ in range(n_rep):
        index.nearest(mut)
    ms = (time.perf_counter() - t0) * 1000 / n_rep
    print(f"nearest-train {ms:.2f} ms/query (target <3ms after warmup)", flush=True)
    if ms > 15:
        fail(f"nearest-train too slow: {ms:.2f} ms")

    print("SMOKE OK", flush=True)


if __name__ == "__main__":
    main()
