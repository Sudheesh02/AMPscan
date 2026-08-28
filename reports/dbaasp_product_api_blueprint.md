# Product, API & Pitch Blueprint: AMPscan Pro

**Target**: Full-Stack API, Frontend & SIH Hackathon Defense Strategy  
**Date**: August 24, 2026

---

## 1. New API Endpoints (`services/predict_api/`)

1. **`POST /predict/target-specificity`**: Returns 6-axis activity radar vector (`gram_pos`, `gram_neg`, `fungus`, `virus`, `cancer`, `biofilm`).
2. **`POST /predict/safety-profile`**: Returns mammalian cytotoxicity probability, hemolysis risk level, and Therapeutic Selectivity Index ($).
3. **`POST /search/dbaasp-homologs`**: Instant k-mer alignment search against 25,070 DBAASP curated peptides with literature citations and terminus modification badges.
4. **`GET /metrics/external-dbaasp`**: External zero-shot validation benchmarks on homology-partitioned DBAASP holdouts.

---

## 2. 90-Second Hackathon Judge Pitch Script

> *"Judges, antimicrobial resistance is the silent pandemic. Traditional discovery pipelines take years and waste millions synthesizing peptides that either don't generalize or lyse human red blood cells.*
> 
> *Meet **AMPscan Pro**—a 4-tiered in silico antimicrobial discovery platform.*
> 
> *First, we solve the field's fatal flaw: **homology leakage**. Built on strict MMseqs2 30% cluster isolation, our calibrated engine delivers an honest **0.9515 ROC-AUC**.*
> 
> *Second, we don't just give a binary yes/no. Powered by our merged **25,000+ DBAASP dataset**, AMPscan computes a multi-axis target radar across **Gram-positive, Gram-negative, Fungal, and Viral pathogens**.*
> 
> *Third, our **Pre-Clinical Safety Filter** predicts mammalian cytotoxicity and computes a **Therapeutic Selectivity Index**, preventing toxic candidates from reaching expensive synthesis.*
> 
> *Finally, our **Residue Attribution Studio** allows researchers to perform in silico single-point mutations in real-time to optimize antimicrobial potency while tuning down host toxicity.*
> 
> *AMPscan is fast, completely offline-capable, scientifically honest, and ready for pre-clinical triage."*
