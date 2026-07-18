import { API_BASE_URL } from "@/lib/api";

export type UploadedDocument = {
  id: number;
  owner_id: number;
  filename: string;
  original_filename: string;
  file_type: string;
  file_path: string;
  file_size: number;
  status: string;
  created_at?: string;
  updated_at?: string;
};

export type DocumentProcessResponse = {
  document_id: number;
  original_filename: string;
  file_type: string;
  status: string;
  text_length: number;
  chunk_count: number;
  message: string;
  extracted_text?: string;
};

export type DocumentIndexResponse = {
  document_id: number;
  original_filename: string;
  status: string;
  indexed_chunks: number;
  collection: string;
  embedding_provider: string;
  embedding_model: string;
  vector_size: number;
  message: string;
};

export type DocumentStatusResponse = {
  document_id: number;
  original_filename: string;
  file_type: string;
  status: string;
  owner_id: number;
  created_at: string;
  updated_at: string;
};

type UploadDocumentArgs = {
  file: File;
  token: string;
  onProgress: (progress: number) => void;
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

function parseXhrError(xhr: XMLHttpRequest): string {
  try {
    const data = JSON.parse(xhr.responseText) as { detail?: string };

    if (typeof data.detail === "string") {
      return data.detail;
    }

    return `Upload failed with status ${xhr.status}`;
  } catch {
    return `Upload failed with status ${xhr.status}`;
  }
}

export function uploadDocument({
  file,
  token,
  onProgress,
}: UploadDocumentArgs): Promise<UploadedDocument> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const formData = new FormData();

    formData.append("file", file);

    xhr.open("POST", `${API_BASE_URL}/documents/upload`);
    xhr.setRequestHeader("Authorization", `Bearer ${token}`);

    xhr.upload.onprogress = (event) => {
      if (!event.lengthComputable) {
        return;
      }

      const progress = Math.round((event.loaded / event.total) * 100);
      onProgress(progress);
    };

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        const data = JSON.parse(xhr.responseText) as UploadedDocument;
        onProgress(100);
        resolve(data);
        return;
      }

      reject(new Error(parseXhrError(xhr)));
    };

    xhr.onerror = () => {
      reject(new Error("Upload failed. Check backend connection or CORS."));
    };

    xhr.send(formData);
  });
}

export async function processDocument(
  documentId: number,
  token: string,
): Promise<DocumentProcessResponse> {
  const response = await fetch(
    `${API_BASE_URL}/documents/${documentId}/process`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
      },
    },
  );

  if (!response.ok) {
    throw new Error(await parseErrorResponse(response));
  }

  return response.json() as Promise<DocumentProcessResponse>;
}

export async function indexDocument(
  documentId: number,
  token: string,
): Promise<DocumentIndexResponse> {
  const response = await fetch(
    `${API_BASE_URL}/documents/${documentId}/index`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
      },
    },
  );

  if (!response.ok) {
    throw new Error(await parseErrorResponse(response));
  }

  return response.json() as Promise<DocumentIndexResponse>;
}

export async function getDocumentStatus(
  documentId: number,
  token: string,
): Promise<DocumentStatusResponse> {
  const response = await fetch(
    `${API_BASE_URL}/documents/${documentId}/status`,
    {
      method: "GET",
      headers: {
        Authorization: `Bearer ${token}`,
      },
    },
  );

  if (!response.ok) {
    throw new Error(await parseErrorResponse(response));
  }

  return response.json() as Promise<DocumentStatusResponse>;
}
