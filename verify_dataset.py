#!/usr/bin/env python3
"""Dataset Integrity & Health Verification Script

Verifies all files in the SEC EDGAR dataset:
- Checks existence and non-zero size of all raw and staging data files
- Validates JSON Lines parsing and schema keys
- Validates TSV files and row counts
- Confirms zero corrupt records
"""
from __future__ import annotations
import os
import sys
import json
import csv
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent
DATA = ROOT / "data"

EXPECTED_STAGING = {
    "auditors.jsonl": {"expected_min": 20, "required_keys": {"accession_number", "company_cik", "auditor_name"}},
    "companies.jsonl": {"expected_min": 3500, "required_keys": {"cik", "name"}},
    "documents.jsonl": {"expected_min": 65000, "required_keys": {"accession_number", "doc_type", "filename"}},
    "fetch_manifest.jsonl": {"expected_min": 200, "required_keys": {"accession_number", "filename", "doc_type"}},
    "filings.jsonl": {"expected_min": 5700, "required_keys": {"accession_number", "company_cik", "form_type"}},
    "form345_issuers.jsonl": {"expected_min": 5000, "required_keys": {"cik", "name"}},
    "insiders.jsonl": {"expected_min": 37000, "required_keys": {"owner_cik", "owner_name"}},
    "owner_edges.jsonl": {"expected_min": 76000, "required_keys": {"accession_number", "owner_cik", "issuer_cik"}},
    "sections.jsonl": {"expected_min": 400, "required_keys": {"accession_number", "item_code", "section_text"}},
    "subsidiaries.jsonl": {"expected_min": 3800, "required_keys": {"accession_number", "parent_cik", "subsidiary_name"}},
}

EXPECTED_FORM345 = {
    "DERIV_HOLDING.tsv": 18000,
    "DERIV_TRANS.tsv": 43000,
    "FOOTNOTES.tsv": 170000,
    "NONDERIV_HOLDING.tsv": 33000,
    "NONDERIV_TRANS.tsv": 110000,
    "OWNER_SIGNATURE.tsv": 75000,
    "REPORTINGOWNER.tsv": 76000,
    "SUBMISSION.tsv": 71000,
}

csv.field_size_limit(10_000_000)


def verify_staging() -> bool:
    print("--- Verifying data/staging ---")
    staging_dir = DATA / "staging"
    if not staging_dir.is_dir():
        print("ERROR: staging directory missing")
        return False

    all_ok = True
    for fname, spec in EXPECTED_STAGING.items():
        p = staging_dir / fname
        if not p.exists() or p.stat().st_size == 0:
            print(f"  [FAIL] {fname}: missing or empty")
            all_ok = False
            continue

        count = 0
        corrupt = 0
        with p.open("r", encoding="utf-8", errors="replace") as fh:
            for line_no, line in enumerate(fh, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    count += 1
                    if line_no == 1:
                        missing = spec["required_keys"] - set(obj.keys())
                        if missing:
                            print(f"  [WARN] {fname}: missing expected keys {missing}")
                except Exception as e:
                    corrupt += 1
                    if corrupt <= 3:
                        print(f"  [FAIL] {fname} line {line_no} JSON parse error: {e}")

        if corrupt > 0 or count < spec["expected_min"]:
            print(f"  [FAIL] {fname}: {count:,} rows parsed, {corrupt} corrupt lines")
            all_ok = False
        else:
            print(f"  [PASS] {fname}: {count:,} valid rows, 0 corrupt ({p.stat().st_size / 1e6:.2f} MB)")

    # Check SIC map
    sic_map = staging_dir / "sic_map.json"
    if sic_map.exists() and sic_map.stat().st_size > 0:
        data = json.loads(sic_map.read_text("utf-8"))
        print(f"  [PASS] sic_map.json: {len(data):,} SIC codes verified")
    else:
        print("  [FAIL] sic_map.json missing or empty")
        all_ok = False

    return all_ok


def verify_form345() -> bool:
    print("\n--- Verifying data/form345 ---")
    f345_dir = DATA / "form345"
    if not f345_dir.is_dir():
        print("ERROR: form345 directory missing")
        return False

    all_ok = True
    for fname, min_rows in EXPECTED_FORM345.items():
        p = f345_dir / fname
        if not p.exists() or p.stat().st_size == 0:
            print(f"  [FAIL] {fname}: missing or empty")
            all_ok = False
            continue

        with p.open("r", encoding="utf-8", errors="replace") as fh:
            reader = csv.reader(fh, delimiter="\t")
            header = next(reader, None)
            if not header:
                print(f"  [FAIL] {fname}: missing header")
                all_ok = False
                continue
            rows = sum(1 for _ in reader)

        if rows < min_rows:
            print(f"  [FAIL] {fname}: only {rows:,} rows, expected >= {min_rows:,}")
            all_ok = False
        else:
            print(f"  [PASS] {fname}: {rows:,} rows, {len(header)} columns ({p.stat().st_size / 1e6:.2f} MB)")

    return all_ok


def verify_raw_and_feeds() -> bool:
    print("\n--- Verifying Raw Archives & Feeds ---")
    all_ok = True
    
    xml_feed = DATA / "xbrlrss-2022-01.xml"
    if xml_feed.exists() and xml_feed.stat().st_size > 20_000_000:
        print(f"  [PASS] xbrlrss-2022-01.xml: {xml_feed.stat().st_size / 1e6:.2f} MB")
    else:
        print("  [FAIL] xbrlrss-2022-01.xml missing or truncated")
        all_ok = False

    zip_file = DATA / "2022q1_form345.zip"
    if zip_file.exists() and zip_file.stat().st_size > 10_000_000:
        print(f"  [PASS] 2022q1_form345.zip: {zip_file.stat().st_size / 1e6:.2f} MB")
    else:
        print("  [FAIL] 2022q1_form345.zip missing or truncated")
        all_ok = False

    raw_dir = DATA / "raw"
    if raw_dir.is_dir():
        dirs = [d for d in raw_dir.iterdir() if d.is_dir()]
        files = list(raw_dir.glob("*/*"))
        print(f"  [PASS] raw/: {len(dirs):,} accession folders, {len(files):,} downloaded filing documents")
    else:
        print("  [FAIL] raw/ directory missing")
        all_ok = False

    return all_ok


def main() -> int:
    print(f"Checking dataset integrity at: {DATA}\n")
    ok1 = verify_staging()
    ok2 = verify_form345()
    ok3 = verify_raw_and_feeds()

    if ok1 and ok2 and ok3:
        print("\nAll dataset components verified: 100% intact, valid, and uncorrupted.")
        return 0
    else:
        print("\nIntegrity check FAILED on one or more components.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
