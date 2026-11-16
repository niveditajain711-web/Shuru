import type { Lang, Run } from "./types";

const FALLBACK_MESSAGE = "Something went wrong. Please try again.";
const INVALID_INPUT_MESSAGE = "Please check what you entered and try again.";
const NETWORK_MESSAGE = "We couldn't reach the server. Check your connection and try again.";

/** An error whose message is safe and plain enough to show to the user. */
export class ApiError extends Error {
  constructor(
    message: string,
    readonly code: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api${path}`, init);
  } catch (cause) {
    console.error("network error", path, cause);
    throw new ApiError(NETWORK_MESSAGE, "network_error");
  }

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const error = body?.error;
    console.error("api error", path, response.status, error ?? body);
    if (response.status === 422 && !error) {
      // FastAPI's own request validation uses a different body than our errors.
      throw new ApiError(INVALID_INPUT_MESSAGE, "invalid_input");
    }
    throw new ApiError(error?.message ?? FALLBACK_MESSAGE, error?.code ?? "unknown_error");
  }
  return (await response.json()) as T;
}

function post<T>(path: string, body?: unknown): Promise<T> {
  return request<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

export const api = {
  createRun: (idea: string, lang: Lang) => post<Run>("/runs", { idea, lang }),

  listDomains: (runId: string, keyword?: string) => {
    const query = keyword ? `?keyword=${encodeURIComponent(keyword)}` : "";
    return request<Run>(`/runs/${runId}/domains${query}`);
  },

  chooseDomain: (runId: string, domain: string) => post<Run>(`/runs/${runId}/domain`, { domain }),

  regenerateSite: (runId: string) => post<Run>(`/runs/${runId}/regenerate`),

  previewUrl: (runId: string, lang: Lang, version: number) =>
    `/api/runs/${runId}/preview?lang=${lang}&v=${version}`,
};
