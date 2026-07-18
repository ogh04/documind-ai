import Link from "next/link";

import { AppShell } from "@/components/AppShell";

const stats = [
  {
    label: "Documents",
    value: "0",
    description: "Uploaded files ready for processing",
  },
  {
    label: "Indexed chunks",
    value: "0",
    description: "Vectorized passages stored in Qdrant",
  },
  {
    label: "Queries",
    value: "0",
    description: "Questions asked against your documents",
  },
  {
    label: "Avg latency",
    value: "—",
    description: "Tracked by the backend performance logs",
  },
];

export default function DashboardPage() {
  return (
    <AppShell
      title="Dashboard"
      description="High-level overview of your private document intelligence workspace."
    >
      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {stats.map((stat) => (
          <article
            key={stat.label}
            className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5"
          >
            <p className="text-sm text-slate-400">{stat.label}</p>
            <p className="mt-3 text-4xl font-bold text-white">{stat.value}</p>
            <p className="mt-3 text-sm leading-6 text-slate-500">
              {stat.description}
            </p>
          </article>
        ))}
      </section>

      <section className="mt-8 grid gap-6 lg:grid-cols-2">
        <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
          <h3 className="text-xl font-semibold">Quick actions</h3>
          <div className="mt-5 grid gap-3">
            <Link
              href="/upload"
              className="rounded-xl bg-cyan-400 px-5 py-3 text-center font-semibold text-slate-950 transition hover:bg-cyan-300"
            >
              Upload a document
            </Link>
            <Link
              href="/chat"
              className="rounded-xl border border-slate-700 px-5 py-3 text-center font-semibold text-slate-200 transition hover:border-cyan-400 hover:text-cyan-300"
            >
              Ask a question
            </Link>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
          <h3 className="text-xl font-semibold">Pipeline status</h3>
          <ul className="mt-5 space-y-3 text-sm text-slate-400">
            <li>✅ Upload API ready</li>
            <li>✅ Extraction and chunking ready</li>
            <li>✅ Embedding and Qdrant indexing ready</li>
            <li>✅ Query and answer endpoints ready</li>
            <li>✅ Performance tracking active</li>
          </ul>
        </div>
      </section>
    </AppShell>
  );
}
