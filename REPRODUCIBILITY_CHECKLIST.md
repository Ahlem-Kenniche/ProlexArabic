# Reviewer Reproducibility Checklist

The package is designed so that the core review checks do not require private credentials or a database server.

## Offline checks

After installing `requirements.txt`, run:

```bash
python scripts/smoke_test.py
```

A successful run confirms:

- bundled SQLite data can be read;
- the Arabic rule system produces a known nisba example (`مصر` → `مصري`);
- the OntoLex/SKOS ontology parses as Turtle;
- the curated RDF fixture parses as Turtle;
- competency queries CQ1-CQ10 all execute and return at least one result;
- the sample ProLMF XML validates against the bundled XSD.

## Demo

```bash
streamlit run app/streamlit_app.py
```

ProLexBase browsing and rule-based generation are local. LLM-assisted extraction/classification is optional and requires a Groq API key supplied at runtime or through `GROQ_API_KEY`.

## Full-data regeneration

Full SQL→RDF and SQL→ProLMF regeneration requires a local Prolexbase MySQL database and a private `config.yaml` copied from `config.example.yaml`. The full RDF dump is not bundled because of its size. Full-run aggregate statistics are provided under `outputs/`.

## Package hygiene

- no API key is embedded in source code;
- local MySQL credentials are not embedded in the bundled SQLite database;
- `.gitignore` excludes common local secret/configuration files.
