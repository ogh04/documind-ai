import Link from "next/link";

import { AppShell } from "@/components/AppShell";

const emptyDocuments = [];

export default function DocumentsPage() {
  return (
    <AppShell
      title="Documents"
      description="Manage uploaded files, processing state, and indexed document chunks."
    >
      <section className="rounded-2xl border border-slate-800 bg-slate-900/70">
        <div className="flex items-center justify-between border-b border-slate-800 p-6">
          <div>
            <h3 className="text-xl font-semibold">Document library</h3>
            <p className="mt-1 text-sm text-slate-400">
              Uploaded documents will appear here after API integration.
            </p>
          </div>

          <Link
            href="/upload"
            className="rounded-xl bg-cyan-400 px-5 py-3 text-sm font-semibold text-slate-950 transition hover:bg-cyan-300"
          >
            Upload
          </Link>
        </div>

        {emptyDocuments.length === 0 ? (
          <div className="p-10 text-center">
            <p className="text-lg font-semibold">No documents yet</p>
            <p className="mt-2 text-slate-400">
              Upload your first PDF, DOCX, PNG, or JPG to start building the
              knowledge base.
            </p>
          </div>
        ) : null}
      </section>
    </AppShell>
  );
}
