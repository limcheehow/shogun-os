import { useMemo, useState } from 'react';
import { Link, Navigate } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Boxes, Code2, Copy, ExternalLink, Globe2, Handshake, Kanban, LayoutDashboard,
  LifeBuoy, Loader2, Megaphone, MessageSquare, Package, Plus, Shield, Users, Wallet, Brain,
  type LucideIcon,
} from 'lucide-react';
import toast from 'react-hot-toast';
import { authApi, departmentsApi, onboardingApi } from '../lib/api';
import { useAuth } from '../lib/auth';
import {
  DEPARTMENT_CATALOG,
  DEPARTMENT_KEYS,
  type Department,
  type DepartmentKey,
} from '../lib/types';

const ICONS: Record<string, LucideIcon> = {
  Users, Wallet, Handshake, Megaphone, Shield, LifeBuoy, Code2, Kanban, Boxes, Package,
};

function mergeCatalog(remote: Department[] | undefined): Department[] {
  const map = new Map((remote || []).map((d) => [d.key || (d as { name?: string }).name, d]));
  return DEPARTMENT_KEYS.map((key) => {
    const base = DEPARTMENT_CATALOG[key];
    const r = map.get(key);
    return {
      ...base,
      ...r,
      key,
      name: base?.name || (r?.name ? r.name.charAt(0).toUpperCase() + r.name.slice(1) : key),
      persona: r?.persona || base.persona,
      description: r?.description || base.description,
      color: r?.color || base.color,
      icon: r?.icon || base.icon,
      active: r?.active ?? (r as { status?: string } | undefined)?.status === 'active',
      status: r?.status || 'offline',
      gateway_status: r?.gateway_status,
      provider_status: r?.provider_status,
      provider_config: r?.provider_config,
      profile_name: r?.profile_name || base.profile_name,
    };
  });
}

