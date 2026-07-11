from app.schemas.answer import AnswerSource


def build_context_from_sources(sources: list[AnswerSource]) -> str:
    context_parts: list[str] = []

    for source in sources:
        page_label = (
            f"page {source.page_number}"
            if source.page_number is not None
            else "unknown page"
        )

        context_parts.append(
            (
                f"[Source: {source.source_filename}, "
                f"{page_label}, chunk {source.chunk_index}]\n"
                f"{source.text}"
            )
        )

    return "\n\n".join(context_parts).strip()


def build_grounded_draft_answer(
    question: str,
    sources: list[AnswerSource],
) -> str:
    if not sources:
        return (
            "I could not find relevant information in the indexed documents "
            "to answer this question."
        )

    context = build_context_from_sources(sources)

    return (
        "Based on the retrieved document context, the relevant information is:\n\n"
        f"{context}\n\n"
        "This is a grounded draft answer generated only from the retrieved chunks. "
        "A full LLM-generated answer will be added in the next step."
    )