# SEC EDGAR Filings & Corporate Ownership Network Dataset

A structured, multi-layer research dataset of U.S. Securities and Exchange Commission (SEC) EDGAR filings, corporate ownership networks, corporate subsidiaries, auditor relationships, and narrative disclosure text.

The primary design principle of this dataset is that **`accession_number` (or `adsh`) serves as the universal join key and provenance identifier** across all layers, linking company metadata, raw documents, narrative text sections, insider trading records, and corporate hierarchy trees.

---

## 1. Dataset Overview & Scope

| Component | Coverage Period | Raw Source | Processed Format | Records / Count | Uncompressed Size |
|---|---|---|---|---|---|
| **Filing Spine & Manifest** | Jan 1, 2022 – Jan 31, 2022 | SEC Monthly XBRL RSS Feed | XML & JSONL | 5,732 filings, 3,554 companies, 66,333 docs | ~47 MB |
| **Form 3/4/5 Insider Ownership** | Jan 1, 2022 – Mar 31, 2022 (2022 Q1) | SEC Insider Transactions Dataset | TSV & JSONL | 76,260 reporting owner records, 71,395 submissions | ~90 MB |
| **Raw SEC Documents** | Jan 2022 Filings | EDGAR Document Archives | HTML / iXBRL | 161 accessions, 206 primary 10-K & EX-21 docs | ~237 MB |
| **Extracted Narrative Sections** | 2021 Fiscal Year (Filed Jan 2022) | 10-K Primary Documents | JSONL | 409 items (16.4M text chars: Item 1, 1A, 3, 7, 7A) | ~17 MB |
| **Corporate Subsidiaries** | Filed Jan 2022 | 10-K Exhibit 21 Attachments | JSONL | 3,815 subsidiary mappings (97.1% with jurisdiction) | ~0.7 MB |
| **Independent Auditors** | Fiscal Year 2021 | 10-K Cover Page XBRL tags | JSONL | 20 auditor profiles (PCAOB firm IDs, locations) | ~4 KB |
| **Embedding Weights & Model** | Reference Embeddings | Hugging Face (all-MiniLM-L6-v2) | safetensors / config | 384-dimensional dense vectors (14,187 chunks) | ~87 MB |

---

## 2. Temporal Coverage & Date Ranges

- **Filing Date Range (Filing Spine)**: `2021-12-30` to `2022-01-31`
- **Period of Report Range (Filings)**: `2019-09-30` to `2022-01-31` (concentrated on annual and quarterly periods ending December 31, 2021)
- **Insider Transaction Filing Dates (Form 3/4/5)**: `2022-01-03` to `2022-03-31` (Q1 2022)
- **Historical Transaction Dates (Form 3/4/5)**: Reports historical insider holdings dating back to `1988-03-22` up to `2022-03-31`

---

## 3. Data Acquisition & Pipeline

The dataset was acquired directly from official U.S. SEC EDGAR endpoints adhering strictly to SEC Fair Access guidelines (<= 10 requests/second, custom user agent header, and gzip encoding).

```
                      xbrlrss-2022-01.xml (Monthly Feed)
                                     │
                    ┌────────────────┴────────────────┐
                    │   Stage 1: Filing Spine & CIKs  │
                    └────────────────┬────────────────┘
                                     │
         ┌───────────────────────────┼───────────────────────────┐
         │                           │                           │
2022q1_form345.zip           206 SEC Documents           EX-21 Exhibits
(SEC Insider Data)         (10-K HTML primary docs)   (Subsidiary lists)
         │                           │                           │
         ▼                           ▼                           ▼
Form 3/4/5 TSVs               Item 1, 1A, 3, 7, 7A         Subsidiary Tree
(Roles & Trades)              (Narrative Sections)        (Jurisdictions)
         │                           │                           │
         └───────────────────────────┼───────────────────────────┘
                                     │
                                     ▼
                        data/staging/*.jsonl
              (Unified relational and graph-ready records)
```

