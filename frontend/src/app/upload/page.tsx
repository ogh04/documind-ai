"use client";

import { ChangeEvent, DragEvent, useRef, useState } from "react";

import { AppShell } from "@/components/AppShell";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { useAuth } from "@/components/AuthProvider";
import {
  DocumentIndexResponse,
  DocumentProcessResponse,
  UploadedDocument,
  getDocumentStatus,
  indexDocument,
  processDocument,
  uploadDocument,
} from "@/lib/documents-api";

type UploadStage =
  | "idle"
  | "selected"
  | "uploading"
  | "uploaded"
  | "processing"
  | "processed"
  | "indexing"
  | "indexed"
  | "failed";

type StatusLogItem = {
  label: string;
  detail: string;
  state: "done" | "active" | "error";
};

const acceptedFileTypes = ".pdf,.docx,.png,.jpg,.jpeg";

function formatFileSize(sizeInBytes: number): string {
  const sizeInMb = sizeInBytes / (1024 * 1024);

  if (sizeInMb >= 1) {
    return `${sizeInMb.toFixed(2)} MB`;
  }

  return `${(sizeInBytes / 1024).toFixed(2)} KB`;
}

function getStageLabel(stage: UploadStage): string {
  const labels: Record<UploadStage, string> = {
    idle: "Waiting for file",
    selected: "File selected",
    uploading: "Uploading",
    uploaded: "Uploaded",
    processing: "Processing",
    processed: "Processed",
    indexing: "Indexing",
    indexed: "Indexed",
    failed: "Failed",
  };

  return labels[stage];
}

