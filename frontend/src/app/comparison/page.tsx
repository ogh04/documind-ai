"use client";

import { FormEvent, useMemo, useState } from "react";

import { AppShell } from "@/components/AppShell";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { useAuth } from "@/components/AuthProvider";
import {
  ComparisonMethodResult,
  ComparisonResponse,
  ComparisonSource,
  RagasScores,
  compareRetrievalPipelines,
} from "@/lib/comparison-api";

type MetricRow = {
  label: string;
  methodAValue: number | null;
  methodBValue: number | null;
};

function formatNullableScore(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return "—";
  }

  return value.toFixed(3);
}

function formatLatency(value: number): string {
  if (value >= 1000) {
    return `${(value / 1000).toFixed(2)}s`;
  }

  return `${value.toFixed(0)}ms`;
}

function normalizeWidth(value: number | null | undefined): number {
  if (value === null || value === undefined) {
    return 0;
  }

  if (value <= 1) {
    return Math.max(4, Math.min(100, value * 100));
  }

  return Math.max(4, Math.min(100, value));
}

function getWinnerLabel(result: ComparisonResponse | null): string {
  if (!result) {
    return "No comparison yet";
  }

  if (!result.winner) {
    return "Winner not computed";
  }

  return result.winner;
}

function getRagasRows(
  methodA: ComparisonMethodResult,
  methodB: ComparisonMethodResult,
): MetricRow[] {
  return [
    {
      label: "Faithfulness",
      methodAValue: methodA.ragas_scores.faithfulness,
      methodBValue: methodB.ragas_scores.faithfulness,
    },
    {
      label: "Context precision",
      methodAValue: methodA.ragas_scores.context_precision,
      methodBValue: methodB.ragas_scores.context_precision,
    },
    {
      label: "Context recall",
      methodAValue: methodA.ragas_scores.context_recall,
      methodBValue: methodB.ragas_scores.context_recall,
    },
    {
      label: "Answer relevance",
      methodAValue: methodA.ragas_scores.answer_relevance,
      methodBValue: methodB.ragas_scores.answer_relevance,
    },
  ];
}

function MetricBar({
  label,
  value,
}: {
  label: string;
  value: number | null | undefined;
}) {
  return (
    <div>
      <div className="flex items-center justify-between text-sm">
        <span className="text-slate-400">{label}</span>
        <span className="font-mono text-slate-200">
          {formatNullableScore(value)}
        </span>
      </div>

      <div className="mt-2 h-3 overflow-hidden rounded-full bg-slate-800">
        <div
          className="h-full rounded-full bg-cyan-400 transition-all"
          style={{ width: `${normalizeWidth(value)}%` }}
        />
      </div>
    </div>
  );
}

