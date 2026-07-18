"use client";

import { FormEvent, useMemo, useState } from "react";

import { AppShell } from "@/components/AppShell";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { useAuth } from "@/components/AuthProvider";
import {
  AnswerResponse,
  AnswerSource,
  askDocumentQuestion,
} from "@/lib/chat-api";

type ChatTurn = {
  id: string;
  question: string;
  answer: string;
  contextUsed: boolean;
  sources: AnswerSource[];
};

function formatScore(score: number): string {
  return score.toFixed(3);
}

function getPageLabel(pageNumber?: number | null): string {
  if (pageNumber === null || pageNumber === undefined) {
    return "Page unknown";
  }

  return `Page ${pageNumber}`;
}

function createCitationLabel(source: AnswerSource, index: number): string {
  return `[${index + 1}] ${source.source_filename} · ${getPageLabel(
    source.page_number,
  )} · Chunk ${source.chunk_index}`;
}

function buildAnswerWithInlineCitations(response: AnswerResponse): string {
  if (response.sources.length === 0) {
    return response.answer;
  }

  const citationText = response.sources
    .slice(0, 3)
    .map((source, index) => {
      return `[${index + 1}] ${source.source_filename}, ${getPageLabel(
        source.page_number,
      )}`;
    })
    .join("  ");

  return `${response.answer}\n\nSources: ${citationText}`;
}

function SourceCard({
  source,
  index,
}: {
  source: AnswerSource;
  index: number;
}) {
  return (
    <article className="rounded-2xl border border-slate-800 bg-slate-950 p-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-semibold text-cyan-300">
            Citation [{index + 1}]
          </p>
          <h4 className="mt-2 text-sm font-semibold text-white">
            {source.source_filename}
          </h4>
        </div>

        <span className="rounded-full border border-slate-700 px-3 py-1 text-xs text-slate-300">
          score {formatScore(source.score)}
        </span>
      </div>

      <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-3">
        <div>
          <dt className="text-slate-500">Page</dt>
          <dd className="mt-1 text-slate-200">
            {source.page_number ?? "Unknown"}
          </dd>
        </div>

        <div>
          <dt className="text-slate-500">Chunk</dt>
          <dd className="mt-1 text-slate-200">{source.chunk_index}</dd>
        </div>

        <div>
          <dt className="text-slate-500">Document ID</dt>
          <dd className="mt-1 text-slate-200">{source.document_id}</dd>
        </div>
      </dl>

      <div className="mt-4 rounded-xl border border-slate-800 bg-slate-900 p-4">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
          Source excerpt
        </p>
        <p className="mt-3 text-sm leading-6 text-slate-300">{source.text}</p>
      </div>
    </article>
  );
}

