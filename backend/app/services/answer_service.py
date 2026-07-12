from app.schemas.answer import AnswerSource


NO_ANSWER_MESSAGE = "I cannot find this information in the provided document."


def filter_sources_by_min_score(
    sources: list[AnswerSource],
    min_score: float,
) -> list[AnswerSource]:
    return [
        source
        for source in sources
        if source.score >= min_score
    ]


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
        return NO_ANSWER_MESSAGE

    context = build_context_from_sources(sources)

    return (
        "Based on the retrieved document context, the relevant information is:\n\n"
        f"{context}\n\n"
        "This answer is generated only from the retrieved document context."
    )