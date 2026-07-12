# DocuMind AI

DocuMind AI is a multilingual document intelligence platform that combines document processing, OCR, semantic search, vector databases, and Retrieval-Augmented Generation.

The project allows users to upload documents, extract their content, split the extracted text into semantic chunks, index those chunks in a vector database, and ask questions over the indexed documents with source-based answers.

This project is designed as a production-style AI portfolio project focused on RAG systems, document intelligence, and applied LLM workflows.

---

## Project Overview

DocuMind AI provides a complete backend pipeline for document-based question answering:

1. User authentication
2. Document upload
3. Text extraction from PDF and DOCX files
4. OCR support for images and scanned PDFs
5. Chunking extracted text into retrieval-ready segments
6. Embedding generation using a local multilingual model
7. Vector indexing with Qdrant
8. Semantic search over indexed documents
9. Grounded answer generation with source references

---

## Current Status

The project currently supports:

- JWT authentication
- Authenticated document upload
- PDF text extraction
- DOCX text extraction
- OCR for PNG/JPG images
- OCR fallback for scanned PDFs
- Strong error handling for invalid or corrupted files
- Document processing status workflow
- Text chunking with metadata
- Local multilingual embeddings
- Qdrant vector indexing
- Semantic search over indexed chunks
- Grounded draft answer endpoint with sources

External LLM integration with providers such as Mistral API or OpenAI API is planned as the next step.

---

## Core Features

### Authentication

Users can register, log in, and access protected document endpoints using JWT authentication.

### Document Upload

Supported file types:

- PDF
- DOCX
- PNG
- JPG / JPEG

The backend validates file type, content type, and maximum upload size.

### Text Extraction

The system extracts text from:

- Digital PDFs using PyMuPDF
- DOCX documents using python-docx
- Images using Tesseract OCR
- Scanned PDFs using OCR fallback

### Error Handling

The system handles:

- Unsupported file formats
- Corrupted files
- Empty documents
- Extraction failures
- Large files
- Missing files

Instead of crashing, the backend returns clear error messages and updates the document status.

### Chunking

Extracted text is split into chunks suitable for semantic search.

Each chunk stores:

- Document ID
- Page number
- Chunk index
- Text content

### Embeddings

The project uses a local multilingual embedding model:

```txt
intfloat/multilingual-e5-small
```

This model was selected because it supports multilingual semantic search and works locally without API costs.

The embedding vector size is:

```txt
384
```

### Vector Database

Qdrant is used to store document vectors.

Each indexed vector includes metadata:

- Document ID
- User ID
- Page number
- Chunk index
- Text
- Source filename
- Document chunk ID

### Semantic Search

Users can ask questions over indexed documents.

The system converts the user question into an embedding, searches Qdrant, and retrieves the most relevant chunks.

### Grounded Answer Endpoint

The `/answer` endpoint retrieves relevant context and returns a grounded draft answer with source references.

A full LLM-generated answer will be added through an external LLM provider such as Mistral API or OpenAI API.

---

## Tech Stack

### Backend

- Python 3.11
- FastAPI
- SQLAlchemy
- Pydantic
- JWT authentication

### Databases

- PostgreSQL
- Qdrant vector database

### AI / NLP

- Sentence Transformers
- intfloat/multilingual-e5-small
- Tesseract OCR
- PyMuPDF
- python-docx

### Infrastructure

- Docker
- Docker Compose

---

## Project Architecture

```txt
User
 |
 |--> Register / Login
 |
 |--> Upload document
 |
 |--> Process document
        |
        |--> Extract text
        |--> OCR if needed
        |--> Create chunks
        |--> Store chunks in PostgreSQL
 |
 |--> Index document
        |
        |--> Generate embeddings
        |--> Store vectors in Qdrant
 |
 |--> Ask question
        |
        |--> Generate query embedding
        |--> Search Qdrant
        |--> Retrieve relevant chunks
        |--> Return answer with sources
```

---

## API Endpoints

### Authentication

```txt
POST /auth/register
POST /auth/login
GET  /auth/me
```

### Documents

```txt
POST /documents/upload
GET  /documents/{document_id}/status
POST /documents/{document_id}/process
GET  /documents/{document_id}/chunks
POST /documents/{document_id}/index
```

### Query

```txt
POST /query
```

Returns the most relevant chunks from indexed documents.

### Answer

```txt
POST /answer
```

Returns a grounded draft answer with source references.

### System

```txt
GET /health
GET /db-health
GET /
```

---

## Environment Variables

Create a `.env` file from `.env.example`:

```bash
copy .env.example .env
```

Main configuration values:

```env
DATABASE_URL=postgresql://documind:documind_password@postgres:5432/documind_db
QDRANT_URL=http://qdrant:6333

SECRET_KEY=change_this_secret_key_in_production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

UPLOAD_DIR=uploads
MAX_UPLOAD_SIZE_MB=20

EMBEDDING_PROVIDER=local
EMBEDDING_MODEL_NAME=intfloat/multilingual-e5-small
EMBEDDING_VECTOR_SIZE=384

QDRANT_HOST=qdrant
QDRANT_PORT=6333
QDRANT_COLLECTION_NAME=documind_chunks

LLM_PROVIDER=mistral
MISTRAL_API_KEY=
MISTRAL_MODEL=mistral-small-latest
MISTRAL_API_URL=https://api.mistral.ai/v1/chat/completions
```

Do not commit real API keys to GitHub.

---

## Run the Project

Build and start the services:

```bash
docker compose up --build
```

Run in detached mode:

```bash
docker compose up -d
```

Stop the services:

```bash
docker compose down
```

Backend URL:

```txt
http://localhost:8000
```

API documentation:

```txt
http://localhost:8000/docs
```

Health check:

```txt
http://localhost:8000/health
```

---

## Basic Workflow

1. Register a user.
2. Log in and get an access token.
3. Upload a document.
4. Process the document.
5. Check generated chunks.
6. Index the document in Qdrant.
7. Ask semantic questions using `/query`.
8. Generate grounded draft answers using `/answer`.

---

## Development Roadmap

### Completed

- R1 — Project foundation
- R2 — PostgreSQL connection
- R3 — Database models and schemas
- R4 — JWT authentication
- R5 — Authenticated document upload
- R6 — PDF and DOCX text extraction
- R7 — Document processing status workflow
- R8 — OCR and robust error handling
- R9 — Document chunking system
- R10 — Embedding model decision
- R11 — Qdrant indexing
- R12 — Semantic search
- R13A — Grounded answer endpoint structure

### In Progress

- R13B — External LLM provider integration

### Planned

- Mistral API or OpenAI API integration
- Local LLM support with Ollama or LM Studio
- RAG answer generation with strict context grounding
- Evaluation pipeline
- Admin dashboard
- Next.js frontend
- Deployment-ready configuration

---

## Project Goal

The goal of DocuMind AI is to demonstrate practical skills in:

- Backend engineering
- AI application development
- Retrieval-Augmented Generation
- OCR and document processing
- Vector search
- Semantic search
- LLM application architecture
- Production-style project organization

This project is intended to be used as a professional AI portfolio project.