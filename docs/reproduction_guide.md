# Reproduction Guide

This package supports two levels of reproduction:

1. **Self-contained review reproduction** — no MySQL server and no API key required. This validates the Streamlit data layer, Arabic rule system, ProLMF/XSD artifact, RDF/Turtle artifacts, and SPARQL competency queries.
2. **Full-data regeneration** — optional, requires a local Prolexbase MySQL database. The external Groq API is required only for the optional LLM-assisted extraction/classification component.

## 1. Environment

Recommended: Python 3.11 or 3.12.

```bash
python -m venv .venv
source .venv/bin/activate          # Linux/macOS
# .venv\Scripts\activate       # Windows PowerShell/CMD
pip install -r requirements.txt
```

## 2. One-command offline smoke test

From the repository root:

```bash
python scripts/smoke_test.py
```

It checks:

- the bundled SQLite demo database;
- Turtle syntax for the ontology and RDF sample;
- execution of `CQ1`–`CQ10` on the curated RDF fixture;
- ProLMF XML validation against `ProLMF_4.xsd`.

No network connection, API key, or MySQL server is needed for this test.

## 3. Run the English Streamlit demo

```bash
streamlit run app/streamlit_app.py
```

The bundled `data_sample/prolexbase_sample.db` is the reproducibility database used by the local exploration and rule-based generation views. MySQL-dependent semantic-relation views are optional and degrade gracefully when no MySQL configuration is present.

### Optional LLM-assisted extraction/classification

The extraction/classification page calls Groq only when the user provides a key. Never commit a key to the repository.

Linux/macOS:

```bash
export GROQ_API_KEY="your_key_here"
export GROQ_MODEL="openai/gpt-oss-120b"
```

Windows CMD:

```bat
set GROQ_API_KEY=your_key_here
set GROQ_MODEL=openai/gpt-oss-120b
```

The demo model is configurable because hosted model availability can change. The model used for the experiments reported in the paper should be cited separately from the currently available live-demo model.

## 4. ProLMF XML validation

The review package contains:

- `prolmf/ProLMF_4.xsd`;
- `outputs/sample_prolmf_excerpt.xml`;
- `prolmf/validate_xml.py`.

Run:

```bash
python prolmf/validate_xml.py
```

To validate another generated XML file:

```bash
python prolmf/validate_xml.py --xml outputs/prolmf_full.xml
```

## 5. RDF/Turtle and SPARQL

For a fast, self-contained check:

```bash
python scripts/run_sample_queries.py
```

`rdf/sample.ttl` is a curated query fixture designed specifically to exercise `CQ1`–`CQ10`. The expected examples for the full corpus are documented in `outputs/competency_question_outputs.md`.

You can also open:

```text
ontology/prolexbase-ontolex.ttl
rdf/sample.ttl
```

in Protégé, GraphDB, or Apache Jena tools.

## 6. Optional full-data RDF regeneration

A full relational-to-RDF regeneration requires a local MySQL copy of Prolexbase.

```bash
cp config.example.yaml config.yaml    # Linux/macOS
# copy config.example.yaml config.yaml # Windows
```

Edit only your local `config.yaml`, then run:

```bash
python rdf/rdf_generator.py --config config.yaml
```

Optional custom output:

```bash
python rdf/rdf_generator.py --config config.yaml --output rdf/prolexbase-full.ttl
```

The full generated RDF file is intentionally not bundled because of its size. Corpus-level statistics from the full generation are preserved in `outputs/quantitative_results.csv`.

## 7. Optional full-data ProLMF export

Using the same local `config.yaml`:

```bash
python prolmf/prolmf_exporter.py
```

or point to another configuration file:

```bash
PROLEX_CONFIG=/path/to/config.yaml python prolmf/prolmf_exporter.py
```

The default output path is `outputs/prolmf_full.xml`.

## 8. Reproducibility boundaries

- **Offline/reviewer reproducible:** bundled SQLite exploration, rule-based morphology, XML/XSD validation, ontology parsing, RDF fixture parsing, and CQ1–CQ10 execution.
- **Requires local Prolexbase MySQL data:** complete RDF regeneration, complete ProLMF export, and MySQL-backed semantic relations in the interface.
- **Requires an external API:** LLM-assisted extraction/classification only. Hosted model identifiers may be deprecated by the provider; use `GROQ_MODEL` to select an available model.
