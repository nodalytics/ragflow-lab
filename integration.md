# RAGFlow: what it is, what it costs, when it is worth it

An assessment of [RAGFlow](https://github.com/infiniflow/ragflow), made before hosting it. A first trial ran
v0.21.1 in May 2026; the lab now runs the latest release (v1.0.0 on 2026-11-23), with the setup in
[README.md](README.md).

## What it is

A self-hosted retrieval engine. It takes documents in (PDF, Word, images, tables), cuts them into pieces by their
layout (with OCR for scans), embeds and indexes them, and answers questions over them with a citation for every
answer. Strengths over a bare vector database:

- **Layout-aware chunking:**
  - tables, multi-column PDFs and scanned pages come through intact;
  - plain fixed-size chunking breaks them.
- **Citations:** every answer points back to the page and passage it came from.
- **Any model:**
  - chat and embedding models are pluggable;
  - local servers (Ollama, or any OpenAI-compatible server) and hosted APIs both work.
- **Its own interfaces:**
  - a web UI;
  - an HTTP API;
  - an OpenAI-compatible chat endpoint per assistant;
  - an MCP endpoint for coding agents.

## What it runs

| Service | Role |
|---|---|
| RAGFlow server | Web UI, API, ingestion workers |
| MySQL | Accounts, datasets, documents |
| Elasticsearch (or Infinity, OpenSearch) | The vector and full-text index |
| MinIO | The uploaded files |
| Kvrocks / Redis, NATS | Cache and queues (v1.0) |
| Text-embeddings service | Embeddings, since v0.22 stopped bundling embedding models |

At rest, the stack takes a few GB of memory plus the embedding model, and about 8 GB of images. The index takes
roughly 5 GB per 10,000 pages.

## Lessons from the trial

- **Pick the provider type that matches the model server.** RAGFlow's "Ollama" provider calls Ollama's native
  `/api/chat`. A server that only speaks OpenAI's API (vLLM, SGLang, LM Studio and others) must be added as
  "OpenAI-API-Compatible", or every call fails with a connection error. Leave headroom under the model's context
  for its thinking.
- **v0.21 bundled embedding models in its full image (~9 GB); v0.22 and later do not.** Add an embedding service:
  this repo runs the text-embeddings service on the CPU.
- **Sign-up is open by default and the admin password is `admin`.** On a public address, close sign-up and set the
  password before the first start; `ragflow.sh` does both.

## When it is worth it

RAGFlow is heavy: half a dozen services for one feature. A lighter path covers plain-text documents:
- `pgvector` on an existing Postgres;
- simple chunking;
- an embedding model.

RAGFlow earns its place when any of these hold:
- the documents are image-heavy or scanned, or full of tables;
- the collection grows past roughly ten thousand documents;
- people need the web UI, the citations and dataset management, not just an API.

Measure whether the agents and people using it actually query it, before scaling it further.
