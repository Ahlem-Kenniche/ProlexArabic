# Evaluation, scope, and reviewer-facing clarifications

This document clarifies what the public EACL demonstration package does, what is directly reproducible from this repository, and which results refer to the full internal Prolexbase-Arabic processing pipeline.

## Current demo architecture

The public Streamlit demo exposes three main functions:

1. **ProLexBase exploration** over the bundled SQLite demonstration subset;
2. **deterministic Arabic generation** using explicit category-aware rules and lexical exceptions;
3. **optional Extraction & Classification**, where a Groq-compatible external LLM is used to extract candidate Arabic proper names and assign ProLexBase semantic types. The resulting type can be reviewed/edited before the deterministic generation rules are applied.

The current demo **does not require CAMeL Tools at runtime**. The LLM-dependent path is deliberately isolated: database exploration, morphological generation, ProLMF validation, RDF parsing, and SPARQL competency tests remain executable without an external API.

## Reproducible checks included in this repository

The bundled package supports the following reviewer checks without private data or credentials:

- SQLite sample-database access;
- a known Arabic nisba generation check (`مصر` → `مصري`);
- Turtle parsing of the OntoLex-Lemon/SKOS ontology and curated RDF fixture;
- execution of competency queries `CQ1`–`CQ10` over the curated fixture;
- ProLMF XML validation against the bundled `ProLMF_4.xsd` schema.

Run all of these with:

```bash
python scripts/smoke_test.py
```

The curated RDF and SQLite samples are intentionally small reviewer fixtures. They are **not** the full Prolexbase database and should not be used to recompute full-resource statistics.

## Evaluation evidence reported with the associated submission

The associated EACL submission distinguishes several complementary levels of evidence rather than treating a small demonstration sample as a resource-wide accuracy estimate:

- a **2,000-prolexeme consistency audit** for large-scale structural checking;
- a **family-level linguistic assessment of 235 complete nisba paradigms**, with 226 correct, 8 incorrect, and 1 doubtful family (96.6% over unambiguous decisions);
- explicit error analysis focusing on lexicalized nisbas, terminal-form transformations, and compound-name base selection;
- formal ProLMF/XSD validation;
- RDF/SPARQL competency-query validation;
- a downstream NER experiment reported separately in the paper, not as part of the runtime architecture of the Streamlit demo.

These levels answer different questions: linguistic plausibility, structural consistency, standards conformance, semantic retrievability, and downstream usefulness.

## Positioning relative to general Arabic NLP tools and LLMs

ProlexArabic is not intended to replace general Arabic tokenizers, analyzers, NER systems, or LLMs. Its distinctive role is to maintain traceable proper-name lexical families linked to stable Prolexbase pivots, apply explicit Arabic generation rules, and publish the resulting lexical structure through ProLMF and RDF/OntoLex-Lemon/SKOS.

The optional LLM path is used for contextual extraction and semantic typing in the interactive demo. Morphological generation, pivot-based identity, serialization, validation, and SPARQL publication remain explicit and inspectable.

## Known limitations

- The public repository contains a demonstration subset rather than the full Prolexbase database.
- The extraction/classification view depends on a third-party hosted LLM and therefore requires a user-supplied API key and a currently available compatible model.
- Linguistic evaluation is stronger for complete nisba families than for the resource as a whole; the repository does not claim that the reported family-level score is a global accuracy figure for all 15,749 Arabic prolexemes.
- Modern Standard Arabic is the primary target; dialectal and highly variable orthographic realizations are not comprehensively modeled.
- The current public package does not provide a formal interface-usability study.
