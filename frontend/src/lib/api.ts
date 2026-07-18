export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type ApiUser = {
  id: number;
  full_name: string;
  email: string;
  created_at: string;
};

export type RegisterPayload = {
  full_name: string;
  email: string;
  password: string;
};

export type LoginPayload = {
  email: string;
  password: string;
};

export type LoginResponse = {
  access_token: string;
  token_type: string;
};

type ApiErrorResponse = {
  detail?: string;
};

async function parseApiError(response: Response): Promise<string> {
  try {
    const data = (await response.json()) as ApiErrorResponse;

    if (typeof data.detail === "string") {
      return data.detail;
    }

    return `Request failed with status ${response.status}`;
  } catch {
    return `Request failed with status ${response.status}`;
  }
}

export async function registerUser(
  payload: RegisterPayload,
): Promise<ApiUser> {
  const response = await fetch(`${API_BASE_URL}/auth/register`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(await parseApiError(response));
  }

  return response.json() as Promise<ApiUser>;
}

export async function loginUser(payload: LoginPayload): Promise<LoginResponse> {
  const formData = new URLSearchParams();

  formData.set("username", payload.email);
  formData.set("password", payload.password);

  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: formData.toString(),
  });

  if (!response.ok) {
    throw new Error(await parseApiError(response));
  }

  return response.json() as Promise<LoginResponse>;
}

export async function getCurrentUser(token: string): Promise<ApiUser> {
  const response = await fetch(`${API_BASE_URL}/auth/me`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    throw new Error(await parseApiError(response));
  }

  return response.json() as Promise<ApiUser>;
}
