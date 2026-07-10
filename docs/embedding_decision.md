# R10 — Embedding Model Decision

## Objective

Choose the embedding model that will convert document chunks and user questions into numerical vectors for semantic search.

## Options Considered

### Lightweight Local Option

`sentence-transformers/all-MiniLM-L6-v2`

This model is lightweight and fast, but it is mainly optimized for English.

### Stronger Local Option

`BAAI/bge-small-en-v1.5`

This model is strong for English semantic search, but it is not the best first choice for multilingual documents.

### Multilingual Local Option

`intfloat/multilingual-e5-small`

This model supports multilingual semantic search and is suitable for French, English, and Arabic documents.

### API Option

OpenAI embeddings or Mistral embeddings can provide strong results, but they require API keys and may generate usage costs.

## Selected Model

The initial embedding model selected for DocuMind AI is:

`intfloat/multilingual-e5-small`

## Provider

`local`

## Vector Size

`384`

## Reason for the Decision

DocuMind AI needs to support multilingual documents, especially French, English, and Arabic.

The first version should also work without API costs.

Therefore, the selected model is:

- multilingual
- local
- free to use
- lightweight enough for the first version
- suitable for semantic search
- appropriate for a portfolio-grade RAG project

## E5 Formatting Rule

For document chunks, the text should be embedded with the prefix:

`passage:`

For user questions, the text should be embedded with the prefix:

`query:`

Example document chunk:

`passage: This document explains the classification model.`

Example user question:

`query: What model was used for classification?`

This formatting improves retrieval quality because E5 models are trained to distinguish between passages and queries.

## Future Extension

The architecture can later support API-based embedding providers such as OpenAI embeddings or Mistral embeddings.

For the first version, the local multilingual model is preferred to avoid API costs.