#!/usr/bin/env python3
"""Example Usage Script for SEC EDGAR Filings Dataset

Demonstrates how to load, filter, and query the dataset using Python's
standard library and optional pandas integration.
"""
from __future__ import annotations
import json
import csv
import pathlib
from typing import Iterator

DATA_DIR = pathlib.Path(__file__).resolve().parent / "data"
STAGING_DIR = DATA_DIR / "staging"
FORM345_DIR = DATA_DIR / "form345"

# Increase CSV field size limit for large disclosure fields
csv.field_size_limit(10_000_000)


def load_jsonl(filename: str) -> list[dict]:
    """Load a JSON Lines file from data/staging."""
    path = STAGING_DIR / filename
    with path.open("r", encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def stream_jsonl(filename: str) -> Iterator[dict]:
    """Stream a JSON Lines file record-by-record to conserve memory."""
    path = STAGING_DIR / filename
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)


def stream_tsv(filename: str) -> Iterator[dict]:
    """Stream a Form 3/4/5 TSV file record-by-record."""
    path = FORM345_DIR / filename
    with path.open("r", encoding="utf-8", errors="replace") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        yield from reader


def demo_companies():
    print("--- 1. Companies Overview ---")
    companies = load_jsonl("companies.jsonl")
    print(f"Loaded {len(companies):,} companies.")
    print("Sample company record:")
    sample = companies[0]
    for k, v in sample.items():
        print(f"  {k}: {v}")


def demo_risk_factors():
    print("\n--- 2. Item 1A Risk Factors Text ---")
    sections = load_jsonl("sections.jsonl")
    risk_factors = [s for s in sections if s.get("item_code") == "1A"]
    print(f"Found {len(risk_factors)} Item 1A Risk Factor narrative extractions.")
    if risk_factors:
        rf = risk_factors[0]
        print(f"Accession: {rf['accession_number']} (CIK: {rf['company_cik']})")
        print(f"Character length: {rf['char_len']:,}")
        preview = rf["section_text"][:250].replace("\n", " ")
        print(f"Preview: {preview}...")


def demo_insider_edges():
    print("\n--- 3. Form 3/4/5 Insider Relationships ---")
    count = 0
    officer_count = 0
    director_count = 0
    for edge in stream_jsonl("owner_edges.jsonl"):
        count += 1
        if edge.get("is_officer"):
            officer_count += 1
        if edge.get("is_director"):
            director_count += 1
        if count <= 2:
            print(f"  [{edge['accession_number']}] {edge['owner_name']} -> {edge['issuer_name']} ({edge.get('officer_title') or edge.get('relationship')})")
    print(f"Total relationships: {count:,} (Officers: {officer_count:,}, Directors: {director_count:,})")


def demo_subsidiaries():
    print("\n--- 4. Exhibit 21 Subsidiary Relationships ---")
    subsidiaries = load_jsonl("subsidiaries.jsonl")
    print(f"Total subsidiary mappings: {len(subsidiaries):,}")
    print("Sample subsidiary records:")
    for sub in subsidiaries[:3]:
        print(f"  Parent CIK: {sub['parent_cik']} -> {sub['subsidiary_name']} [{sub.get('jurisdiction') or 'Unknown jurisdiction'}]")


def demo_auditors():
    print("\n--- 5. Cover Page Auditor Disclosures ---")
    auditors = load_jsonl("auditors.jsonl")
    print(f"Total identified auditor records: {len(auditors):,}")
    for a in auditors[:3]:
        print(f"  CIK {a['company_cik']}: {a['auditor_name']} ({a['auditor_location']}, PCAOB Firm ID: {a['pcaob_firm_id']})")


def main():
    demo_companies()
    demo_risk_factors()
    demo_insider_edges()
    demo_subsidiaries()
    demo_auditors()
    print("\nExample queries completed successfully.")


if __name__ == "__main__":
    main()
