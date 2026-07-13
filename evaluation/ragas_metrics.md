# RAGAS Metrics for DocuMind AI

This document describes the evaluation metrics planned for measuring the quality of the DocuMind AI RAG pipeline.

## Objective

The goal of R19 is to define clear metrics for evaluating both retrieval quality and answer generation quality.

DocuMind AI uses a Retrieval-Augmented Generation pipeline. This means the system must be evaluated in two parts:

1. Retrieval quality: did the system retrieve the right context?
2. Generation quality: did the LLM generate a faithful and relevant answer using that context?

## Metrics

### 1. Context Precision

Context Precision measures whether the retrieved chunks are relevant to the question and whether the most useful chunks appear near the top of the retrieved results.

High context precision means the retriever is not returning too many irrelevant chunks.

Used for evaluating:

- semantic search;
- BM25 keyword search;
- reciprocal rank fusion;
- reranker quality.

### 2. Context Recall

Context Recall measures whether the retrieved chunks contain the information needed to answer the question.

High context recall means the system successfully retrieved the evidence required to answer.

Used for evaluating:

- whether the correct source was retrieved;
- whether the correct page was retrieved;
- whether important evidence was missed.

### 3. Faithfulness

Faithfulness measures whether the generated answer is supported by the retrieved context.

High faithfulness means the model is not hallucinating and is staying grounded in the document.

Used for evaluating:

- hallucination risk;
- source-grounded generation;
- answer reliability.

### 4. Answer Relevance

Answer Relevance measures whether the generated answer directly answers the user question.

High answer relevance means the answer is focused, useful, and aligned with the question.

Used for evaluating:

- response quality;
- answer focus;
- usefulness of the LLM output.

## Evaluation Dataset Fields

The evaluation dataset contains:

- id;
- question;
- expected_answer;
- expected_source_filename;
- expected_page;
- difficulty;
- type.

The dataset includes several question types:

- fact;
- summary;
- reasoning;
- negative.

Negative questions are used to verify that the system refuses to answer when the answer is not present in the document.

## Future R20 Evaluation Script

In R20, an evaluation script will be created to:

- load the evaluation dataset;
- call the DocuMind AI answer endpoint;
- collect generated answers;
- collect retrieved contexts;
- run RAGAS metrics;
- save results as JSON;
- save results as CSV;
- generate a short evaluation summary.

## Expected Output

The final evaluation output should help compare different retrieval pipelines:

- semantic search only;
- hybrid search;
- hybrid search plus reranker.

This will make DocuMind AI stronger than a basic RAG demo because the system will include measurable retrieval and answer-quality evaluation.