function LatencyChart({
  methodA,
  methodB,
}: {
  methodA: ComparisonMethodResult;
  methodB: ComparisonMethodResult;
}) {
  const maxLatency = Math.max(methodA.latency_ms, methodB.latency_ms, 1);

  const rows = [
    {
      label: methodA.method_name,
      value: methodA.latency_ms,
    },
    {
      label: methodB.method_name,
      value: methodB.latency_ms,
    },
  ];

  return (
    <section className="rounded-3xl border border-slate-800 bg-slate-900/70 p-6">
      <h3 className="text-xl font-semibold">Latency comparison</h3>
      <p className="mt-2 text-sm text-slate-400">
        Lower latency is better. Values are measured by the backend comparison
        pipeline.
      </p>

      <div className="mt-6 space-y-5">
        {rows.map((row) => (
          <div key={row.label}>
            <div className="flex items-center justify-between gap-4 text-sm">
              <span className="font-semibold text-slate-200">{row.label}</span>
              <span className="font-mono text-cyan-300">
                {formatLatency(row.value)}
              </span>
            </div>

            <div className="mt-2 h-4 overflow-hidden rounded-full bg-slate-800">
              <div
                className="h-full rounded-full bg-cyan-400 transition-all"
                style={{ width: `${Math.max(5, (row.value / maxLatency) * 100)}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function AnswerQualityChart({
  methodA,
  methodB,
}: {
  methodA: ComparisonMethodResult;
  methodB: ComparisonMethodResult;
}) {
  return (
    <section className="rounded-3xl border border-slate-800 bg-slate-900/70 p-6">
      <h3 className="text-xl font-semibold">Answer quality</h3>
      <p className="mt-2 text-sm text-slate-400">
        Computed only when a reference answer is provided.
      </p>

      <div className="mt-6 space-y-5">
        <MetricBar label={methodA.method_name} value={methodA.answer_quality} />
        <MetricBar label={methodB.method_name} value={methodB.answer_quality} />
      </div>
    </section>
  );
}

function RagasDashboard({
  methodA,
  methodB,
}: {
  methodA: ComparisonMethodResult;
  methodB: ComparisonMethodResult;
}) {
  const rows = getRagasRows(methodA, methodB);

  return (
    <section className="rounded-3xl border border-slate-800 bg-slate-900/70 p-6">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h3 className="text-xl font-semibold">RAGAS scores</h3>
          <p className="mt-2 text-sm text-slate-400">
            Side-by-side score comparison for retrieval and answer quality.
          </p>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-950 px-4 py-3 text-sm">
          <p className="text-slate-500">Status</p>
          <p className="mt-1 font-semibold text-cyan-300">
            {methodA.ragas_scores.status} / {methodB.ragas_scores.status}
          </p>
        </div>
      </div>

      <div className="mt-6 overflow-hidden rounded-2xl border border-slate-800">
        <div className="grid grid-cols-[1fr_1fr_1fr] border-b border-slate-800 bg-slate-950 p-4 text-sm font-semibold text-slate-300">
          <span>Metric</span>
          <span>{methodA.method_name}</span>
          <span>{methodB.method_name}</span>
        </div>

        {rows.map((row) => (
          <div
            key={row.label}
            className="grid grid-cols-[1fr_1fr_1fr] gap-4 border-b border-slate-800 p-4 last:border-b-0"
          >
            <p className="text-sm font-semibold text-white">{row.label}</p>

            <div>
              <p className="font-mono text-sm text-slate-200">
                {formatNullableScore(row.methodAValue)}
              </p>
              <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-800">
                <div
                  className="h-full rounded-full bg-cyan-400"
                  style={{ width: `${normalizeWidth(row.methodAValue)}%` }}
                />
              </div>
            </div>

            <div>
              <p className="font-mono text-sm text-slate-200">
                {formatNullableScore(row.methodBValue)}
              </p>
              <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-800">
                <div
                  className="h-full rounded-full bg-cyan-400"
                  style={{ width: `${normalizeWidth(row.methodBValue)}%` }}
                />
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function MethodCard({
  method,
}: {
  method: ComparisonMethodResult;
}) {
  return (
    <article className="rounded-3xl border border-slate-800 bg-slate-900/70 p-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.25em] text-cyan-400">
            Method
          </p>
          <h3 className="mt-3 text-2xl font-bold">{method.method_name}</h3>
          <p className="mt-2 text-sm leading-6 text-slate-400">
            {method.retrieval_pipeline}
          </p>
        </div>

        <span
          className={`rounded-full px-3 py-1 text-xs font-semibold ${
            method.context_used
              ? "bg-emerald-400/10 text-emerald-300"
              : "bg-amber-400/10 text-amber-300"
          }`}
        >
          {method.context_used ? "context used" : "no context"}
        </span>
      </div>

      <dl className="mt-6 grid gap-4 text-sm sm:grid-cols-3">
        <div className="rounded-2xl border border-slate-800 bg-slate-950 p-4">
          <dt className="text-slate-500">Latency</dt>
          <dd className="mt-2 font-mono text-cyan-300">
            {formatLatency(method.latency_ms)}
          </dd>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-950 p-4">
          <dt className="text-slate-500">Quality</dt>
          <dd className="mt-2 font-mono text-cyan-300">
            {formatNullableScore(method.answer_quality)}
          </dd>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-950 p-4">
          <dt className="text-slate-500">Chunks</dt>
          <dd className="mt-2 font-mono text-cyan-300">
            {method.retrieved_chunks_count}
          </dd>
        </div>
      </dl>

      <div className="mt-6 rounded-2xl border border-slate-800 bg-slate-950 p-5">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
          Generated answer
        </p>
        <p className="mt-3 whitespace-pre-wrap text-sm leading-7 text-slate-200">
          {method.answer}
        </p>
      </div>
    </article>
  );
}

function SourceCard({
  source,
  index,
}: {
  source: ComparisonSource;
  index: number;
}) {
  return (
    <article className="rounded-2xl border border-slate-800 bg-slate-950 p-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-semibold text-cyan-300">
            Source [{index + 1}]
          </p>
          <h4 className="mt-2 text-sm font-semibold text-white">
            {source.source_filename}
          </h4>
        </div>

        <span className="rounded-full border border-slate-700 px-3 py-1 text-xs text-slate-300">
          score {source.score.toFixed(3)}
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
          Excerpt
        </p>
        <p className="mt-3 text-sm leading-6 text-slate-300">{source.text}</p>
      </div>
    </article>
  );
}

function MethodSources({
  title,
  sources,
}: {
  title: string;
  sources: ComparisonSource[];
}) {
  return (
    <section className="rounded-3xl border border-slate-800 bg-slate-900/70 p-6">
      <h3 className="text-xl font-semibold">{title}</h3>
      <p className="mt-2 text-sm text-slate-400">
        Retrieved chunks used by this method.
      </p>

      <div className="mt-5 space-y-4">
        {sources.length === 0 ? (
          <div className="rounded-2xl border border-slate-800 bg-slate-950 p-5 text-sm text-slate-500">
            No sources returned.
          </div>
        ) : (
          sources.map((source, index) => (
            <SourceCard
              key={`${source.document_chunk_id}-${index}`}
              source={source}
              index={index}
            />
          ))
        )}
      </div>
    </section>
  );
}

export default function ComparisonPage() {
  const { token } = useAuth();

  const [question, setQuestion] = useState("Summarize this document.");
  const [documentId, setDocumentId] = useState("7");
  const [topK, setTopK] = useState(5);
  const [referenceAnswer, setReferenceAnswer] = useState("");
  const [result, setResult] = useState<ComparisonResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const hasResult = result !== null;

  const notes = useMemo(() => {
    if (!result) {
      return [];
    }

    return result.notes;
  }, [result]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!question.trim()) {
      setErrorMessage("Write a question first.");
      return;
    }

    if (!token) {
      setErrorMessage("You must be logged in before comparing methods.");
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

      const comparison = await compareRetrievalPipelines(
        {
          question: question.trim(),
          document_id: parsedDocumentId,
          top_k: topK,
          reference_answer: referenceAnswer.trim()
            ? referenceAnswer.trim()
            : null,
        },
        token,
      );

      setResult(comparison);
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : "Comparison failed.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <ProtectedRoute>
      <AppShell
        title="Comparison Dashboard"
        description="Compare normal RAG against hybrid search plus reranking using latency, answer quality, RAGAS scores, and retrieved sources."
      >
        <section className="space-y-6">
          <form
            onSubmit={handleSubmit}
            className="rounded-3xl border border-slate-800 bg-slate-900/70 p-6"
          >
            <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              <div>
                <p className="text-sm font-semibold uppercase tracking-[0.25em] text-cyan-400">
                  RAG evaluation
                </p>
                <h3 className="mt-3 text-2xl font-bold">
                  Compare retrieval pipelines
                </h3>
                <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-400">
                  Provide a question, optionally restrict to one document, and
                  add a reference answer if you want answer quality and RAGAS
                  metrics.
                </p>
              </div>

              <div className="rounded-2xl border border-slate-800 bg-slate-950 px-5 py-4">
                <p className="text-sm text-slate-500">Winner</p>
                <p className="mt-1 font-semibold text-cyan-300">
                  {getWinnerLabel(result)}
                </p>
              </div>
            </div>

            <div className="mt-6 grid gap-4 lg:grid-cols-[1fr_160px_120px]">
              <input
                type="text"
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                placeholder="Ask a comparison question..."
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

            <textarea
              value={referenceAnswer}
              onChange={(event) => setReferenceAnswer(event.target.value)}
              placeholder="Optional reference answer for answer quality and RAGAS scores..."
              rows={4}
              className="mt-4 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none transition placeholder:text-slate-600 focus:border-cyan-400"
            />

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
              {isSubmitting ? "Running comparison..." : "Run comparison"}
            </button>
          </form>

          {!hasResult ? (
            <div className="rounded-3xl border border-slate-800 bg-slate-900/70 p-8 text-center">
              <p className="text-lg font-semibold text-white">
                No comparison run yet.
              </p>
              <p className="mt-2 text-sm text-slate-400">
                Run a comparison to display method outputs, charts, latency, and
                RAGAS metrics.
              </p>
            </div>
          ) : null}

          {result ? (
            <>
              <section className="grid gap-6 xl:grid-cols-2">
                <MethodCard method={result.method_a} />
                <MethodCard method={result.method_b} />
              </section>

              <section className="grid gap-6 xl:grid-cols-2">
                <LatencyChart
                  methodA={result.method_a}
                  methodB={result.method_b}
                />
                <AnswerQualityChart
                  methodA={result.method_a}
                  methodB={result.method_b}
                />
              </section>

              <RagasDashboard
                methodA={result.method_a}
                methodB={result.method_b}
              />

              {notes.length > 0 ? (
                <section className="rounded-3xl border border-slate-800 bg-slate-900/70 p-6">
                  <h3 className="text-xl font-semibold">Evaluation notes</h3>
                  <ul className="mt-4 space-y-2 text-sm text-slate-400">
                    {notes.map((note) => (
                      <li key={note}>• {note}</li>
                    ))}
                  </ul>
                </section>
              ) : null}

              <section className="grid gap-6 xl:grid-cols-2">
                <MethodSources
                  title={`${result.method_a.method_name} sources`}
                  sources={result.method_a.retrieved_chunks}
                />
                <MethodSources
                  title={`${result.method_b.method_name} sources`}
                  sources={result.method_b.retrieved_chunks}
                />
              </section>
            </>
          ) : null}
        </section>
      </AppShell>
    </ProtectedRoute>
  );
}
