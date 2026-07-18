import { AppShell } from "@/components/AppShell";

export default function ChatPage() {
  return (
    <AppShell
      title="Chat"
      description="Ask grounded questions against your indexed documents using the RAG backend."
    >
      <section className="grid min-h-[620px] gap-6 lg:grid-cols-[1fr_320px]">
        <div className="flex flex-col rounded-2xl border border-slate-800 bg-slate-900/70">
          <div className="border-b border-slate-800 p-5">
            <h3 className="text-xl font-semibold">Document Q&A</h3>
            <p className="mt-1 text-sm text-slate-400">
              Chat integration will connect to /answer and /query.
            </p>
          </div>

          <div className="flex-1 space-y-4 p-5">
            <div className="max-w-xl rounded-2xl bg-slate-950 p-4 text-slate-300">
              Upload and index a document, then ask a question here.
            </div>
          </div>

          <form className="border-t border-slate-800 p-5">
            <div className="flex gap-3">
              <input
                type="text"
                placeholder="Ask a question about your documents..."
                className="flex-1 rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none transition placeholder:text-slate-600 focus:border-cyan-400"
              />
              <button
                type="button"
                className="rounded-xl bg-cyan-400 px-6 py-3 font-semibold text-slate-950 transition hover:bg-cyan-300"
              >
                Ask
              </button>
            </div>
          </form>
        </div>

        <aside className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
          <h3 className="text-lg font-semibold">Answer sources</h3>
          <p className="mt-2 text-sm leading-6 text-slate-400">
            Citations, document names, page numbers, chunk indexes, and scores
            will appear here after API integration.
          </p>
        </aside>
      </section>
    </AppShell>
  );
}
