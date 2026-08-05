import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type Dispatch,
  type SetStateAction,
} from 'react';
import type {
  AccessInfo,
  AuthResponse,
  BrainLink,
  BrainPage,
  CeoDashboardStats,
  ChangePasswordPayload,
  ChatMessage,
  Company,
  ConnectionTestResult,
  CreateStaffPayload,
  DashboardConfig,
  Department,
  DepartmentKey,
  DocumentArtifact,
  FinanceDashboardStats,
  LoginPayload,
  OnboardingState,
  ProcurementDashboardStats,
  ProviderConfig,
  StaffMember,
  User,
} from './types';

const TOKEN_KEY = 'shogun_access_token';

export class ApiError extends Error {
  status: number;
  details?: unknown;

  constructor(message: string, status: number, details?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.details = details;
  }
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

async function parseError(res: Response): Promise<ApiError> {
  let message = res.statusText || 'Request failed';
  let details: unknown;
  try {
    const data = await res.json();
    details = data;
    if (typeof data?.detail === 'string') message = data.detail;
    else if (Array.isArray(data?.detail)) {
      message = data.detail.map((d: { msg?: string }) => d.msg || JSON.stringify(d)).join(', ');
    } else if (typeof data?.message === 'string') message = data.message;
    else if (typeof data?.error === 'string') message = data.error;
  } catch {
    // ignore
  }
  return new ApiError(message, res.status, details);
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers = new Headers(options.headers || {});
  const token = getToken();
  if (token) headers.set('Authorization', `Bearer ${token}`);
  if (options.body && !(options.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const res = await fetch(path.startsWith('/') ? path : `/api${path}`, {
    ...options,
    headers,
  });

  if (res.status === 204) return undefined as T;
  if (!res.ok) throw await parseError(res);

  const ct = res.headers.get('content-type') || '';
  if (ct.includes('application/json')) return (await res.json()) as T;
  return (await res.text()) as T;
}

function wsUrl(path: string): string {
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const token = getToken();
  const base = `${proto}//${window.location.host}${path}`;
  if (!token) return base;
  const sep = path.includes('?') ? '&' : '?';
  return `${base}${sep}token=${encodeURIComponent(token)}`;
}

export const authApi = {
  me: () => apiFetch<User>('/api/auth/me'),
  login: (payload: LoginPayload) =>
    apiFetch<AuthResponse>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  logout: () =>
    apiFetch<void>('/api/auth/logout', { method: 'POST' }).catch(() => undefined),
  changePassword: (payload: ChangePasswordPayload) =>
    apiFetch<User>('/api/auth/change-password', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  oauthUrl: (provider: 'google' | 'microsoft') => `/api/auth/oauth/${provider}`,
  oauthCallback: (params: URLSearchParams) =>
    apiFetch<AuthResponse>(`/api/auth/callback?${params.toString()}`),
  myAccess: () => apiFetch<AccessInfo>('/api/auth/me/access'),
};

export const staffApi = {
  list: () => apiFetch<{ staff: StaffMember[] }>('/api/staff'),
  get: (id: number) => apiFetch<{ user: StaffMember }>(`/api/staff/${id}`),
  create: (payload: CreateStaffPayload) =>
    apiFetch<{ ok: boolean; user: StaffMember; temporary_password?: string }>('/api/staff', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  update: (id: number, payload: Partial<CreateStaffPayload>) =>
    apiFetch<{ ok: boolean; user: StaffMember }>(`/api/staff/${id}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    }),
  remove: (id: number) =>
    apiFetch<{ ok: boolean }>(`/api/staff/${id}`, { method: 'DELETE' }),
  resetPassword: (id: number) =>
    apiFetch<{ ok: boolean; temporary_password: string }>(`/api/staff/${id}/reset-password`, {
      method: 'POST',
    }),
  importCsv: (file: File) => {
    const fd = new FormData();
    fd.append('file', file);
    return apiFetch<{ ok: boolean; created: number; updated: number; skipped: number; errors: string[]; temporary_passwords: Record<string, string> }>('/api/staff/import-csv', {
      method: 'POST',
      body: fd,
    });
  },
  directory: (params?: { q?: string; department?: string; role?: string; source?: string; limit?: number; offset?: number }) => {
    const sp = new URLSearchParams();
    if (params?.q) sp.set('q', params.q);
    if (params?.department) sp.set('department', params.department);
    if (params?.role) sp.set('role', params.role);
    if (params?.source) sp.set('source', params.source);
    if (params?.limit) sp.set('limit', String(params.limit));
    if (params?.offset) sp.set('offset', String(params.offset));
    return apiFetch<{ staff: StaffMember[]; total: number; limit: number; offset: number }>(`/api/staff/directory?${sp.toString()}`);
  },
  syncBriohr: () =>
    apiFetch<{ ok: boolean; created: number; updated: number; errors: string[]; synced_at?: string }>('/api/staff/sync-briohr', { method: 'POST' }),
};

export const onboardingApi = {
  get: () => apiFetch<OnboardingState>('/api/onboarding'),
  save: (state: Partial<OnboardingState>) =>
    apiFetch<OnboardingState>('/api/onboarding', {
      method: 'PUT',
      body: JSON.stringify(state),
    }),
  complete: async () => {
    const res = await apiFetch<{
      ok?: boolean;
      state?: OnboardingState;
      go_live?: GoLiveResult;
    } & Partial<OnboardingState>>('/api/onboarding/complete', { method: 'POST' });
    // Backend returns { ok, state, go_live }; normalize for SPA
    if (res && typeof res === 'object' && res.state) {
      return { ...res.state, go_live: res.go_live };
    }
    return res as OnboardingState & { go_live?: GoLiveResult };
  },
  goLive: (opts?: { create_tunnel?: boolean; force?: boolean }) =>
    apiFetch<GoLiveResult>('/api/onboarding/go-live', {
      method: 'POST',
      body: JSON.stringify({
        create_tunnel: opts?.create_tunnel ?? true,
        force: opts?.force ?? false,
      }),
    }),
  status: () => apiFetch<{ onboarding: OnboardingState; registry: RegistryStatus }>('/api/onboarding/status'),
};

export type GoLiveResult = {
  ok: boolean;
  public_url?: string | null;
  subdomain?: string | null;
  message?: string | null;
  skipped?: boolean;
  tunnel?: {
    token_saved?: boolean;
    token_path?: string;
    connector?: { started?: boolean; reason?: string; hint?: string };
  };
  onboarding?: OnboardingState;
};

export type RegistryStatus = {
  live: boolean;
  subdomain?: string;
  public_url?: string | null;
  company_name?: string;
  registry_url?: string;
  tunnel_token_present?: boolean;
  local_url?: string;
};

export const companyApi = {
  get: () => apiFetch<Company>('/api/company'),
  update: (data: Partial<Company> | FormData) => {
    if (data instanceof FormData) {
      return apiFetch<Company>('/api/company', { method: 'PUT', body: data });
    }
    return apiFetch<Company>('/api/company', {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },
};

export const departmentsApi = {
  list: async () => {
    const res = await apiFetch<Department[] | { departments: Department[] }>('/api/departments');
    if (Array.isArray(res)) return res;
    if (res && typeof res === 'object' && Array.isArray((res as { departments?: Department[] }).departments)) {
      return (res as { departments: Department[] }).departments;
    }
    return [];
  },
  get: (name: string) => apiFetch<Department>(`/api/departments/${name}`),
  activate: (name: string, config?: ProviderConfig) =>
    apiFetch<Department>(`/api/departments/${name}/activate`, {
      method: 'POST',
      body: JSON.stringify(config || {}),
    }),
  updateConfig: (name: string, config: ProviderConfig) =>
    apiFetch<Department>(`/api/departments/${name}/configure`, {
      method: 'POST',
      body: JSON.stringify(config),
    }),
  testConnection: (name: string, config?: ProviderConfig) =>
    apiFetch<ConnectionTestResult>(`/api/departments/${name}/test-connection`, {
      method: 'POST',
      body: JSON.stringify(config || {}),
    }),
  status: (name: string) =>
    apiFetch<{ status: string; gateway_status: string; provider_status: string }>(
      `/api/departments/${name}/status`,
    ),
  dashboardConfig: (name: string) =>
    apiFetch<DashboardConfig>(`/api/departments/${name}/dashboard`),
  dashboardCeoStats: (dept: string) =>
    apiFetch<CeoDashboardStats>(`/api/departments/${dept}/dashboard/ceo-stats`),
  dashboardFinanceStats: (dept: string) =>
    apiFetch<FinanceDashboardStats>(`/api/departments/${dept}/dashboard/finance-stats`),
  dashboardProcurementStats: (dept: string) =>
    apiFetch<ProcurementDashboardStats>(`/api/departments/${dept}/dashboard/procurement-stats`),
};

export const brainApi = {
  list: async (dept: string, q?: string) => {
    const qs = q ? `?q=${encodeURIComponent(q)}` : '';
    const res = await apiFetch<BrainPage[] | { pages?: BrainPage[] }>(`/api/departments/${dept}/brain${qs}`);
    if (Array.isArray(res)) return res;
    if (res && typeof res === 'object' && Array.isArray(res.pages)) return res.pages;
    return [];
  },
  get: (dept: string, slug: string) =>
    apiFetch<BrainPage>(`/api/departments/${dept}/brain/${encodeURIComponent(slug)}`),
  backlinks: (dept: string, slug: string) =>
    apiFetch<BrainLink[]>(
      `/api/departments/${dept}/brain/${encodeURIComponent(slug)}/backlinks`,
    ),
  search: async (dept: string, query: string) => {
    const res = await apiFetch<BrainPage[] | { pages?: BrainPage[] }>(
      `/api/departments/${dept}/brain/search?q=${encodeURIComponent(query)}`,
    );
    if (Array.isArray(res)) return res;
    if (res && typeof res === 'object' && Array.isArray(res.pages)) return res.pages;
    return [];
  },
};

export const docsApi = {
  list: async (dept: string) => {
    const res = await apiFetch<DocumentArtifact[] | { artifacts?: DocumentArtifact[]; docs?: DocumentArtifact[] }>(`/api/departments/${dept}/docs`);
    if (Array.isArray(res)) return res;
    if (res && typeof res === 'object') {
      if (Array.isArray(res.artifacts)) return res.artifacts;
      if (Array.isArray(res.docs)) return res.docs;
    }
    return [];
  },
  get: (dept: string, id: string) =>
    apiFetch<DocumentArtifact>(`/api/departments/${dept}/docs/${id}`),
  downloadUrl: (dept: string, id: string) =>
    `/api/departments/${dept}/docs/${id}/download`,
};

export const chatApi = {
  history: (dept: string) =>
    apiFetch<ChatMessage[]>(`/api/departments/${dept}/chat/history`),
};

export type ChatSocketEvent =
  | { type: 'message'; message: ChatMessage }
  | { type: 'delta'; id: string; content: string }
  | { type: 'tool_call'; id: string; tool_call: NonNullable<ChatMessage['tool_calls']>[number] }
  | { type: 'done'; id: string }
  | { type: 'error'; message: string }
  | { type: 'ping' };

export function useChatSocket(
  department: string | undefined,
  opts?: {
    enabled?: boolean;
    onEvent?: (event: ChatSocketEvent) => void;
  },
) {
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const onEventRef = useRef(opts?.onEvent);
  onEventRef.current = opts?.onEvent;

  useEffect(() => {
    if (!department || opts?.enabled === false) return;

    let closed = false;
    let retry = 0;
    let timer: number | undefined;

    const connect = () => {
      const url = wsUrl(`/ws/chat/${department}`);
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        if (closed) return;
        setConnected(true);
        setError(null);
        retry = 0;
      };

      ws.onmessage = (ev) => {
        try {
          const data = JSON.parse(ev.data) as ChatSocketEvent;
          onEventRef.current?.(data);
        } catch {
          // ignore malformed
        }
      };

      ws.onerror = () => {
        setError('WebSocket error');
      };

      ws.onclose = () => {
        setConnected(false);
        wsRef.current = null;
        if (closed) return;
        const delay = Math.min(1000 * 2 ** retry, 15000);
        retry += 1;
        timer = window.setTimeout(connect, delay);
      };
    };

    connect();

    return () => {
      closed = true;
      if (timer) window.clearTimeout(timer);
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, [department, opts?.enabled]);

  const send = useCallback((content: string) => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      throw new Error('Chat is not connected');
    }
    ws.send(JSON.stringify({ type: 'message', content }));
  }, []);

  return { connected, error, send };
}

export function mergeDepartments(apiDepts: Department[] | undefined): Department[] {
  const byKey = new Map((apiDepts || []).map((d) => [d.key, d]));
  const keys = Object.keys(
    // lazy import avoided — catalog is with types
    {
      hr: 1,
      finance: 1,
      crm: 1,
      marketing: 1,
      compliance: 1,
      support: 1,
      engineering: 1,
      projects: 1,
      product: 1,
      procurement: 1,
    },
  ) as DepartmentKey[];

  // Use static catalog from module via require pattern — import already exists in consumers.
  return keys.map((key) => {
    const remote = byKey.get(key);
    return {
      key,
      name: remote?.name || key,
      persona: remote?.persona || '',
      description: remote?.description || '',
      color: remote?.color || '#6366f1',
      icon: remote?.icon || 'Boxes',
      active: remote?.active ?? false,
      status: remote?.status || 'offline',
      gateway_status: remote?.gateway_status,
      provider_status: remote?.provider_status,
      provider_config: remote?.provider_config,
      profile_name: remote?.profile_name,
    };
  });
}

export type SetMessages = Dispatch<SetStateAction<ChatMessage[]>>;
