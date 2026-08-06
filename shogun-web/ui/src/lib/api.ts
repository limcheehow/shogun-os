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
  ChatAttachment,
  ChatMessage,
  Company,
  ConnectionTestResult,
  Connector,
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
  Skill,
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
  return localStorage.getItem(TOKEN_KEY) || sessionStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null, keepSignedIn: boolean = true) {
  if (token) {
    if (keepSignedIn) {
      localStorage.setItem(TOKEN_KEY, token);
      sessionStorage.removeItem(TOKEN_KEY);
    } else {
      sessionStorage.setItem(TOKEN_KEY, token);
      localStorage.removeItem(TOKEN_KEY);
    }
  } else {
    localStorage.removeItem(TOKEN_KEY);
    sessionStorage.removeItem(TOKEN_KEY);
  }
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
  const host = window.location.port === '5173' ? '127.0.0.1:8000' : window.location.host;
  const base = `${proto}//${host}${path}`;
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
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const res = await apiFetch<any>(`/api/departments/${dept}/brain${qs}`);
    const files = res?.files || (Array.isArray(res) ? res : res?.pages || res?.result?.pages || []);
    const folders = res?.folders || [];
    return { files, folders };
  },
  getFileContent: (dept: string, path: string) =>
    apiFetch<{ name: string; path: string; ext: string; content: string }>(
      `/api/departments/${dept}/brain/file-content?path=${encodeURIComponent(path)}`,
    ),
  get: (dept: string, slug: string) =>
    apiFetch<BrainPage>(`/api/departments/${dept}/brain/${encodeURIComponent(slug)}`),
  backlinks: (dept: string, slug: string) =>
    apiFetch<BrainLink[]>(
      `/api/departments/${dept}/brain/${encodeURIComponent(slug)}/backlinks`,
    ),
  search: async (dept: string, query: string) => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const res = await apiFetch<any>(
      `/api/departments/${dept}/brain/search?q=${encodeURIComponent(query)}`,
    );
    const files = res?.files || (Array.isArray(res) ? res : res?.pages || res?.result?.pages || []);
    const folders = res?.folders || [];
    return { files, folders };
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
  saveMessages: (dept: string, messages: ChatMessage[]) =>
    apiFetch<{ ok: boolean; saved_count: number }>(`/api/departments/${dept}/chat/messages`, {
      method: 'POST',
      body: JSON.stringify({ messages }),
    }),
  uploadFile: async (dept: string, file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    const token = getToken();
    const headers: Record<string, string> = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const res = await fetch(`/api/departments/${dept}/chat/upload`, {
      method: 'POST',
      headers,
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Upload failed' }));
      throw new Error(err.detail || 'Upload failed');
    }
    return res.json() as Promise<{
      ok: boolean;
      attachment: {
        id: string;
        name: string;
        url: string;
        mime_type: string;
        size_bytes: number;
        is_image: boolean;
      };
    }>;
  },
};

export const connectorsApi = {
  list: (dept: string) =>
    apiFetch<{ connectors: Connector[] }>(`/api/departments/${dept}/connectors`),
  toggle: (dept: string, connectorId: string) =>
    apiFetch<{ ok: boolean; connector: Connector }>(`/api/departments/${dept}/connectors/${connectorId}/toggle`, {
      method: 'POST',
    }),
};

export interface SkillRecommendation {
  explanation: string;
  recommendations: Array<{ skill_id: string; match_pct: number; reason: string }>;
  shogunify_suggestion?: {
    needed: boolean;
    mode: string;
    command: string;
    description: string;
  };
}

export const skillsApi = {
  listAll: () => apiFetch<{ skills: Skill[] }>('/api/skills'),
  listDepartment: (dept: string) =>
    apiFetch<{ skills: Skill[] }>(`/api/departments/${dept}/skills`),
  install: (skillId: string, dept?: string) =>
    apiFetch<{ ok: boolean; skill: Skill }>('/api/skills/install', {
      method: 'POST',
      body: JSON.stringify({ skill_id: skillId, department: dept }),
    }),
  deleteDepartmentSkill: (dept: string, skillId: string) =>
    apiFetch<{ ok: boolean }>(`/api/departments/${dept}/skills/${skillId}`, {
      method: 'DELETE',
    }),
  recommend: (prompt: string) =>
    apiFetch<SkillRecommendation>('/api/skills/recommend', {
      method: 'POST',
      body: JSON.stringify({ prompt }),
    }),
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
    resetKey?: number;
  },
) {
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const onEventRef = useRef(opts?.onEvent);
  onEventRef.current = opts?.onEvent;

  useEffect(() => {
    if (!department || opts?.enabled === false) return;

    let isMounted = true;
    let timer: number | undefined;

    const connect = () => {
      if (!isMounted) return;

      if (wsRef.current && (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING)) {
        return;
      }

      const url = wsUrl(`/api/gateway/${department}`);
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        if (!isMounted) return;
        setConnected(true);
        setError(null);
      };

      ws.onmessage = (ev) => {
        if (!isMounted) return;
        try {
          const raw = JSON.parse(ev.data);
          if (raw?.type === 'shogun.proxy.ready') {
            setConnected(true);
            return;
          }
          if (raw?.type === 'shogun.proxy.error') {
            setError(raw?.error || 'Gateway unavailable');
            setConnected(false);
            return;
          }
          const known = ['message', 'delta', 'tool_call', 'done', 'error', 'ping'];
          if (raw && typeof raw.type === 'string' && known.includes(raw.type)) {
            onEventRef.current?.(raw as ChatSocketEvent);
            return;
          }
          const id = raw?.id || raw?.message_id || `hermes-${Date.now()}`;
          const content =
            typeof raw?.content === 'string' ? raw.content
            : typeof raw?.text === 'string' ? raw.text
            : typeof raw?.delta === 'string' ? raw.delta
            : '';
          if (content) {
            onEventRef.current?.({ type: 'delta', id, content });
          } else if (raw?.type === 'end' || raw?.done) {
            onEventRef.current?.({ type: 'done', id });
          }
        } catch {
          // ignore malformed
        }
      };

      ws.onerror = () => {
        if (!isMounted) return;
      };

      ws.onclose = () => {
        if (!isMounted) return;
        setConnected(false);
        wsRef.current = null;
        timer = window.setTimeout(connect, 3000);
      };
    };

    connect();

    return () => {
      isMounted = false;
      if (timer) window.clearTimeout(timer);
      if (wsRef.current) {
        const ws = wsRef.current;
        wsRef.current = null;
        if (ws.readyState === WebSocket.OPEN) {
          ws.close();
        }
      }
    };
  }, [department, opts?.enabled, opts?.resetKey]);

  const send = useCallback((content: string, attachments?: ChatAttachment[]) => {
    const ws = wsRef.current;
    const payload = attachments && attachments.length > 0
      ? { type: 'message', content, attachments }
      : { type: 'message', content };
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(payload));
    } else if (ws && ws.readyState === WebSocket.CONNECTING) {
      ws.addEventListener(
        'open',
        () => {
          ws.send(JSON.stringify(payload));
        },
        { once: true },
      );
    }
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
      name: remote?.name ? (remote.name.charAt(0).toUpperCase() + remote.name.slice(1)) : (key.charAt(0).toUpperCase() + key.slice(1)),
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
