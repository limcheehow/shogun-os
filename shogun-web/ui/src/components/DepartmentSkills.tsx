import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Wrench, Trash2, Loader2, Zap, ShieldCheck } from 'lucide-react';
import toast from 'react-hot-toast';
import { skillsApi } from '../lib/api';
import type { Skill } from '../lib/types';

interface DepartmentSkillsProps {
  department: string;
}

export default function DepartmentSkills({ department }: DepartmentSkillsProps) {
  const [deletingIds, setDeletingIds] = useState<Record<string, boolean>>({});

  const skillsQuery = useQuery({
    queryKey: ['department-skills', department],
    queryFn: async () => {
      const res = await skillsApi.listDepartment(department);
      return res.skills;
    },
  });

  const skills: Skill[] = skillsQuery.data || [];

  const handleDelete = async (skill: Skill) => {
    setDeletingIds((prev) => ({ ...prev, [skill.id]: true }));
    try {
      await skillsApi.deleteDepartmentSkill(department, skill.id);
      toast.success(`Removed skill "${skill.name}" from ${department}`);
      skillsQuery.refetch();
    } catch {
      toast.error('Failed to remove skill');
    } finally {
      setDeletingIds((prev) => ({ ...prev, [skill.id]: false }));
    }
  };

  return (
    <div className="space-y-6 p-6">
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-700/50 pb-4">
        <div>
          <h2 className="text-xl font-bold text-white capitalize">
            {department} Downloaded Skills
          </h2>
          <p className="text-xs text-slate-300 mt-1">
            Active specialized AI tools and task automation packages enabled for the {department} agent.
          </p>
        </div>
        <div className="flex items-center gap-2 rounded-lg bg-indigo-500/10 px-3 py-1.5 text-xs font-semibold text-indigo-300 border border-indigo-500/30">
          <Wrench className="h-4 w-4 text-indigo-400" />
          {skills.length} Installed Skills
        </div>
      </div>

      {skillsQuery.isLoading ? (
        <div className="flex justify-center py-16 text-slate-400">
          <Loader2 className="h-8 w-8 animate-spin" />
        </div>
      ) : skills.length === 0 ? (
        <div className="py-16 text-center text-slate-500 bg-white rounded-xl border border-dashed border-slate-300">
          <Wrench className="mx-auto h-10 w-10 text-slate-300 mb-2" />
          <p className="text-sm font-medium">No installed skills for {department}.</p>
          <p className="text-xs text-slate-400 mt-1">
            Visit the global <strong>Skills</strong> tab on the left sidebar to browse and add skills.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-5 md:grid-cols-2 lg:grid-cols-3">
          {skills.map((skill) => {
            const isDeleting = deletingIds[skill.id];

            return (
              <div
                key={skill.id}
                className="flex flex-col justify-between rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-slate-900 dark:text-white p-5 shadow-sm transition hover:border-slate-300 dark:hover:border-slate-700"
              >
                <div className="space-y-3">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-2.5">
                      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-50 dark:bg-indigo-900/40 text-indigo-600 dark:text-indigo-300">
                        <Wrench className="h-5 w-5" />
                      </div>
                      <div>
                        <h3 className="text-sm font-bold text-slate-900 dark:text-white">{skill.name}</h3>
                        <span className="text-[11px] font-medium text-slate-400">
                          {skill.author || 'Installed Skill'}
                        </span>
                      </div>
                    </div>
                    {skill.version && (
                      <span className="rounded bg-slate-100 dark:bg-slate-800 px-2 py-0.5 text-[10px] font-mono font-medium text-slate-600 dark:text-slate-300">
                        {skill.version}
                      </span>
                    )}
                  </div>

                  <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed">{skill.description}</p>
                </div>

                <div className="mt-6 flex items-center justify-between border-t border-slate-100 pt-4">
                  <div className="flex items-center gap-1 text-[11px] font-medium text-emerald-600">
                    <ShieldCheck className="h-3.5 w-3.5" />
                    Active on {department}
                  </div>

                  <button
                    type="button"
                    onClick={() => handleDelete(skill)}
                    disabled={isDeleting}
                    className="flex items-center gap-1.5 rounded-lg border border-rose-200 bg-rose-50 px-3 py-1.5 text-xs font-semibold text-rose-700 transition hover:bg-rose-100 active:scale-95 disabled:opacity-50"
                  >
                    {isDeleting ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <Trash2 className="h-3.5 w-3.5" />
                    )}
                    Delete
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
