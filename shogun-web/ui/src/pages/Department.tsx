import { FormEvent, useMemo, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  ArrowLeft,
  Brain,
  FileText,
  Loader2,
  MessageSquare,
  BarChart3,
  Settings,
} from 'lucide-react';
import clsx from 'clsx';
import toast from 'react-hot-toast';
import BrainViewer from '../components/BrainViewer';
import Chat from '../components/Chat';
import DocsViewer from '../components/DocsViewer';
import { DashboardViewer } from '../components/dashboards/DashboardViewer';
import StatusBadge from '../components/StatusBadge';
import { departmentsApi } from '../lib/api';
import {
  DEPARTMENT_CATALOG,
  type DepartmentKey,
  type ProviderConfig,
} from '../lib/types';

const TABS = [
  { id: 'chat', label: 'Chat', icon: MessageSquare },
  { id: 'brain', label: 'Brain', icon: Brain },
  { id: 'docs', label: 'Docs', icon: FileText },
  { id: 'dashboard', label: 'Dashboard', icon: BarChart3 },
  { id: 'settings', label: 'Settings', icon: Settings },
] as const;

type TabId = (typeof TABS)[number]['id'];

export default function Department() {
  const { name = '' } = useParams();
  const key = name.toLowerCase() as DepartmentKey;
  const [searchParams, setSearchParams] = useSearchParams();
  const tabParam = (searchParams.get('tab') || 'chat') as TabId;
  const tab = TABS.some((t) => t.id === tabParam) ? tabParam : 'chat';
  const queryClient = useQueryClient();

  const meta = DEPARTMENT_CATALOG[key];
  const deptQuery = useQuery({
    queryKey: ['department', key],
    queryFn: () => departmentsApi.get(key),
    enabled: !!meta,
  });

  const statusQuery = useQuery({
    queryKey: ['department-status', key],
    queryFn: () => departmentsApi.status(key),
    enabled: !!meta,
    refetchInterval: 30_000,
  });

  const department = deptQuery.data;
  const displayName = department?.name || meta?.name || key;
  const persona = department?.persona || meta?.persona || '';
  const color = department?.color || meta?.color || '#6366f1';
  const status =
    statusQuery.data?.status ||
    department?.status ||
    department?.gateway_status ||
    'unknown';

  const [config, setConfig] = useState<ProviderConfig>({});
  const configReady = useMemo(() => {
    if (department?.provider_config) {
      return department.provider_config;
    }
    return {};
  }, [department]);

  // hydrate local form when remote loads
  useMemo(() => {
    if (configReady && Object.keys(config).length === 0) {
      setConfig(configReady);
    }
  }, [configReady]); // eslint-disable-line react-hooks/exhaustive-deps

  const saveMutation = useMutation({
    mutationFn: (payload: ProviderConfig) => departmentsApi.updateConfig(key, payload),
    onSuccess: async () => {
      toast.success('Settings saved');
      await queryClient.invalidateQueries({ queryKey: ['department', key] });
    },
    onError: (err: Error) => toast.error(err.message || 'Save failed'),
  });

  const testMutation = useMutation({
    mutationFn: () => departmentsApi.testConnection(key, config),
    onSuccess: (res) => {
      if (res.ok) toast.success(res.message || 'Connection OK');
      else toast.error(res.message || 'Connection failed');
    },
    onError: (err: Error) => toast.error(err.message || 'Test failed'),
  });

  const setTab = (id: TabId) => {
    setSearchParams({ tab: id });
  };

  if (!meta && !deptQuery.isLoading) {
    return (
      <div className="mx-auto max-w-lg rounded-xl border border-surface-border bg-white p-8 text-center">
        <h1 className="text-lg font-semibold">Department not found</h1>
        <p className="mt-2 text-sm text-slate-500">“{name}” is not a known department.</p>
        <Link to="/dashboard" className="btn-primary mt-6 inline-flex">
          Back to dashboard
        </Link>
      </div>
    );
  }

  const onSave = (e: FormEvent) => {
    e.preventDefault();
    saveMutation.mutate(config);
  };

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-4 lg:flex-row">
      <aside className="w-full shrink-0 lg:w-52">
        <Link
          to="/dashboard"
          className="mb-3 inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-800"
        >
          <ArrowLeft className="h-4 w-4" />
          Dashboard
        </Link>

        <div className="card mb-3 p-4 lg:mb-4">
          <div className="flex items-center gap-3">
            <div
              className="flex h-10 w-10 items-center justify-center rounded-xl text-sm font-bold text-white"
              style={{ backgroundColor: color }}
            >
              {(displayName || '?').charAt(0)}
            </div>
            <div className="min-w-0">
              <div className="truncate font-semibold text-slate-900">{displayName}</div>
              <div className="truncate text-xs text-slate-500">{persona}</div>
            </div>
          </div>
          <div className="mt-3">
            <StatusBadge status={status} />
          </div>
        </div>

        <nav className="flex gap-1 overflow-x-auto lg:flex-col lg:overflow-visible">
          {TABS.map((t) => {
            const Icon = t.icon;
            const active = tab === t.id;
            return (
              <button
                key={t.id}
                type="button"
                onClick={() => setTab(t.id)}
                className={clsx(
                  'flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition whitespace-nowrap',
                  active
                    ? 'bg-white text-slate-900 shadow-sm ring-1 ring-surface-border'
                    : 'text-slate-600 hover:bg-white/70',
                )}
              >
                <Icon className="h-4 w-4" />
                {t.label}
              </button>
            );
          })}
        </nav>
      </aside>

      <div className="min-w-0 flex-1">
        <header className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-xl font-semibold text-slate-900">
              {displayName}
              <span className="ml-2 text-base font-normal text-slate-400">{persona}</span>
            </h1>
            <p className="text-sm text-slate-500">{meta?.description}</p>
          </div>
          <StatusBadge
            status={statusQuery.data?.gateway_status || department?.gateway_status || status}
            label={`Gateway: ${statusQuery.data?.gateway_status || department?.gateway_status || status}`}
            size="md"
          />
        </header>

        {deptQuery.isLoading && (
          <div className="flex justify-center py-16 text-slate-400">
            <Loader2 className="h-7 w-7 animate-spin" />
          </div>
        )}

        {!deptQuery.isLoading && tab === 'chat' && <Chat department={key} />}
        {!deptQuery.isLoading && tab === 'brain' && <BrainViewer department={key} />}
        {!deptQuery.isLoading && tab === 'docs' && <DocsViewer department={key} />}
        {!deptQuery.isLoading && tab === 'dashboard' && (
          <DashboardViewer department={key} color={color} />
        )}
        {!deptQuery.isLoading && tab === 'settings' && (
          <form className="card max-w-2xl space-y-4 p-6" onSubmit={onSave}>
            <div>
              <h2 className="text-base font-semibold text-slate-900">Provider configuration</h2>
              <p className="text-sm text-slate-500">
                Credentials and endpoints for this department&apos;s integrations.
              </p>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <div className="sm:col-span-2">
                <label className="label">Provider</label>
                <input
                  className="input"
                  value={config.provider || ''}
                  onChange={(e) => setConfig((c) => ({ ...c, provider: e.target.value }))}
                />
              </div>
              <div>
                <label className="label">Subdomain</label>
                <input
                  className="input"
                  value={config.subdomain || ''}
                  onChange={(e) => setConfig((c) => ({ ...c, subdomain: e.target.value }))}
                />
              </div>
              <div>
                <label className="label">Base URL</label>
                <input
                  className="input"
                  value={config.base_url || ''}
                  onChange={(e) => setConfig((c) => ({ ...c, base_url: e.target.value }))}
                />
              </div>
              <div className="sm:col-span-2">
                <label className="label">API key</label>
                <input
                  type="password"
                  className="input"
                  value={config.api_key || ''}
                  onChange={(e) => setConfig((c) => ({ ...c, api_key: e.target.value }))}
                  placeholder="••••••••"
                />
              </div>
            </div>

            <div className="rounded-lg border border-surface-border bg-surface-muted px-4 py-3">
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                Gateway status
              </div>
              <div className="mt-2 flex flex-wrap gap-4">
                <StatusBadge
                  status={statusQuery.data?.gateway_status || department?.gateway_status}
                  label={`Gateway · ${statusQuery.data?.gateway_status || department?.gateway_status || 'unknown'}`}
                />
                <StatusBadge
                  status={statusQuery.data?.provider_status || department?.provider_status}
                  label={`Provider · ${statusQuery.data?.provider_status || department?.provider_status || 'unknown'}`}
                />
              </div>
            </div>

            <div className="flex flex-wrap gap-2 pt-2">
              <button type="submit" className="btn-primary" disabled={saveMutation.isPending}>
                {saveMutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
                Save settings
              </button>
              <button
                type="button"
                className="btn-secondary"
                disabled={testMutation.isPending}
                onClick={() => testMutation.mutate()}
              >
                {testMutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
                Test connection
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
