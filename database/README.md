# Full Prolexbase database

The complete Prolexbase MySQL database is **not distributed in this public repository**.

For reviewer reproduction, use the curated SQLite and CSV sample provided under `data_sample/`. This sample is sufficient for the Streamlit demo, smoke test, RDF query fixture, and the documented reproducibility workflow.

The SQL→RDF and SQL→ProLMF exporters can also be run against an authorized local Prolexbase MySQL installation. To do so, copy `config.example.yaml` to `config.yaml` and provide local connection settings. Do not commit credentials or a full database dump.

Prolexbase data remain subject to the terms described in `LICENSE-PROLEXBASE`.
