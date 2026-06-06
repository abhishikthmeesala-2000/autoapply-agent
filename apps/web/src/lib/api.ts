export interface ApiHealthResponse {
  status: string;
}

export interface ApiConnectionState {
  reachable: boolean;
  baseUrl: string;
  statusText: string;
}

const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";
const REQUEST_TIMEOUT_MS = 1200;

export function getApiBaseUrl(): string {
  return (
    process.env.NEXT_PUBLIC_API_BASE_URL?.trim() ||
    process.env.API_BASE_URL?.trim() ||
    DEFAULT_API_BASE_URL
  );
}

async function fetchWithTimeout(input: string, init?: RequestInit): Promise<Response> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    return await fetch(input, {
      ...init,
      signal: controller.signal,
      cache: "no-store",
    });
  } finally {
    clearTimeout(timeout);
  }
}

export async function loadApiConnectionState(): Promise<ApiConnectionState> {
  const baseUrl = getApiBaseUrl();

  try {
    const response = await fetchWithTimeout(`${baseUrl}/health`);
    if (!response.ok) {
      return {
        reachable: false,
        baseUrl,
        statusText: `HTTP ${response.status}`,
      };
    }

    const payload = (await response.json()) as Partial<ApiHealthResponse>;
    return {
      reachable: true,
      baseUrl,
      statusText: payload.status ?? "ok",
    };
  } catch {
    return {
      reachable: false,
      baseUrl,
      statusText: "mock mode",
    };
  }
}

