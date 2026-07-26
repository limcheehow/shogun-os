import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Copy, ExternalLink, Globe2, Loader2, Plus } from 'lucide-react';
import toast from 'react-hot-toast';
import DepartmentCard from '../components/DepartmentCard';
import { departmentsApi, onboardingApi } from '../lib/api';
import { useAuth } from '../lib/auth';
import {
  DEPARTMENT_CATALOG,
  DEPARTMENT_KEYS,
  type Department,
  type DepartmentKey,
} from '../lib/types';

function mergeCatalog(remote: Department[] | undefined): Department[] {
  const map = new Map((remote || []).map((d) => [d.key || (d as { name?: string }).name, d]));
  return DEPARTMENT_KEYS.map((key) => {
    const base = DEPARTMENT_CATALOG[key];
    const r = map.get(key);
    return {
      ...base,
      ...r,
      key,
      name: r?.name || base.name,
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
        <div className="mb-6 flex flex-col gap-3 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-start gap-3">
            <Globe2 className="mt-0.5 h-5 w-5 text-emerald-600" />
            <div>
              <div className="text-sm font-semibold text-emerald-900">Public company URL</div>
              <a
                href={publicUrl}
                target="_blank"
                rel="noreferrer"
                className="break-all text-sm font-medium text-emerald-700 hover:underline"
              >
                {publicUrl}
              </a>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className="btn-secondary"
              onClick={() => {
                void navigator.clipboard.writeText(publicUrl).then(
                  () => toast.success('Copied'),
                  () => toast.error('Copy failed'),
                );
              }}
            >
              <Copy className="h-4 w-4" />
              Copy
            </button>
            <a href={publicUrl} target="_blank" rel="noreferrer" className="btn-secondary">
              <ExternalLink className="h-4 w-4" />
              Open
            </a>
          </div>
        </div>
      ) : (
        <div className="mb-6 flex flex-col gap-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="text-sm font-semibold text-amber-900">Not on the public internet yet</div>
            <p className="text-sm text-amber-800">
              Claim a free random *.shogun-os.ai URL - no tokens or Cloudflare needed.
            </p>
          </div>
          <button
            type="button"
            className="btn-primary"
            disabled={goLiveMutation.isPending}
            onClick={() => goLiveMutation.mutate()}
          >
            {goLiveMutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Globe2 className="h-4 w-4" />
            )}
            Get public URL
          </button>
        </div>
      )}

      <div className="mb-8 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900">
            Company dashboard
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            Welcome back{user?.name ? `, ${user.name}` : ''}. One place for every
            department agent - activate, chat, and monitor from here.
          </p>
        </div>
        {inactive.length > 0 && (
          <button
            type="button"
            className="btn-secondary"
            onClick={() => setAdding(inactive[0].key)}
          >
            <Plus className="h-4 w-4" />
            Add Department
          </button>
        )}
      </div>

      {active.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 px-6 py-16 text-center">
          <Loader2 className="mx-auto h-8 w-8 animate-spin text-slate-400" />
          <p className="mt-4 text-sm text-slate-500">No active departments yet.</p>
          <p className="text-xs text-slate-400">
            Activate one from the list below, or finish onboarding.
          </p>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {active.map((dept) => (
            <DepartmentCard key={dept.key} department={dept} />
          ))}
        </div>
      )}

      {inactive.length > 0 && (
        <div className="mt-10">
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-400">
            Available departments
          </h2>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {inactive.map((dept) => (
              <div
                key={dept.key}
                className="card cursor-pointer p-4 transition hover:border-slate-300"
                onClick={() => {
                  if (adding === dept.key) {
                    setAdding(null);
                  } else {
                    setAdding(dept.key);
                  }
                }}
              >
                <div className="flex items-center gap-2">
                  <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: dept.color }} />
                  <span className="font-medium text-slate-900">{dept.name}</span>
                  <span className="text-xs text-slate-400">{dept.persona}</span>
                </div>
                <p className="mt-1 text-sm text-slate-600">{dept.description}</p>
                {adding === dept.key && (
                  <button
                    type="button"
                    className="btn-primary mt-3 w-full"
                    disabled={activateMutation.isPending}
                    onClick={(e) => {
                      e.stopPropagation();
                      activateMutation.mutate(dept.key);
                    }}
                  >
                    {activateMutation.isPending ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : null}
                    Activate {dept.name}
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}