export default function Dashboard() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [adding, setAdding] = useState<DepartmentKey | null>(null);

  const deptsQuery = useQuery({
    queryKey: ['departments'],
    queryFn: () => departmentsApi.list(),
  });

  const statusQuery = useQuery({
    queryKey: ['onboarding-status'],
    queryFn: () => onboardingApi.status(),
    staleTime: 30_000,
  });

  const publicUrl = statusQuery.data?.registry?.public_url || statusQuery.data?.onboarding?.public_url;
  const isLive = Boolean(statusQuery.data?.registry?.live || publicUrl);

  // Non-admin users: redirect to first assigned department or no-access
  const accessQuery = useQuery({
    queryKey: ['my-access'],
    queryFn: () => authApi.myAccess(),
    staleTime: 30_000,
  });

  if (accessQuery.data && user?.role !== 'admin' && user?.role !== 'owner') {
    if (!accessQuery.data.has_access) {
      return <Navigate to="/no-access" replace />;
    }
    if (accessQuery.data.assigned_departments.length > 0) {
      return <Navigate to={`/department/${accessQuery.data.assigned_departments[0].department}`} replace />;
    }
  }

  const departments = useMemo(() => mergeCatalog(deptsQuery.data), [deptsQuery.data]);
  const active = departments.filter((d) => d.active);
  const inactive = departments.filter((d) => !d.active);

  const activateMutation = useMutation({
    mutationFn: (key: DepartmentKey) => departmentsApi.activate(key, {}),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['departments'] });
      toast.success('Department activated');
      setAdding(null);
    },
    onError: (err: Error) => toast.error(err.message || 'Failed to activate'),
  });

  const goLiveMutation = useMutation({
    mutationFn: () => onboardingApi.goLive({ create_tunnel: true, force: false }),
    onSuccess: async (res) => {
      await queryClient.invalidateQueries({ queryKey: ['onboarding-status'] });
      toast.success(res.public_url ? `Live: ${res.public_url}` : 'Go live complete');
    },
    onError: (err: Error) => toast.error(err.message || 'Go live failed'),
  });

  return (
    <div className="mx-auto max-w-6xl">
      {isLive && publicUrl ? (
        <div className="sd-banner ok">
          <Globe2 className="h-5 w-5" style={{ color: 'var(--samurai-ok)' }} />
          <div className="flex-1 min-w-0">
            <div className="text-sm font-semibold">Public company URL</div>
            <a href={publicUrl} target="_blank" rel="noreferrer" className="break-all text-sm font-medium" style={{ color: 'var(--samurai-lime)' }}>
              {publicUrl}
            </a>
          </div>
          <div className="flex gap-2">
            <button
              type="button"
              className="sd-btn sd-btn-secondary"
              onClick={() => {
                void navigator.clipboard.writeText(publicUrl).then(
                  () => toast.success('Copied'),
                  () => toast.error('Copy failed'),
                );
              }}
            >
              <Copy className="h-4 w-4" /> Copy
            </button>
            <a href={publicUrl} target="_blank" rel="noreferrer" className="sd-btn sd-btn-secondary">
              <ExternalLink className="h-4 w-4" /> Open
            </a>
          </div>
        </div>
      ) : (
        <div className="sd-banner warn">
          <Globe2 className="h-5 w-5" style={{ color: 'var(--samurai-warning)' }} />
          <div className="flex-1">
            <div className="text-sm font-semibold">Not on the public internet yet</div>
            <p className="text-sm" style={{ color: 'var(--samurai-muted)' }}>
              Claim a free random *.shogun-os.ai URL — no tokens or Cloudflare needed.
            </p>
          </div>
          <button
            type="button"
            className="sd-btn sd-btn-primary"
            disabled={goLiveMutation.isPending}
            onClick={() => goLiveMutation.mutate()}
          >
            {goLiveMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Globe2 className="h-4 w-4" />}
            Get public URL
          </button>
        </div>
      )}

      <div className="sd-page-head" style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1>Company dashboard</h1>
          <p>Welcome back{user?.name ? `, ${user.name}` : ''}. One place for every department agent — activate, chat, and monitor from here.</p>
        </div>
        {inactive.length > 0 && (
          <button type="button" className="sd-btn sd-btn-secondary" onClick={() => setAdding(inactive[0].key)}>
            <Plus className="h-4 w-4" /> Add Department
          </button>
        )}
      </div>

      {active.length === 0 ? (
        <div className="sd-empty">
          <Loader2 className="h-8 w-8 animate-spin" />
          <h2>No active departments yet</h2>
          <p>Activate one from the list below, or finish onboarding.</p>
        </div>
      ) : (
        <div className="sd-grid sd-dept-grid">
          {active.map((dept) => {
            const meta = DEPARTMENT_CATALOG[dept.key] || dept;
            const Icon = ICONS[meta.icon] || Boxes;
            const color = meta.color || dept.color || '#6366f1';
            const displayName = DEPARTMENT_CATALOG[dept.key]?.name || dept.name || dept.key;
            const status = String(dept.status || dept.gateway_status || '');
            const level = status === 'active' || status === 'online' ? 'ok' : status === 'degraded' ? 'warn' : status === 'offline' || status === 'down' ? 'bad' : 'muted';
            return (
              <Link key={dept.key} to={`/department/${dept.key}?tab=dashboard`} className="sd-card interactive" style={{ textDecoration: 'none' }}>
                <div className="sd-dept-card-head">
                  <div className="sd-dept-card-id">
                    <span className="sd-dept-icon-tile" style={{ backgroundColor: color }}><Icon className="h-5 w-5" /></span>
                    <div>
                      <div className="sd-dept-card-name">{displayName}</div>
                      <div className="sd-dept-card-persona">{meta.persona}</div>
                    </div>
                  </div>
                  <span className={`sd-chip ${level}`}>{status || 'offline'}</span>
                </div>
                <p className="sd-dept-card-desc">{meta.description}</p>
                <div className="sd-dept-card-foot">
                  <span className="sd-chip muted"><LayoutDashboard className="h-3 w-3" /> Dashboard</span>
                  <span className="sd-chip muted"><MessageSquare className="h-3 w-3" /> Chat</span>
                  <span className="sd-chip muted"><Brain className="h-3 w-3" /> Brain</span>
                </div>
              </Link>
            );
          })}
        </div>
      )}

      {inactive.length > 0 && (
        <div className="mt-10">
          <h2 className="sd-sidebar-section" style={{ padding: '0 0 0.75rem' }}>Available departments</h2>
          <div className="sd-grid sd-dept-grid">
            {inactive.map((dept) => {
              const meta = DEPARTMENT_CATALOG[dept.key] || dept;
              const Icon = ICONS[meta.icon] || Boxes;
              const color = meta.color || dept.color || '#6366f1';
              const displayName = DEPARTMENT_CATALOG[dept.key]?.name || dept.name || dept.key;
              return (
                <div
                  key={dept.key}
                  className="sd-card interactive"
                  onClick={() => setAdding(adding === dept.key ? null : dept.key)}
                >
                  <div className="sd-dept-card-head">
                    <div className="sd-dept-card-id">
                      <span className="sd-dept-icon-tile" style={{ backgroundColor: color }}><Icon className="h-5 w-5" /></span>
                      <div>
                        <div className="sd-dept-card-name">{displayName}</div>
                        <div className="sd-dept-card-persona">{meta.persona}</div>
                      </div>
                    </div>
                  </div>
                  <p className="sd-dept-card-desc">{meta.description}</p>
                  {adding === dept.key && (
                    <button
                      type="button"
                      className="sd-btn sd-btn-primary w-full"
                      disabled={activateMutation.isPending}
                      onClick={(e) => { e.stopPropagation(); activateMutation.mutate(dept.key); }}
                    >
                      {activateMutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
                      Activate {displayName}
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}