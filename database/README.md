# Database notes

The English Streamlit demo uses the bundled read-only reproducibility database at `data_sample/prolexbase_sample.db` by default.

The review package does not require a MySQL server for the main demo, rule-based generation, RDF fixture, SPARQL checks, or ProLMF validation. A local MySQL copy of Prolexbase is needed only for complete RDF/ProLMF regeneration and optional MySQL-backed semantic-relation views.

For full regeneration, copy `config.example.yaml` to `config.yaml` and enter only local credentials. `config.yaml` is ignored by Git and must not be committed.
