import { API_BASE_URL } from "@/lib/api";

export type AnswerSource = {
  document_id: number;
  page_number?: number | null;
  chunk_index: number;
  source_filename: string;
  document_chunk_id: number;
  score: number;
  text: string;
};

export type AnswerResponse = {
  question: string;
  answer: string;
  context_used: boolean;
  sources_count: number;
  sources: AnswerSource[];
};

export type AskQuestionPayload = {
  question: string;
  document_id?: number | null;
  top_k: number;
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

export async function askDocumentQuestion(
  payload: AskQuestionPayload,
  token: string,
): Promise<AnswerResponse> {
  const response = await fetch(`${API_BASE_URL}/answer`, {
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

  return response.json() as Promise<AnswerResponse>;
}
