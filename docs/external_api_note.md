# External API reproducibility note

The LLM-assisted extraction/classification component is optional. It is the only part of the demo that depends on a third-party hosted model.

The experiments described in the associated paper used the model identifier reported in the paper at the time of experimentation. Hosted providers can later retire model identifiers or change access tiers. For that reason, the application reads the current demo model from the `GROQ_MODEL` environment variable rather than embedding a fixed provider model in the code.

This separation is intentional:

- the **experimental record** remains tied to the model/version reported in the paper;
- the **live demonstration** can use a currently available compatible model;
- the rule-based morphological generator, SQLite exploration, ProLMF validation, RDF fixture, and SPARQL query tests remain reproducible without an external LLM.
