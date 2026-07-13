from __future__ import annotations

import csv
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_DATASET_PATH = (
    PROJECT_ROOT / "evaluation" / "datasets" / "cxr_report_eval_dataset.json"
)
RESULTS_DIR = PROJECT_ROOT / "evaluation" / "results"

DEFAULT_API_BASE_URL = "http://localhost:8000"
DEFAULT_DOCUMENT_ID = 6

NO_ANSWER_MESSAGE = "I cannot find this information in the provided document."


def load_environment() -> None:
    env_path = PROJECT_ROOT / ".env"

    if env_path.exists():
        load_dotenv(env_path)


def get_api_base_url() -> str:
    return os.getenv("DOCUMIND_API_BASE_URL", DEFAULT_API_BASE_URL).rstrip("/")


def get_dataset_path() -> Path:
    dataset_path = os.getenv("DOCUMIND_EVAL_DATASET_PATH")

    if not dataset_path:
        return DEFAULT_DATASET_PATH

    path = Path(dataset_path)

    if path.is_absolute():
        return path

    return PROJECT_ROOT / path


def get_document_id() -> int | None:
    document_id = os.getenv("DOCUMIND_DOCUMENT_ID")

    if not document_id:
        return DEFAULT_DOCUMENT_ID

    return int(document_id)


def load_dataset(dataset_path: Path) -> list[dict[str, Any]]:
    if not dataset_path.exists():
        raise FileNotFoundError(f"Evaluation dataset not found: {dataset_path}")

    with dataset_path.open("r", encoding="utf-8") as file:
        dataset = json.load(file)

    if not isinstance(dataset, list):
        raise ValueError("Evaluation dataset must be a JSON list.")

    return dataset


def get_auth_token(api_base_url: str) -> str:
    existing_token = os.getenv("DOCUMIND_AUTH_TOKEN")

    if existing_token:
        return existing_token

    email = os.getenv("DOCUMIND_EMAIL")
    password = os.getenv("DOCUMIND_PASSWORD")

    if not email or not password:
        raise RuntimeError(
            "Missing authentication. Set DOCUMIND_AUTH_TOKEN or set "
            "DOCUMIND_EMAIL and DOCUMIND_PASSWORD before running evaluation."
        )

    login_url = f"{api_base_url}/auth/login"

    response = requests.post(
        login_url,
        data={
            "username": email,
            "password": password,
        },
        timeout=60,
    )

    response.raise_for_status()

    token_payload = response.json()
    access_token = token_payload.get("access_token")

    if not access_token:
        raise RuntimeError("Login succeeded but no access_token was returned.")

    return access_token


def call_answer_endpoint(
    api_base_url: str,
    token: str,
    question: str,
    document_id: int | None = None,
    top_k: int = 5,
) -> dict[str, Any]:
    url = f"{api_base_url}/answer"

    payload: dict[str, Any] = {
        "question": question,
        "top_k": top_k,
    }

    if document_id is not None:
        payload["document_id"] = document_id

    response = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=180,
    )

    response.raise_for_status()

    return response.json()


def normalize_text(text: str | None) -> str:
    if text is None:
        return ""

    return " ".join(text.lower().strip().split())


def is_no_answer(answer: str | None) -> bool:
    normalized_answer = normalize_text(answer)
    normalized_expected = normalize_text(NO_ANSWER_MESSAGE)

    return normalized_expected in normalized_answer


def is_expected_absent_answer(expected_answer: str | None) -> bool:
    return is_no_answer(expected_answer)


