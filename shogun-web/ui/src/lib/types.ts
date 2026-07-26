export type StatusLevel = 'online' | 'degraded' | 'offline' | 'unknown' | 'pending';

export type DepartmentKey =
  | 'hr'
  | 'finance'
  | 'crm'
  | 'marketing'
  | 'compliance'
  | 'support'
  | 'engineering'
  | 'projects'
  | 'product'
  | 'procurement';

export interface User {
  id: string;
  email: string;
  name: string;
  avatar_url?: string | null;
  first_login: boolean;
  must_change_password: boolean;
  company_id?: string | null;
  role?: string;
}

export interface Company {
  id: string;
  name: string;
  logo_url?: string | null;
  timezone: string;
}

export interface ProviderConfig {
  provider?: string;
  api_key?: string;
  subdomain?: string;
  base_url?: string;
  extra?: Record<string, string>;
}

export interface Department {
  key: DepartmentKey;
  name: string;
  persona: string;
  description: string;
  color: string;
  icon: string;
  active: boolean;
  status: StatusLevel;
  gateway_status?: StatusLevel;
  provider_status?: StatusLevel;
  provider_config?: ProviderConfig;
  profile_name?: string;
}

export interface OnboardingState {
  step: number;
  selected_departments: DepartmentKey[];
  company?: Partial<Company>;
  department_configs?: Partial<Record<DepartmentKey, ProviderConfig>>;
  completed: boolean;
  public_url?: string | null;
  subdomain?: string | null;
  go_live?: {
    ok?: boolean;
    public_url?: string | null;
    subdomain?: string | null;
    message?: string | null;
    tunnel?: Record<string, unknown>;
  };
}

export interface BrainPage {
  slug: string;
  title: string;
  type?: string;
  summary?: string;
  updated_at?: string;
  content?: string;
  tags?: string[];
}

export interface BrainLink {
  slug: string;
  title?: string;
  link_type?: string;
}

export interface DocumentArtifact {
  id: string;
  name: string;
  mime_type?: string;
  size_bytes?: number;
  created_at?: string;
  updated_at?: string;
  url?: string;
  preview_url?: string;
  description?: string;
}

export interface ChatToolCall {
  id: string;
  name: string;
  arguments?: unknown;
  result?: unknown;
  status?: 'running' | 'done' | 'error';
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  created_at?: string;
  tool_calls?: ChatToolCall[];
  streaming?: boolean;
}

export interface AuthResponse {
  access_token: string;
  token_type?: string;
  user: User;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface ChangePasswordPayload {
  current_password: string;
  new_password: string;
}

export interface ConnectionTestResult {
  ok: boolean;
  message: string;
  details?: Record<string, unknown>;
}

export const DEPARTMENT_CATALOG: Record<
  DepartmentKey,
  Omit<Department, 'active' | 'status' | 'gateway_status' | 'provider_status' | 'provider_config'>
> = {
  hr: {
    key: 'hr',
    name: 'HR',
    persona: 'Jinzai',
    description: 'People ops, leave, recruitment, and policy guidance.',
    color: '#ec4899',
    icon: 'Users',
    profile_name: 'hr-manager',
  },
  finance: {
    key: 'finance',
    name: 'Finance',
    persona: 'Koku',
    description: 'Budgets, expenses, grants, and financial reporting.',
    color: '#10b981',
    icon: 'Wallet',
    profile_name: 'finance-manager',
  },
  crm: {
    key: 'crm',
    name: 'CRM',
    persona: 'Eigyo',
    description: 'Pipeline, accounts, and sales intelligence.',
    color: '#3b82f6',
    icon: 'Handshake',
    profile_name: 'crm-manager',
  },
  marketing: {
    key: 'marketing',
    name: 'Marketing',
    persona: 'Kokuchi',
    description: 'Campaigns, content, and brand messaging.',
    color: '#f59e0b',
    icon: 'Megaphone',
    profile_name: 'marketing-manager',
  },
  compliance: {
    key: 'compliance',
    name: 'Compliance',
    persona: 'Junshu',
    description: 'Policies, audits, and regulatory tracking.',
    color: '#8b5cf6',
    icon: 'Shield',
    profile_name: 'compliance-manager',
  },
  support: {
    key: 'support',
    name: 'Support',
    persona: 'Shien',
    description: 'Tickets, SLAs, and customer success workflows.',
    color: '#06b6d4',
    icon: 'LifeBuoy',
    profile_name: 'customer-support',
  },
  engineering: {
    key: 'engineering',
    name: 'Engineering',
    persona: 'Gijutsu',
    description: 'Codebase ops, deployments, and technical delivery.',
    color: '#6366f1',
    icon: 'Code2',
    profile_name: 'engineering-manager',
  },
  projects: {
    key: 'projects',
    name: 'Projects',
    persona: 'Keikaku',
    description: 'Delivery plans, scrum cadences, and milestones.',
    color: '#f97316',
    icon: 'Kanban',
    profile_name: 'project-manager',
  },
  product: {
    key: 'product',
    name: 'Product',
    persona: 'Seihin',
    description: 'Roadmaps, research, and product decisions.',
    color: '#14b8a6',
    icon: 'Boxes',
    profile_name: 'product-manager',
  },
  procurement: {
    key: 'procurement',
    name: 'Procurement',
    persona: 'Chotatsu',
    description: 'Purchase orders, vendors, and contract lifecycle.',
    color: '#ef4444',
    icon: 'Package',
    profile_name: 'procurement-manager',
  },
};

export const DEPARTMENT_KEYS = Object.keys(DEPARTMENT_CATALOG) as DepartmentKey[];

export const TIMEZONES = [
  'Asia/Kuala_Lumpur',
  'Asia/Singapore',
  'Asia/Jakarta',
  'Asia/Bangkok',
  'Asia/Hong_Kong',
  'Asia/Tokyo',
  'Asia/Shanghai',
  'Asia/Kolkata',
  'Australia/Sydney',
  'Europe/London',
  'Europe/Berlin',
  'America/New_York',
  'America/Los_Angeles',
  'America/Chicago',
  'UTC',
];
