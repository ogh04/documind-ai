# DocuMind AI Evaluation

This folder contains evaluation assets for measuring the quality of the DocuMind AI RAG pipeline.

## Purpose

The evaluation dataset is used to test whether the system can retrieve the correct document chunks, answer questions using only the provided document context, return the correct source filename, return the correct source page, and reject questions whose answers are not present in the document.

## Dataset

Current dataset: evaluation/datasets/rag_eval_dataset.json

Each evaluation item contains: id, question, expected_answer, expected_source_filename, expected_page, difficulty, and type.

Example item:

{
  "id": "eval_001",
  "question": "What is the document about?",
  "expected_answer": "...",
  "expected_source_filename": "Cookie_Beamer_Theme.pdf",
  "expected_page": 1,
  "difficulty": "easy",
  "type": "summary"
}

## Question Types

- fact: direct factual question.
- summary: summary-style question.
- reasoning: question requiring light interpretation from the document.
- negative: question whose answer is not present in the document.

## Notes

This is an initial seed evaluation dataset. It will later be expanded with richer documents and stronger test cases.

Future evaluation rounds will add RAGAS metrics, context precision, context recall, faithfulness, answer relevance, and JSON/CSV result exports.