def evaluate_single_item(
    item: dict[str, Any],
    response_payload: dict[str, Any],
) -> dict[str, Any]:
    answer = response_payload.get("answer", "")
    sources = response_payload.get("sources", [])

    expected_answer = item.get("expected_answer")
    expected_source_filename = item.get("expected_source_filename")
    expected_page = item.get("expected_page")

    first_source = sources[0] if sources else {}

    actual_source_filename = first_source.get("source_filename")
    actual_page = first_source.get("page_number")

    source_filenames = [
        source.get("source_filename")
        for source in sources
    ]

    source_pages = [
        source.get("page_number")
        for source in sources
    ]

    expected_absent_answer = is_expected_absent_answer(expected_answer)

    if expected_absent_answer:
        refusal_correct = is_no_answer(answer)
        source_filename_match = len(sources) == 0
        source_page_match = len(sources) == 0
        passed = refusal_correct
    else:
        refusal_correct = not is_no_answer(answer)
        source_filename_match = expected_source_filename in source_filenames

        if expected_page is None:
            source_page_match = True
        else:
            source_page_match = expected_page in source_pages

        passed = refusal_correct and source_filename_match

    return {
        "id": item.get("id"),
        "question": item.get("question"),
        "type": item.get("type"),
        "difficulty": item.get("difficulty"),
        "expected_answer": expected_answer,
        "actual_answer": answer,
        "context_used": response_payload.get("context_used"),
        "sources_count": response_payload.get("sources_count"),
        "expected_source_filename": expected_source_filename,
        "actual_source_filename": actual_source_filename,
        "expected_page": expected_page,
        "actual_page": actual_page,
        "all_source_filenames": source_filenames,
        "all_source_pages": source_pages,
        "top_source_score": first_source.get("score"),
        "refusal_correct": refusal_correct,
        "source_filename_match": source_filename_match,
        "source_page_match": source_page_match,
        "passed": passed,
        "sources": sources,
    }


def save_json_results(
    results: list[dict[str, Any]],
    output_path: Path,
) -> None:
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(results, file, indent=2, ensure_ascii=False)


def save_csv_results(
    results: list[dict[str, Any]],
    output_path: Path,
) -> None:
    fieldnames = [
        "id",
        "question",
        "type",
        "difficulty",
        "expected_answer",
        "actual_answer",
        "context_used",
        "sources_count",
        "expected_source_filename",
        "actual_source_filename",
        "expected_page",
        "actual_page",
        "all_source_filenames",
        "all_source_pages",
        "top_source_score",
        "refusal_correct",
        "source_filename_match",
        "source_page_match",
        "passed",
        "error",
    ]

    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()

        for result in results:
            row = {
                key: result.get(key)
                for key in fieldnames
            }
            writer.writerow(row)


def build_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(results)
    passed = sum(1 for result in results if result.get("passed") is True)
    failed = total - passed

    absent_answer_items = [
        result for result in results
        if is_expected_absent_answer(result.get("expected_answer"))
    ]

    absent_answer_passed = sum(
        1 for result in absent_answer_items
        if result.get("passed") is True
    )

    source_filename_matches = sum(
        1 for result in results
        if result.get("source_filename_match") is True
    )

    source_page_matches = sum(
        1 for result in results
        if result.get("source_page_match") is True
    )

    return {
        "total_questions": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": round(passed / total, 4) if total else 0,
        "absent_answer_questions": len(absent_answer_items),
        "absent_answer_passed": absent_answer_passed,
        "absent_answer_pass_rate": round(
            absent_answer_passed / len(absent_answer_items),
            4,
        )
        if absent_answer_items else None,
        "source_filename_match_rate": round(source_filename_matches / total, 4)
        if total else 0,
        "source_page_match_rate": round(source_page_matches / total, 4)
        if total else 0,
    }