### 3.1. Stage 1: Monthly XBRL RSS Feed Parsing
- **Endpoint**: `https://www.sec.gov/Archives/edgar/monthly/xbrlrss-2022-01.xml`
- **Purpose**: Serves as the canonical filing spine. Each RSS item provides complete metadata (`accessionNumber`, `cikNumber`, `formType`, `filingDate`, `periodOfReport`, `assignedSic`) and a complete document manifest with URLs and sequence numbers.
- **Output**: `data/staging/companies.jsonl`, `data/staging/filings.jsonl`, `data/staging/documents.jsonl`.

### 3.2. Stage 2: Targeted SEC Document Ingestion
- **Source**: SEC EDGAR Archive URLs (`https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/...`)
- **Criteria**: Rather than unselectively mirroring gigabytes of binary and XBRL calculation links, the pipeline fetched:
  1. Sequence 1 primary documents for all `10-K` and `10-K/A` filings (for narrative extraction).
  2. All `EX-21*` exhibits (subsidiary disclosures).
- **Output**: `data/raw/{accession_number}/{filename}` (161 filing folders, 206 document files).

### 3.3. Stage 3: Insider Transactions & Relationships (Form 3, 4, 5)
- **Source**: SEC Insider Transactions Data Sets (`2022q1_form345.zip`).
- **Processing**: Form 3, 4, and 5 filings identify corporate officers, directors, and 10% beneficial owners. Submissions (`SUBMISSION.tsv`) and owners (`REPORTINGOWNER.tsv`) are matched on `ACCESSION_NUMBER` and normalized.
- **Output**: `data/staging/insiders.jsonl`, `data/staging/owner_edges.jsonl`, and `data/staging/form345_issuers.jsonl`.

### 3.4. Stage 4: Narrative Text & Exhibit Extraction
- **Section Parsing**: Converts raw 10-K HTML into a structured document object model, strips script/style tags, normalizes whitespace, and identifies major statutory sections using boundary detection. A longest-block heuristic is applied to disambiguate table-of-contents hits from actual narrative sections.
- **Extracted Items**:
  - `Item 1`: Business Description
  - `Item 1A`: Risk Factors
  - `Item 1B`: Unresolved Staff Comments
  - `Item 2`: Properties
  - `Item 3`: Legal Proceedings
  - `Item 7`: Management's Discussion and Analysis (MD&A)
  - `Item 7A`: Quantitative and Qualitative Disclosures About Market Risk
- **Exhibit 21 Extraction**: Parses tabular and text subsidiary exhibits, extracting subsidiary legal entity names and state/country of incorporation.
- **Auditor Metadata**: Parses XBRL cover-page tags (`dei:AuditorName`, `dei:AuditorLocation`, `dei:AuditorFirmId`).

---

## 4. Repository Directory Structure

```
.
├── README.md                 # Dataset documentation and schema reference
├── .gitignore                # Git exclusions
├── verify_dataset.py         # Integrity validation script (checks all files and rows)
├── example_usage.py          # Standalone python script demonstrating dataset queries
└── data/
    ├── xbrlrss-2022-01.xml   # SEC Monthly XBRL RSS feed (25.4 MB)
    ├── 2022q1_form345.zip    # Raw SEC Form 3/4/5 Insider Dataset archive (14.2 MB)
    ├── form345/              # Uncompressed Form 3/4/5 tab-delimited files
    │   ├── SUBMISSION.tsv
    │   ├── REPORTINGOWNER.tsv
    │   ├── NONDERIV_TRANS.tsv
    │   ├── NONDERIV_HOLDING.tsv
    │   ├── DERIV_TRANS.tsv
    │   ├── DERIV_HOLDING.tsv
    │   ├── FOOTNOTES.tsv
    │   ├── OWNER_SIGNATURE.tsv
    │   ├── insider_transactions_metadata.json
    │   └── insider_transactions_readme.htm
    ├── raw/                  # Downloaded 10-K and EX-21 HTML files (161 folders)
    │   └── {accession}/
    │       └── {filename}.htm
    ├── staging/              # Cleaned, standardized JSONL files
    │   ├── companies.jsonl
    │   ├── filings.jsonl
    │   ├── documents.jsonl
    │   ├── sections.jsonl
    │   ├── subsidiaries.jsonl
    │   ├── insiders.jsonl
    │   ├── owner_edges.jsonl
    │   ├── auditors.jsonl
    │   ├── form345_issuers.jsonl
    │   ├── fetch_manifest.jsonl
    │   └── sic_map.json
    └── models/               # Sentence embedding model weights
        └── all-MiniLM-L6-v2/
            ├── model.safetensors
            ├── config.json
            ├── tokenizer.json
            └── vocab.txt
```

