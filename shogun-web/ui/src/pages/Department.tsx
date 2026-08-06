import { FormEvent, useMemo, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Brain,
  History,
  Loader2,
  BarChart3,
  Settings,
} from 'lucide-react';
import toast from 'react-hot-toast';
import BrainViewer from '../components/BrainViewer';
import ChatHistory from '../components/ChatHistory';
import RightChatDock from '../components/RightChatDock';
import { DashboardViewer } from '../components/dashboards/DashboardViewer';
import StatusBadge from '../components/StatusBadge';
import { departmentsApi } from '../lib/api';
import { useAuth } from '../lib/auth';
import {
  DEPARTMENT_CATALOG,
  type DepartmentKey,
  type ProviderConfig,
} from '../lib/types';

const TABS: { id: string; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
  { id: 'dashboard', label: 'Dashboard', icon: BarChart3 },
  { id: 'chat-history', label: 'Chat History', icon: History },
  { id: 'brain', label: 'Brain', icon: Brain },
  { id: 'settings', label: 'Settings', icon: Settings },
];

type TabId = string;

export default function Department() {
  const { name = '' } = useParams();
  const key = name.toLowerCase() as DepartmentKey;
  const { user } = useAuth();
  const [searchParams] = useSearchParams();
  const tabParam = (searchParams.get('tab') || 'dashboard') as TabId;

  const tabs = useMemo(() => {
    if (user?.role === 'admin' || user?.role === 'owner') return TABS;
    return TABS.filter((t) => t.id !== 'settings');
  }, [user?.role]);

  const tab = tabs.some((t) => t.id === tabParam) ? tabParam : tabs[0]?.id || 'dashboard';
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
  const displayName = meta?.name || (department?.name ? department.name.charAt(0).toUpperCase() + department.name.slice(1) : key);
  const persona = department?.persona || meta?.persona || '';
  const color = department?.color || meta?.color || '#6366f1';

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

  if (!meta && !deptQuery.isLoading) {
    return (
      <div className="sd-empty" style={{ marginTop: '2rem' }}>
        <h2>Department not found</h2>
        <p style={{ color: 'var(--samurai-muted)' }}>“{name}” is not a known department.</p>
        <Link to="/dashboard" className="sd-btn sd-btn-primary" style={{ marginTop: '0.75rem' }}>
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
    <div className="flex w-full h-[calc(100vh-3.5rem)] overflow-hidden">
      {/* Main Content Area */}
      <div className="flex-1 min-w-0 overflow-y-auto p-4 md:p-6 space-y-4">
        {deptQuery.isLoading && (
          <div className="sd-empty">
            <div className="h-7 w-7 animate-spin rounded-full" style={{ border: '2px solid var(--samurai-lime)', borderTopColor: 'transparent' }} />
            <p>Loading department…</p>
          </div>
        )}

        {!deptQuery.isLoading && tab === 'dashboard' && (
          <DashboardViewer department={key} color={color} />
        )}
        {!deptQuery.isLoading && (tab === 'chat-history' || tab === 'chat') && (
          <ChatHistory department={key} />
        )}
        {!deptQuery.isLoading && tab === 'brain' && <BrainViewer department={key} />}
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

      {/* Resizable Fixed Right Dock Chat */}
      <RightChatDock
        department={key}
        displayName={displayName}
        persona={persona}
        color={color}
      />
    </div>
  );
}
