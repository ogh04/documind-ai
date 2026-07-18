import { API_BASE_URL } from "@/lib/api";

export type ComparisonSource = {
  document_id: number;
  page_number?: number | null;
  chunk_index: number;
  source_filename: string;
  document_chunk_id: number;
  score: number;
  text: string;
};

export type RagasScores = {
  faithfulness: number | null;
  context_precision: number | null;
  context_recall: number | null;
  answer_relevance: number | null;
  status: string;
};

export type ComparisonMethodResult = {
  method_name: string;
  retrieval_pipeline: string;
  answer: string;
  context_used: boolean;
  answer_quality: number | null;
  retrieved_chunks: ComparisonSource[];
  retrieved_chunks_count: number;
  ragas_scores: RagasScores;
  latency_ms: number;
};

export type ComparisonRequest = {
  question: string;
  document_id?: number | null;
  top_k: number;
  reference_answer?: string | null;
};

export type ComparisonResponse = {
  question: string;
  document_id: number | null;
  top_k: number;
  has_reference_answer: boolean;
  method_a: ComparisonMethodResult;
  method_b: ComparisonMethodResult;
  winner: string | null;
  notes: string[];
};

async function parseErrorResponse(response: Response): Promise<string> {
  try {
    const data = (await response.json()) as { detail?: string };

    if (typeof data.detail === "string") {
      return data.detail;
    }

    return `Request failed with status ${response.status}`;
  } catch {
    return `Request failed with status ${response.status}`;
  }
}

export async function compareRetrievalPipelines(
  payload: ComparisonRequest,
  token: string,
): Promise<ComparisonResponse> {
  const response = await fetch(`${API_BASE_URL}/comparison`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(await parseErrorResponse(response));
  }

  return response.json() as Promise<ComparisonResponse>;
}