---

## 5. Schema Reference

### 5.1. `data/staging/companies.jsonl` (3,554 rows)
Information about corporate entities registered with the SEC that submitted filings in January 2022.
```json
{
  "cik": 1213037,
  "name": "Cardiff Oncology, Inc.",
  "sic": "2836",
  "sic_description": "BIOLOGICAL PRODUCTS, (NO DISGNOSTIC SUBSTANCES)",
  "fiscal_year_end": "1231",
  "assistant_director": "Office of Life Sciences"
}
```

### 5.2. `data/staging/filings.jsonl` (5,732 rows)
Master catalog of SEC submissions in the period.
```json
{
  "accession_number": "0001213900-22-004524",
  "company_cik": 1213037,
  "form_type": "8-K",
  "filing_date": "2022-01-28",
  "period_of_report": "2022-01-28",
  "acceptance_dt": "2022-01-28 17:15:32",
  "file_number": "001-38379",
  "index_url": "https://www.sec.gov/Archives/edgar/data/1213037/000121390022004524/0001213900-22-004524-index.htm",
  "primary_doc_url": "https://www.sec.gov/Archives/edgar/data/1213037/000121390022004524/ea154743-8k_cardiffonco.htm"
}
```

### 5.3. `data/staging/sections.jsonl` (409 rows, 17.1 MB)
Full narrative section text extracted from 10-K primary documents.
```json
{
  "accession_number": "0001493152-22-002765",
  "item_code": "1A",
  "item_title": "Risk Factors",
  "section_text": "RISK FACTORS An investment in our common stock is subject to risks...",
  "char_len": 46953,
  "company_cik": 1007019,
  "filing_date": "2022-01-31"
}
```
**Item Breakdown**:
- `Item 1` (Business): 111 sections, 4,956,121 characters
- `Item 1A` (Risk Factors): 91 sections, 6,795,504 characters
- `Item 1B` (Unresolved Staff Comments): 5 sections, 189,677 characters
- `Item 2` (Properties): 34 sections, 253,453 characters
- `Item 3` (Legal Proceedings): 18 sections, 53,501 characters
- `Item 7` (MD&A): 115 sections, 4,343,993 characters
- `Item 7A` (Market Risk): 35 sections, 262,880 characters

### 5.4. `data/staging/subsidiaries.jsonl` (3,815 rows)
Mappings between reporting parent corporations and active subsidiaries extracted from Exhibit 21.
```json
{
  "accession_number": "0001628280-22-001406",
  "parent_cik": 1823587,
  "subsidiary_name": "Sky Harbour Holdings LLC",
  "name_normalized": "sky harbour holdings llc",
  "jurisdiction": "Delaware"
}
```

### 5.5. `data/staging/owner_edges.jsonl` (76,260 rows, 30.2 MB)
Insider relationships between reporting persons and issuing companies.
```json
{
  "accession_number": "0001567619-22-007809",
  "owner_cik": 1782298,
  "owner_name": "McClaskey James Paul",
  "issuer_cik": 1807209,
  "issuer_name": "Berkeley Lights, Inc.",
  "relationship": "Officer",
  "is_officer": true,
  "is_director": false,
  "is_ten_pct_owner": false,
  "is_other": false,
  "officer_title": "SVP, Chief Accounting Officer",
  "filing_date": "2022-03-31",
  "period_of_report": "2022-03-30",
  "doc_type": "4"
}
```

### 5.6. `data/staging/auditors.jsonl` (20 rows)
Auditor engagements extracted from 10-K cover-page XBRL declarations.
```json
{
  "accession_number": "0001035443-22-000040",
  "company_cik": 1035443,
  "auditor_name": "Ernst & Young LLP",
  "auditor_location": "Los Angeles, California",
  "pcaob_firm_id": 42,
  "fiscal_year": 2021
}
```