export default function ChatPage() {
  const { token } = useAuth();

  const [question, setQuestion] = useState("");
  const [documentId, setDocumentId] = useState("");
  const [topK, setTopK] = useState(5);
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [activeSources, setActiveSources] = useState<AnswerSource[]>([]);
  const [errorMessage, setErrorMessage] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const latestTurn = useMemo(() => turns[0], [turns]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!question.trim()) {
      setErrorMessage("Write a question first.");
      return;
    }

    if (!token) {
      setErrorMessage("You must be logged in before asking questions.");
      return;
    }

    setErrorMessage("");
    setIsSubmitting(true);

    try {
      const parsedDocumentId = documentId.trim()
        ? Number(documentId.trim())
        : null;

      if (
        parsedDocumentId !== null &&
        (!Number.isInteger(parsedDocumentId) || parsedDocumentId <= 0)
      ) {
        throw new Error("Document ID must be a positive number.");
      }

      const response = await askDocumentQuestion(
        {
          question: question.trim(),
          document_id: parsedDocumentId,
          top_k: topK,
        },
        token,
      );

      const newTurn: ChatTurn = {
        id: crypto.randomUUID(),
        question: response.question,
        answer: buildAnswerWithInlineCitations(response),
        contextUsed: response.context_used,
        sources: response.sources,
      };

      setTurns((currentTurns) => [newTurn, ...currentTurns]);
      setActiveSources(response.sources);
      setQuestion("");
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : "Question failed.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <ProtectedRoute>
      <AppShell
        title="Chat"
        description="Ask grounded questions against your indexed documents and inspect citations, pages, chunks, and source excerpts."
      >
        <section className="grid min-h-[720px] gap-6 xl:grid-cols-[1fr_420px]">
          <div className="flex flex-col rounded-3xl border border-slate-800 bg-slate-900/70">
            <div className="border-b border-slate-800 p-6">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                <div>
                  <p className="text-sm font-semibold uppercase tracking-[0.25em] text-cyan-400">
                    RAG Q&A
                  </p>
                  <h3 className="mt-3 text-2xl font-bold">
                    Ask your document collection
                  </h3>
                  <p className="mt-2 text-sm leading-6 text-slate-400">
                    Uses the backend /answer endpoint with hybrid retrieval,
                    reranking, generated answers, and grounded sources.
                  </p>
                </div>

                <div className="rounded-2xl border border-slate-800 bg-slate-950 p-4 text-sm">
                  <p className="text-slate-500">Latest context</p>
                  <p className="mt-1 font-semibold text-cyan-300">
                    {latestTurn
                      ? latestTurn.contextUsed
                        ? "Context used"
                        : "No context used"
                      : "No question yet"}
                  </p>
                </div>
              </div>
            </div>

            <div className="flex-1 space-y-5 overflow-y-auto p-6">
              {turns.length === 0 ? (
                <div className="rounded-2xl border border-slate-800 bg-slate-950 p-6">
                  <p className="text-lg font-semibold text-white">
                    Start with a precise question.
                  </p>
                  <p className="mt-2 text-sm leading-6 text-slate-400">
                    Example: “What does the uploaded document say about work
                    experience?” or “Summarize the candidate profile using
                    cited excerpts.”
                  </p>
                </div>
              ) : (
                turns.map((turn) => (
                  <article
                    key={turn.id}
                    className="rounded-2xl border border-slate-800 bg-slate-950 p-5"
                  >
                    <div className="rounded-2xl bg-slate-900 p-4">
                      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
                        Question
                      </p>
                      <p className="mt-2 text-slate-100">{turn.question}</p>
                    </div>

                    <div className="mt-4 rounded-2xl border border-slate-800 bg-slate-900/70 p-4">
                      <div className="flex items-center justify-between gap-4">
                        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-cyan-400">
                          Generated answer
                        </p>
                        <span
                          className={`rounded-full px-3 py-1 text-xs font-semibold ${
                            turn.contextUsed
                              ? "bg-emerald-400/10 text-emerald-300"
                              : "bg-amber-400/10 text-amber-300"
                          }`}
                        >
                          {turn.contextUsed ? "grounded" : "no context"}
                        </span>
                      </div>

                      <p className="mt-3 whitespace-pre-wrap text-sm leading-7 text-slate-200">
                        {turn.answer}
                      </p>
                    </div>

                    <button
                      type="button"
                      onClick={() => setActiveSources(turn.sources)}
                      className="mt-4 rounded-xl border border-slate-700 px-4 py-2 text-sm font-semibold text-slate-300 transition hover:border-cyan-400 hover:text-cyan-300"
                    >
                      View {turn.sources.length} source
                      {turn.sources.length === 1 ? "" : "s"}
                    </button>
                  </article>
                ))
              )}
            </div>

            <form
              onSubmit={handleSubmit}
              className="border-t border-slate-800 p-6"
            >
              <div className="grid gap-4 lg:grid-cols-[1fr_140px_110px]">
                <input
                  type="text"
                  value={question}
                  onChange={(event) => setQuestion(event.target.value)}
                  placeholder="Ask a question about your indexed documents..."
                  className="rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none transition placeholder:text-slate-600 focus:border-cyan-400"
                />

                <input
                  type="number"
                  min="1"
                  value={documentId}
                  onChange={(event) => setDocumentId(event.target.value)}
                  placeholder="Doc ID"
                  className="rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none transition placeholder:text-slate-600 focus:border-cyan-400"
                />

                <select
                  value={topK}
                  onChange={(event) => setTopK(Number(event.target.value))}
                  className="rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none transition focus:border-cyan-400"
                >
                  <option value={3}>Top 3</option>
                  <option value={5}>Top 5</option>
                  <option value={8}>Top 8</option>
                  <option value={10}>Top 10</option>
                </select>
              </div>

              {errorMessage ? (
                <div className="mt-4 rounded-xl border border-red-500/40 bg-red-500/10 p-3 text-sm text-red-300">
                  {errorMessage}
                </div>
              ) : null}

              <button
                type="submit"
                disabled={isSubmitting}
                className="mt-4 w-full rounded-xl bg-cyan-400 px-6 py-3 font-semibold text-slate-950 transition hover:bg-cyan-300 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isSubmitting ? "Generating answer..." : "Ask question"}
              </button>
            </form>
          </div>

          <aside className="space-y-6">
            <div className="rounded-3xl border border-slate-800 bg-slate-900/70 p-6">
              <h3 className="text-xl font-semibold">Answer sources</h3>
              <p className="mt-2 text-sm leading-6 text-slate-400">
                Citations, source files, page numbers, chunk IDs, scores, and
                excerpts from the backend response.
              </p>

              <div className="mt-5 space-y-4">
                {activeSources.length === 0 ? (
                  <div className="rounded-2xl border border-slate-800 bg-slate-950 p-5 text-sm text-slate-500">
                    Sources will appear after you ask a question.
                  </div>
                ) : (
                  activeSources.map((source, index) => (
                    <SourceCard
                      key={`${source.document_chunk_id}-${index}`}
                      source={source}
                      index={index}
                    />
                  ))
                )}
              </div>
            </div>

            <div className="rounded-3xl border border-slate-800 bg-slate-900/70 p-6">
              <h3 className="text-xl font-semibold">Citation format</h3>
              <div className="mt-4 space-y-3 text-sm text-slate-400">
                {activeSources.length === 0 ? (
                  <p>No active citations yet.</p>
                ) : (
                  activeSources.map((source, index) => (
                    <p key={`${source.document_chunk_id}-citation`}>
                      {createCitationLabel(source, index)}
                    </p>
                  ))
                )}
              </div>
            </div>
          </aside>
        </section>
      </AppShell>
    </ProtectedRoute>
  );
}
