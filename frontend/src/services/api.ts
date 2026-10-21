const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8080/api/v1';

class ApiClient {
  private token: string | null = null;

  setToken(token: string | null) {
    this.token = token;
  }

  getToken(): string | null {
    return this.token;
  }

  async request<T>(
    endpoint: string,
    options: {
      method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
      body?: any;
      headers?: Record<string, string>;
      idempotencyKey?: string;
    } = {}
  ): Promise<{ data: T; correlationId?: string }> {
    const { method = 'GET', body, headers = {}, idempotencyKey } = options;

    const correlationId = 'corr-' + Math.random().toString(36).substring(2, 10);
    const requestHeaders: Record<string, string> = {
      'Content-Type': 'application/json',
      'X-Correlation-ID': correlationId,
      ...headers,
    };

    if (this.token) {
      requestHeaders['Authorization'] = `Bearer ${this.token}`;
    }

    if (idempotencyKey) {
      requestHeaders['Idempotency-Key'] = idempotencyKey;
    }

    const config: RequestInit = {
      method,
      headers: requestHeaders,
    };

    if (body && method !== 'GET') {
      config.body = JSON.stringify(body);
    }

    const response = await fetch(`${API_BASE_URL}${endpoint}`, config);

    // Handle HTTP 409 Conflict (Optimistic Concurrency / Offline draft conflict)
    if (response.status === 409) {
      const errorJson = await response.json();
      const conflictError: any = new Error('Conflicto de versión detectado');
      conflictError.status = 409;
      conflictError.conflictData = errorJson.detail;
      throw conflictError;
    }

    if (!response.ok) {
      let errorMsg = `Error ${response.status}: ${response.statusText}`;
      try {
        const errJson = await response.json();
        if (errJson.detail) {
          if (typeof errJson.detail === 'string') {
            errorMsg = errJson.detail;
          } else if (errJson.detail.message) {
            errorMsg = errJson.detail.message;
          } else if (Array.isArray(errJson.detail)) {
            errorMsg = errJson.detail.map((e: any) => e.msg || e).join(', ');
          }
        }
      } catch (_) {}
      throw new Error(errorMsg);
    }

    const json = await response.json();
    return {
      data: json.data !== undefined ? json.data : json,
      correlationId: response.headers.get('X-Correlation-ID') || correlationId,
    };
  }
}

export const api = new ApiClient();