### 5.7. `data/form345/` (TSV Files)
The complete official SEC Form 3/4/5 relational tables:
- `SUBMISSION.tsv` (71,395 rows): Filing header, accession number, issuer CIK, filing dates.
- `REPORTINGOWNER.tsv` (76,260 rows): Owner CIK, name, officer title, address.
- `NONDERIV_TRANS.tsv` (110,327 rows): Non-derivative equity transactions (grants, sales, exercises).
- `NONDERIV_HOLDING.tsv` (33,312 rows): Non-derivative share amounts held after transactions.
- `DERIV_TRANS.tsv` (43,646 rows): Stock options, warrants, and convertible securities traded.
- `DERIV_HOLDING.tsv` (18,770 rows): Derivative securities held.
- `FOOTNOTES.tsv` (171,741 rows): Narrative footnote disclosures clarifying transaction conditions.
- `OWNER_SIGNATURE.tsv` (75,482 rows): Signatory name and execution date.

---

## 6. How to Use the Dataset

### 6.1. Verification
To ensure all records are intact and that no files have been corrupted or truncated:

```bash
python3 verify_dataset.py
```

### 6.2. Running the Example Script
Execute the included usage demo to test querying companies, risk factors, insider networks, and subsidiaries:

```bash
python3 example_usage.py
```

### 6.3. Python Standard Library
Read and filter JSONL files without requiring external packages:

```python
import json

# Stream Item 1A Risk Factors
with open("data/staging/sections.jsonl", "r", encoding="utf-8") as fh:
    for line in fh:
        section = json.loads(line)
        if section.get("item_code") == "1A":
            print(f"CIK: {section['company_cik']}, Length: {section['char_len']:,} chars")
```

### 6.4. Pandas Integration
Load staging files directly into DataFrames:

```python
import pandas as pd

# Load companies and filings
df_companies = pd.read_json("data/staging/companies.jsonl", lines=True)
df_filings = pd.read_json("data/staging/filings.jsonl", lines=True)

# Merge filings with company metadata
merged = df_filings.merge(df_companies, left_on="company_cik", right_on="cik")
print(merged[["accession_number", "name", "form_type", "filing_date"]].head())
```

### 6.5. Relational Databases (SQLite / PostgreSQL)
Load into SQLite using Python:

```python
import sqlite3
import json

conn = sqlite3.connect("edgar.db")
cur = conn.cursor()

cur.execute("""
    CREATE TABLE IF NOT EXISTS company (
        cik INTEGER PRIMARY KEY,
        name TEXT,
        sic TEXT,
        sic_description TEXT,
        fiscal_year_end TEXT
    )
""")

with open("data/staging/companies.jsonl", "r") as f:
    for line in f:
        c = json.loads(line)
        cur.execute("INSERT OR REPLACE INTO company VALUES (?, ?, ?, ?, ?)",
                    (c["cik"], c["name"], c.get("sic"), c.get("sic_description"), c.get("fiscal_year_end")))

conn.commit()
print("Loaded companies into SQLite.")
```

### 6.6. Graph Databases (Neo4j / NetworkX)
The staging data directly maps to entity nodes and relationships:
- Nodes:
  - `:Company {cik, name, sic}`
  - `:Person {owner_cik, name}`
  - `:Filing {accession_number, form_type, filing_date}`
  - `:Subsidiary {name, jurisdiction}`
  - `:AuditFirm {name, pcaob_firm_id}`
- Edges:
  - `(:Person)-[:OFFICER_OF {title, accession_number}]->(:Company)`
  - `(:Person)-[:DIRECTOR_OF {accession_number}]->(:Company)`
  - `(:Company)-[:FILED]->(:Filing)`
  - `(:Subsidiary)-[:SUBSIDIARY_OF {accession_number}]->(:Company)`
  - `(:Company)-[:AUDITED_BY {fiscal_year}]->(:AuditFirm)`

---

## 7. Data License & Citation

All raw SEC data is published by the U.S. Securities and Exchange Commission and is in the public domain. When using or citing this dataset in research or software, please reference:

- SEC EDGAR (Electronic Data Gathering, Analysis, and Retrieval system): `https://www.sec.gov/edgar`
- SEC Insider Transactions Data Sets: `https://www.sec.gov/files/structureddata/data/insider-transactions-data-sets`
- Repository Maintainer: Fakabbir Amin (fakabbir@gmail.com)
