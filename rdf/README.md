# RDF files

- `sample.ttl`: a **curated, compact reproduction fixture** built to exercise the public competency queries `CQ1`–`CQ10`. It is not the full corpus and must not be used to recompute corpus-level statistics.
- `rdf_generator.py`: MySQL-to-RDF/Turtle converter for the full Prolexbase database.
- `prolexbase-full.ttl`: expected name of the complete generated RDF dataset. It is not included in this demonstration package because of its size.

## Quick query check

From the repository root:

```bash
python scripts/run_sample_queries.py
```

This command loads `sample.ttl` with `rdflib` and executes all ten competency queries. Each query should return at least one row.

## Full-data generation

Copy `config.example.yaml` to `config.yaml`, add your local MySQL credentials, and run:

```bash
python rdf/rdf_generator.py --config config.yaml
```

For archival distribution of the complete RDF file, use a research-data host such as Zenodo, ORTOLANG, Figshare, Hugging Face Datasets, or Git LFS as appropriate.
