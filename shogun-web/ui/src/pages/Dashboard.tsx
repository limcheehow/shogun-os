import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Loader2, Plus } from 'lucide-react';
import toast from 'react-hot-toast';
import DepartmentCard from '../components/DepartmentCard';
import { departmentsApi } from '../lib/api';
import { useAuth } from '../lib/auth';
import {
  DEPARTMENT_CATALOG,
  DEPARTMENT_KEYS,
  type Department,
  type DepartmentKey,
} from '../lib/types';

function mergeCatalog(remote: Department[] | undefined): Department[] {
  const map = new Map((remote || []).map((d) => [d.key, d]));
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
      active: r?.active ?? false,
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

  return (
    <div className="mx-auto max-w-6xl">
      <div className="mb-8 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900">
            Company dashboard
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            Welcome back{user?.name ? `, ${user.name}` : ''}. One place for every
            department agent — activate, chat, and monitor from here.
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

      {deptsQuery.isLoading && (
        <div className="flex justify-center py-20 text-slate-400">
          <Loader2 className="h-8 w-8 animate-spin" />
        </div>
      )}

      {deptsQuery.isError && (
        <div className="mb-6 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          Could not load departments from the API. Showing catalog defaults.
        </div>
      )}

      {!deptsQuery.isLoading && (
        <>
          <section className="mb-10">
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">
              Active ({active.length})
            </h2>
            {active.length === 0 ? (
              <div className="rounded-xl border border-dashed border-slate-300 bg-white px-6 py-12 text-center text-sm text-slate-500">
                No active departments yet. Add one to get started.
              </div>
            ) : (
              <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                {active.map((d) => (
                  <DepartmentCard key={d.key} department={d} />
                ))}
              </div>
            )}
          </section>

          {inactive.length > 0 && (
            <section>
              <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">
                Available
              </h2>
              <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                {inactive.map((d) => (
                  <DepartmentCard
                    key={d.key}
                    department={d}
                    onAdd={() => {
                      setAdding(d.key);
                      activateMutation.mutate(d.key);
                    }}
                  />
                ))}
              </div>
            </section>
          )}
        </>
      )}

      {activateMutation.isPending && adding && (
        <div className="fixed bottom-4 right-4 flex items-center gap-2 rounded-lg bg-slate-900 px-4 py-2 text-sm text-white shadow-lg">
          <Loader2 className="h-4 w-4 animate-spin" />
          Activating {DEPARTMENT_CATALOG[adding].name}…
        </div>
      )}
    </div>
  );
}
