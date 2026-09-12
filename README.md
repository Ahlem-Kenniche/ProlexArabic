# ProlexArabic — EACL 2027 Demonstration Package

**ProlexArabic** is a reproducible toolkit for Arabic proper-name exploration, rule-based morphological generation, ProLMF serialization, and semantic publication with RDF/OntoLex-Lemon/SKOS.

This repository accompanies the demo paper:

> *ProlexArabic: A Reproducible Toolkit for Arabic Proper-Name Generation and Semantic Publication*

**Authors:** Ahlem Kenniche, Zekri Lougmiri, Denis Maurel  
**Ahlem Kenniche affiliation:** Department of Computer Science, Université Oran 1 Ahmed Ben Bella, Oran, Algeria.

## 60-second reproduction check

Recommended: Python 3.11 or 3.12.

```bash
python -m venv .venv
source .venv/bin/activate      # Linux/macOS
# .venv\Scripts\activate   # Windows
pip install -r requirements.txt
python scripts/smoke_test.py
```

The smoke test is **offline and self-contained**: it checks the bundled sample SQLite database (`data_sample/prolexbase_sample.db`), Turtle files, CQ1–CQ10 SPARQL queries, and ProLMF XML/XSD validation. It does not require MySQL or a Groq key.

## Run the English demo

```bash
streamlit run app/streamlit_app.py
```

The application provides three main views:

1. **ProLexBase** — browse Arabic proper names and their stored linguistic information;
2. **Rule System** — generate Arabic inflectional/derivational forms using explicit linguistic rules;
3. **Extraction & Classification** — optional LLM-assisted extraction/classification, followed by the same rule-based generation pipeline.

The first two components work without any external API. By default, the Streamlit application reads the bundled sample database at `data_sample/prolexbase_sample.db`. A different local SQLite database can be selected with the `PROLEXARABIC_DB` environment variable.

## Optional Groq configuration

Do **not** place API keys in source files. Set them locally instead:

```bash
export GROQ_API_KEY="your_key_here"
export GROQ_MODEL="openai/gpt-oss-120b"
```

On Windows CMD:

```bat
set GROQ_API_KEY=your_key_here
set GROQ_MODEL=openai/gpt-oss-120b
```

Hosted model availability changes over time, so the live demo model is configurable. The experimental model reported in the paper remains part of the experimental record; the live API model is not assumed to be permanently available.

## Repository structure

```text
ProlexArabic/
├── app/                 # English Streamlit demo
├── generator/           # Arabic generation rules and tests
├── prolmf/              # ProLMF exporter, XSD schema, XML validator
├── rdf/                 # RDF generator + curated SPARQL reproduction fixture
├── ontology/            # OntoLex-Lemon/SKOS ontology mapping
├── sparql/              # Competency queries CQ1-CQ10 (+ auxiliary queries)
├── data_sample/         # Bundled sample SQLite database + CSV samples
├── outputs/             # Expected examples and full-run quantitative statistics
├── docs/                # Detailed reproduction guide
├── scripts/             # Smoke test, query runner, optional utilities
├── config.example.yaml  # Safe template for optional local MySQL regeneration
├── requirements.txt
├── LICENSE
└── CITATION.cff
```

## RDF / SPARQL reproducibility

`rdf/sample.ttl` is a **curated reproduction fixture**, not the full RDF corpus. It is intentionally small and contains enough representative triples for every public competency query `CQ1`–`CQ10` to execute and return a result.

```bash
python scripts/run_sample_queries.py
```

Full-corpus statistics are stored separately in `outputs/quantitative_results.csv`; they must not be recomputed from the curated fixture.

## ProLMF validation

```bash
python prolmf/validate_xml.py
```

This validates `outputs/sample_prolmf_excerpt.xml` against `prolmf/ProLMF_4.xsd`.

## Full-data regeneration (optional)

The complete SQL→RDF and SQL→ProLMF pipelines require a local Prolexbase MySQL database. Copy `config.example.yaml` to `config.yaml`, add local credentials, then run:

```bash
python rdf/rdf_generator.py --config config.yaml
python prolmf/prolmf_exporter.py
```

See `docs/reproduction_guide.md` for the complete workflow and reproducibility boundaries.

## Security and local configuration

This EACL demonstration package is non-anonymous. Author information may therefore appear in the repository. Private credentials are **not** distributed: local secrets such as `config.yaml`, `.env`, and Streamlit secrets are ignored by Git.

## License

Source code is released under the MIT License. See `LICENSE-PROLEXBASE` and the documentation for the status of redistributed Prolexbase data.

