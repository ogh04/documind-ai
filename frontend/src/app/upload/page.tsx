import { AppShell } from "@/components/AppShell";

export default function UploadPage() {
  return (
    <AppShell
      title="Upload"
      description="Upload documents that will later be processed, chunked, embedded, and indexed."
    >
      <section className="rounded-2xl border border-dashed border-slate-700 bg-slate-900/70 p-8">
        <div className="mx-auto max-w-2xl text-center">
          <p className="text-sm font-semibold uppercase tracking-[0.25em] text-cyan-400">
            Document intake
          </p>

          <h3 className="mt-4 text-2xl font-bold">Upload a file</h3>

          <p className="mt-3 text-slate-400">
            Supported formats: PDF, DOCX, PNG, JPG. The backend currently
            handles validation, storage, extraction, chunking, embeddings, and
            Qdrant indexing.
          </p>

          <div className="mt-8 rounded-2xl border border-slate-800 bg-slate-950 p-6">
            <input
              type="file"
              className="block w-full cursor-pointer rounded-xl border border-slate-700 bg-slate-900 p-3 text-sm text-slate-300 file:mr-4 file:rounded-lg file:border-0 file:bg-cyan-400 file:px-4 file:py-2 file:font-semibold file:text-slate-950"
            />

            <button
              type="button"
              className="mt-5 w-full rounded-xl bg-cyan-400 px-5 py-3 font-semibold text-slate-950 transition hover:bg-cyan-300"
            >
              Upload document
            </button>
          </div>
        </div>
      </section>
    </AppShell>
  );
}
