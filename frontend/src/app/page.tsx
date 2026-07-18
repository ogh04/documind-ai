import Link from "next/link";

const features = [
  "Upload PDF, DOCX, and image documents",
  "Extract, chunk, embed, and index content",
  "Ask grounded questions with citations",
  "Track RAG performance across every major stage",
];

export default function HomePage() {
  return (
    <main className="min-h-screen bg-slate-950 text-white">
      <section className="mx-auto flex min-h-screen max-w-6xl flex-col justify-center px-6 py-16">
        <div className="max-w-3xl">
          <p className="mb-4 text-sm font-semibold uppercase tracking-[0.3em] text-cyan-400">
            DocuMind AI
          </p>

          <h1 className="text-5xl font-bold tracking-tight md:text-7xl">
            Private document intelligence for serious workflows.
          </h1>

          <p className="mt-6 text-lg leading-8 text-slate-300">
            Upload documents, build a searchable knowledge base, and ask precise
            questions using a production-style RAG pipeline.
          </p>

          <div className="mt-10 flex flex-wrap gap-4">
            <Link
              href="/login"
              className="rounded-xl bg-cyan-400 px-6 py-3 font-semibold text-slate-950 transition hover:bg-cyan-300"
            >
              Login
            </Link>

            <Link
              href="/register"
              className="rounded-xl border border-slate-700 px-6 py-3 font-semibold text-white transition hover:border-cyan-400 hover:text-cyan-300"
            >
              Create account
            </Link>
          </div>
        </div>

        <div className="mt-14 grid gap-4 md:grid-cols-2">
          {features.map((feature) => (
            <div
              key={feature}
              className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5 text-slate-300"
            >
              {feature}
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}