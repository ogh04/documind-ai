# DocuMind AI

DocuMind AI is a multilingual document intelligence platform based on OCR, semantic search, vector databases, and Retrieval-Augmented Generation.

The goal of this project is to build a production-style AI portfolio project that allows users to upload documents, extract their content, index them semantically, and ask questions with source-based answers.

## Current Status

R1 — Project initialization.

This phase includes:

* FastAPI backend foundation
* Docker Compose setup
* PostgreSQL service
* Qdrant vector database service
* Health check endpoint
* Initial project structure

## Tech Stack

* Python 3.11
* FastAPI
* PostgreSQL
* Qdrant
* Docker
* Docker Compose

## Future Phases

* Authentication with JWT
* Document upload
* PDF and DOCX text extraction
* OCR
* Chunking
* Embeddings
* RAG pipeline
* Next.js frontend

## Run the Project

Create the environment file:

```bash
copy .env.example .env
```

Build and run the project:

```bash
docker compose up --build
```

Backend URL:

```txt
http://localhost:8000
```

Health check:

```txt
http://localhost:8000/health
```

API documentation:

```txt
http://localhost:8000/docs
```