export default function UploadPage() {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const { token } = useAuth();

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragActive, setIsDragActive] = useState(false);
  const [stage, setStage] = useState<UploadStage>("idle");
  const [uploadProgress, setUploadProgress] = useState(0);
  const [errorMessage, setErrorMessage] = useState("");
  const [uploadedDocument, setUploadedDocument] =
    useState<UploadedDocument | null>(null);
  const [processResult, setProcessResult] =
    useState<DocumentProcessResponse | null>(null);
  const [indexResult, setIndexResult] =
    useState<DocumentIndexResponse | null>(null);
  const [statusLog, setStatusLog] = useState<StatusLogItem[]>([]);

  function addStatusLog(item: StatusLogItem): void {
    setStatusLog((currentItems) => [item, ...currentItems]);
  }

  function resetWorkflow(file: File): void {
    setSelectedFile(file);
    setStage("selected");
    setUploadProgress(0);
    setErrorMessage("");
    setUploadedDocument(null);
    setProcessResult(null);
    setIndexResult(null);
    setStatusLog([
      {
        label: "File selected",
        detail: `${file.name} · ${formatFileSize(file.size)}`,
        state: "done",
      },
    ]);
  }

  function handleFileSelection(file: File | undefined): void {
    if (!file) {
      return;
    }

    resetWorkflow(file);
  }

  function handleInputChange(event: ChangeEvent<HTMLInputElement>): void {
    handleFileSelection(event.target.files?.[0]);
  }

  function handleDragOver(event: DragEvent<HTMLDivElement>): void {
    event.preventDefault();
    setIsDragActive(true);
  }

  function handleDragLeave(event: DragEvent<HTMLDivElement>): void {
    event.preventDefault();
    setIsDragActive(false);
  }

  function handleDrop(event: DragEvent<HTMLDivElement>): void {
    event.preventDefault();
    setIsDragActive(false);
    handleFileSelection(event.dataTransfer.files?.[0]);
  }

  async function handleUploadWorkflow(): Promise<void> {
    if (!selectedFile) {
      setErrorMessage("Select a file first.");
      return;
    }

    if (!token) {
      setErrorMessage("You must be logged in before uploading.");
      return;
    }

    setErrorMessage("");
    setStage("uploading");

    try {
      addStatusLog({
        label: "Upload started",
        detail: "Sending file to /documents/upload",
        state: "active",
      });

      const uploaded = await uploadDocument({
        file: selectedFile,
        token,
        onProgress: setUploadProgress,
      });

      setUploadedDocument(uploaded);
      setStage("uploaded");

      addStatusLog({
        label: "Upload completed",
        detail: `Document #${uploaded.id} created with status: ${uploaded.status}`,
        state: "done",
      });

      setStage("processing");

      addStatusLog({
        label: "Processing started",
        detail: "Extracting text and creating chunks",
        state: "active",
      });

      const processed = await processDocument(uploaded.id, token);

      setProcessResult(processed);
      setStage("processed");

      addStatusLog({
        label: "Processing completed",
        detail: `${processed.chunk_count} chunks created from ${processed.text_length} characters`,
        state: "done",
      });

      setStage("indexing");

      addStatusLog({
        label: "Indexing started",
        detail: "Embedding chunks and upserting vectors to Qdrant",
        state: "active",
      });

      const indexed = await indexDocument(uploaded.id, token);

      setIndexResult(indexed);
      setStage("indexed");

      addStatusLog({
        label: "Indexing completed",
        detail: `${indexed.indexed_chunks} chunks indexed in ${indexed.collection}`,
        state: "done",
      });

      const latestStatus = await getDocumentStatus(uploaded.id, token);

      addStatusLog({
        label: "Final status checked",
        detail: `Backend status: ${latestStatus.status}`,
        state: "done",
      });
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Upload workflow failed.";

      setStage("failed");
      setErrorMessage(message);

      addStatusLog({
        label: "Workflow failed",
        detail: message,
        state: "error",
      });
    }
  }

  const isWorking =
    stage === "uploading" || stage === "processing" || stage === "indexing";

  return (
    <ProtectedRoute>
      <AppShell
        title="Upload"
        description="Upload documents, track upload progress, process text, and index chunks into the vector database."
      >
        <section className="grid gap-6 lg:grid-cols-[1fr_380px]">
          <div className="space-y-6">
            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              className={`rounded-3xl border border-dashed p-8 transition ${
                isDragActive
                  ? "border-cyan-400 bg-cyan-400/10"
                  : "border-slate-700 bg-slate-900/70"
              }`}
            >
              <div className="mx-auto max-w-2xl text-center">
                <p className="text-sm font-semibold uppercase tracking-[0.25em] text-cyan-400">
                  Document intake
                </p>

                <h3 className="mt-4 text-2xl font-bold">
                  Click or drag a document here
                </h3>

                <p className="mt-3 text-slate-400">
                  Supported formats: PDF, DOCX, PNG, JPG, JPEG.
                </p>

                <input
                  ref={fileInputRef}
                  type="file"
                  accept={acceptedFileTypes}
                  onChange={handleInputChange}
                  className="hidden"
                />

                <div className="mt-8 flex flex-wrap justify-center gap-3">
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    disabled={isWorking}
                    className="rounded-xl bg-cyan-400 px-6 py-3 font-semibold text-slate-950 transition hover:bg-cyan-300 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    Choose file
                  </button>

                  <button
                    type="button"
                    onClick={handleUploadWorkflow}
                    disabled={!selectedFile || isWorking}
                    className="rounded-xl border border-slate-700 px-6 py-3 font-semibold text-slate-200 transition hover:border-cyan-400 hover:text-cyan-300 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {isWorking ? "Working..." : "Upload and process"}
                  </button>
                </div>

                {selectedFile ? (
                  <div className="mt-8 rounded-2xl border border-slate-800 bg-slate-950 p-5 text-left">
                    <p className="text-sm text-slate-400">Selected file</p>
                    <p className="mt-2 font-semibold text-white">
                      {selectedFile.name}
                    </p>
                    <p className="mt-1 text-sm text-slate-500">
                      {formatFileSize(selectedFile.size)}
                    </p>
                  </div>
                ) : null}
              </div>
            </div>

            <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <p className="text-sm text-slate-400">Current status</p>
                  <h3 className="mt-1 text-2xl font-bold">
                    {getStageLabel(stage)}
                  </h3>
                </div>

                <span className="rounded-full border border-slate-700 px-4 py-2 text-sm text-cyan-300">
                  {stage}
                </span>
              </div>

              <div className="mt-6">
                <div className="flex justify-between text-sm text-slate-400">
                  <span>Upload progress</span>
                  <span>{uploadProgress}%</span>
                </div>

                <div className="mt-2 h-3 overflow-hidden rounded-full bg-slate-800">
                  <div
                    className="h-full rounded-full bg-cyan-400 transition-all"
                    style={{ width: `${uploadProgress}%` }}
                  />
                </div>
              </div>

              {errorMessage ? (
                <div className="mt-6 rounded-xl border border-red-500/40 bg-red-500/10 p-4 text-sm text-red-300">
                  {errorMessage}
                </div>
              ) : null}
            </div>

            <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
              <h3 className="text-xl font-semibold">Workflow log</h3>

              <div className="mt-5 space-y-3">
                {statusLog.length === 0 ? (
                  <p className="text-sm text-slate-500">
                    Upload activity will appear here.
                  </p>
                ) : (
                  statusLog.map((item, index) => (
                    <div
                      key={`${item.label}-${index}`}
                      className="rounded-xl border border-slate-800 bg-slate-950 p-4"
                    >
                      <div className="flex items-center justify-between gap-4">
                        <p className="font-semibold text-white">{item.label}</p>
                        <span
                          className={`rounded-full px-3 py-1 text-xs font-semibold ${
                            item.state === "done"
                              ? "bg-emerald-400/10 text-emerald-300"
                              : item.state === "active"
                                ? "bg-cyan-400/10 text-cyan-300"
                                : "bg-red-400/10 text-red-300"
                          }`}
                        >
                          {item.state}
                        </span>
                      </div>
                      <p className="mt-2 text-sm text-slate-400">
                        {item.detail}
                      </p>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>

          <aside className="space-y-6">
            <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
              <h3 className="text-xl font-semibold">Document status</h3>

              <dl className="mt-5 space-y-4 text-sm">
                <div>
                  <dt className="text-slate-500">Document ID</dt>
                  <dd className="mt-1 text-white">
                    {uploadedDocument?.id ?? "—"}
                  </dd>
                </div>

                <div>
                  <dt className="text-slate-500">Backend status</dt>
                  <dd className="mt-1 text-white">
                    {indexResult?.status ??
                      processResult?.status ??
                      uploadedDocument?.status ??
                      "—"}
                  </dd>
                </div>

                <div>
                  <dt className="text-slate-500">Chunks</dt>
                  <dd className="mt-1 text-white">
                    {indexResult?.indexed_chunks ??
                      processResult?.chunk_count ??
                      "—"}
                  </dd>
                </div>

                <div>
                  <dt className="text-slate-500">File type</dt>
                  <dd className="mt-1 text-white">
                    {uploadedDocument?.file_type ?? "—"}
                  </dd>
                </div>

                <div>
                  <dt className="text-slate-500">File size</dt>
                  <dd className="mt-1 text-white">
                    {uploadedDocument
                      ? formatFileSize(uploadedDocument.file_size)
                      : "—"}
                  </dd>
                </div>
              </dl>
            </div>

            <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
              <h3 className="text-xl font-semibold">Pipeline</h3>
              <ol className="mt-5 space-y-3 text-sm text-slate-400">
                <li>1. Upload file to FastAPI</li>
                <li>2. Store document metadata</li>
                <li>3. Extract text</li>
                <li>4. Create chunks</li>
                <li>5. Generate embeddings</li>
                <li>6. Upsert vectors to Qdrant</li>
              </ol>
            </div>
          </aside>
        </section>
      </AppShell>
    </ProtectedRoute>
  );
}