def save_summary_report(
    summary: dict[str, Any],
    results: list[dict[str, Any]],
    output_path: Path,
) -> None:
    failed_items = [
        result for result in results
        if result.get("passed") is not True
    ]

    lines = [
        "# DocuMind AI RAG Evaluation Summary",
        "",
        f"Generated at: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Overall Results",
        "",
        f"- Total questions: {summary['total_questions']}",
        f"- Passed: {summary['passed']}",
        f"- Failed: {summary['failed']}",
        f"- Pass rate: {summary['pass_rate']}",
        f"- Absent-answer questions: {summary['absent_answer_questions']}",
        f"- Absent-answer pass rate: {summary['absent_answer_pass_rate']}",
        f"- Source filename match rate: {summary['source_filename_match_rate']}",
        f"- Source page match rate: {summary['source_page_match_rate']}",
        f"- Elapsed seconds: {summary.get('elapsed_seconds')}",
        "",
        "## Failed Items",
        "",
    ]

    if not failed_items:
        lines.append("No failed items.")
    else:
        for item in failed_items:
            lines.extend(
                [
                    f"### {item.get('id')}",
                    "",
                    f"- Question: {item.get('question')}",
                    f"- Type: {item.get('type')}",
                    f"- Difficulty: {item.get('difficulty')}",
                    f"- Expected page: {item.get('expected_page')}",
                    f"- Actual page: {item.get('actual_page')}",
                    f"- All source pages: {item.get('all_source_pages')}",
                    f"- Expected source: {item.get('expected_source_filename')}",
                    f"- Actual source: {item.get('actual_source_filename')}",
                    f"- Source filename match: {item.get('source_filename_match')}",
                    f"- Source page match: {item.get('source_page_match')}",
                    f"- Refusal correct: {item.get('refusal_correct')}",
                    f"- Answer: {item.get('actual_answer')}",
                    f"- Error: {item.get('error')}",
                    "",
                ]
            )

    with output_path.open("w", encoding="utf-8") as file:
        file.write("\n".join(lines))


def build_error_result(
    item: dict[str, Any],
    error: Exception,
) -> dict[str, Any]:
    return {
        "id": item.get("id"),
        "question": item.get("question"),
        "type": item.get("type"),
        "difficulty": item.get("difficulty"),
        "expected_answer": item.get("expected_answer"),
        "actual_answer": None,
        "context_used": None,
        "sources_count": None,
        "expected_source_filename": item.get("expected_source_filename"),
        "actual_source_filename": None,
        "expected_page": item.get("expected_page"),
        "actual_page": None,
        "all_source_filenames": [],
        "all_source_pages": [],
        "top_source_score": None,
        "refusal_correct": False,
        "source_filename_match": False,
        "source_page_match": False,
        "passed": False,
        "sources": [],
        "error": str(error),
    }


def main() -> None:
    load_environment()

    api_base_url = get_api_base_url()
    dataset_path = get_dataset_path()
    document_id = get_document_id()

    token = get_auth_token(api_base_url)
    dataset = load_dataset(dataset_path)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    json_output_path = RESULTS_DIR / f"rag_eval_results_{timestamp}.json"
    csv_output_path = RESULTS_DIR / f"rag_eval_results_{timestamp}.csv"
    summary_output_path = RESULTS_DIR / f"rag_eval_summary_{timestamp}.md"

    results: list[dict[str, Any]] = []

    print(f"Running DocuMind AI evaluation on {len(dataset)} questions...")
    print(f"API base URL: {api_base_url}")
    print(f"Dataset path: {dataset_path}")
    print(f"Document ID: {document_id}")

    start_time = time.perf_counter()

    for index, item in enumerate(dataset, start=1):
        question = item["question"]

        print(f"[{index}/{len(dataset)}] {item['id']} - {question}")

        try:
            response_payload = call_answer_endpoint(
                api_base_url=api_base_url,
                token=token,
                question=question,
                document_id=document_id,
                top_k=5,
            )

            evaluation_result = evaluate_single_item(
                item=item,
                response_payload=response_payload,
            )

            evaluation_result["error"] = None

        except Exception as error:
            evaluation_result = build_error_result(
                item=item,
                error=error,
            )

        results.append(evaluation_result)

    elapsed_seconds = round(time.perf_counter() - start_time, 2)

    summary = build_summary(results)
    summary["elapsed_seconds"] = elapsed_seconds

    save_json_results(results, json_output_path)
    save_csv_results(results, csv_output_path)
    save_summary_report(summary, results, summary_output_path)

    print("")
    print("Evaluation completed.")
    print(f"Elapsed seconds: {elapsed_seconds}")
    print(f"Pass rate: {summary['pass_rate']}")
    print(f"JSON results: {json_output_path}")
    print(f"CSV results: {csv_output_path}")
    print(f"Summary report: {summary_output_path}")


if __name__ == "__main__":
    main()