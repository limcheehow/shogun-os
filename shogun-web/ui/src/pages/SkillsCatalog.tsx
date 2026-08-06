import { useMemo, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import {
  Sparkles,
  Search,
  Check,
  Loader2,
  Wrench,
  Zap,
  Download,
  DollarSign,
  Handshake,
  Users,
  Code2,
  Package,
  Terminal,
  ArrowRight,
  ShieldCheck,
  X,
} from 'lucide-react';
import toast from 'react-hot-toast';
import { skillsApi, type SkillRecommendation } from '../lib/api';
import type { Skill } from '../lib/types';

const CATEGORIES: Skill['category'][] = [
  'Finance',
  'CRM/Sales',
  'Operations',
  'Coding',
  'HR',
  'Procurement',
  'Executive',
];

export default function SkillsCatalog() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [prompt, setPrompt] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('All');
  const [installingIds, setInstallingIds] = useState<Record<string, boolean>>({});
  const [installedIds, setInstalledIds] = useState<Record<string, boolean>>({});
  const [recommendation, setRecommendation] = useState<SkillRecommendation | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  const skillsQuery = useQuery({
    queryKey: ['skills'],
    queryFn: async () => {
      const res = await skillsApi.listAll();
      return res.skills;
    },
  });

  const allSkills: Skill[] = skillsQuery.data || [];

  const handleClearSearch = () => {
    setPrompt('');
    setSearchQuery('');
    setRecommendation(null);
    setSelectedCategory('All');
    toast.success('Cleared search. Viewing all available skills.');
  };

  const handleAiSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim()) return;
    setIsAnalyzing(true);
    toast.loading('Analyzing operational requirement with AI Intent Engine...', { id: 'ai-search' });
    try {
      const rec = await skillsApi.recommend(prompt.trim());
      setRecommendation(rec);
      setSearchQuery(prompt.trim());
      toast.success('AI recommendation complete!', { id: 'ai-search' });
    } catch {
      toast.error('Failed to analyze requirement', { id: 'ai-search' });
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleInstall = async (skill: Skill) => {
    setInstallingIds((prev) => ({ ...prev, [skill.id]: true }));
    try {
      const catDept = skill.category.toLowerCase().split('/')[0];
      await skillsApi.install(skill.id, 'all');
      await queryClient.invalidateQueries({ queryKey: ['department-skills'] });
      await queryClient.invalidateQueries({ queryKey: ['skills'] });
      setInstallingIds((prev) => ({ ...prev, [skill.id]: false }));
      setInstalledIds((prev) => ({ ...prev, [skill.id]: true }));
      toast.success(`Installed skill "${skill.name}" — active in ${catDept.toUpperCase()} & department skills!`);
    } catch {
      setInstallingIds((prev) => ({ ...prev, [skill.id]: false }));
      toast.error('Failed to install skill');
    }
  };

  const handleRunShogunify = (command: string) => {
    navigator.clipboard.writeText(command);
    toast.success(`Copied Shogunify command to clipboard: ${command}`);
    navigate('/departments/finance');
  };

  const filteredSkills = useMemo(() => {
    return allSkills.filter((s) => {
      const matchesCat =
        selectedCategory === 'All' || s.category.toLowerCase() === selectedCategory.toLowerCase();

      if (!searchQuery) return matchesCat;

      // If recommendation exists, prioritize top match IDs
      if (recommendation && recommendation.recommendations.length > 0) {
        const recommendedIds = new Set(recommendation.recommendations.map((r) => r.skill_id));
        if (recommendedIds.has(s.id)) return matchesCat;
      }

      const q = searchQuery.toLowerCase();
      const matchesQuery =
        s.name.toLowerCase().includes(q) ||
        s.description.toLowerCase().includes(q) ||
        s.category.toLowerCase().includes(q);
      return matchesCat && matchesQuery;
    });
  }, [allSkills, selectedCategory, searchQuery, recommendation]);

  const getCategoryIcon = (cat: string) => {
    switch (cat.toLowerCase()) {
      case 'finance':
        return DollarSign;
      case 'crm/sales':
        return Handshake;
      case 'hr':
        return Users;
      case 'coding':
        return Code2;
      case 'procurement':
        return Package;
      default:
        return Wrench;
    }
  };

  return (
    <div className="space-y-8 p-6 max-w-7xl mx-auto">
      {/* Upper Half: Header & Intelligent AI Skill Intent Engine */}
      <div className="relative overflow-hidden rounded-2xl border border-slate-200 bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-900 p-8 text-white shadow-xl">
        <div className="relative z-10 max-w-4xl space-y-5">
          <div className="inline-flex items-center gap-2 rounded-full border border-indigo-400/30 bg-indigo-500/10 px-3 py-1 text-xs font-medium text-indigo-300 backdrop-blur-md">
            <Sparkles className="h-3.5 w-3.5 text-indigo-400" />
            AI Skills Intent Engine & Shogunify Integration
          </div>

          <h1 className="text-3xl font-bold tracking-tight sm:text-4xl text-white">
            Skills are reusable AI tools for specific jobs.
          </h1>

          <p className="text-sm text-slate-300 leading-relaxed">
            Describe your operational workflow requirement below. The AI Intent Engine will analyze your requirement, recommend matching skills, or trigger <strong>Shogunify</strong> (<code className="text-indigo-300 font-mono">/shogunify</code>) to scaffold a custom skill for your team.
          </p>

          {/* AI Intent Input Bar */}
          <form onSubmit={handleAiSearch} className="mt-6 flex flex-wrap items-center gap-2">
            <div className="relative flex-1 min-w-[280px]">
              <Sparkles className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-indigo-400" />
              <input
                type="text"
                value={prompt}
                onChange={(e) => {
                  setPrompt(e.target.value);
                  if (!e.target.value.trim()) {
                    setSearchQuery('');
                    setRecommendation(null);
                  }
                }}
                placeholder="Describe your need (e.g. 'I need automated AR dunning for overdue invoices' or 'Connect Shopee inventory')..."
                className="w-full rounded-xl border border-indigo-500/30 bg-white/10 pl-12 pr-10 py-3.5 text-sm text-white placeholder-slate-400 backdrop-blur-md transition focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-400/20"
              />
              {(prompt || searchQuery || recommendation) && (
                <button
                  type="button"
                  onClick={handleClearSearch}
                  title="Cancel search & view all skills"
                  className="absolute right-3 top-1/2 -translate-y-1/2 rounded-md p-1 text-slate-400 hover:bg-white/20 hover:text-white transition"
                >
                  <X className="h-4 w-4" />
                </button>
              )}
            </div>

            <button
              type="submit"
              disabled={isAnalyzing}
              className="flex items-center gap-2 rounded-xl bg-indigo-600 px-6 py-3.5 text-sm font-semibold text-white shadow-lg shadow-indigo-600/30 transition hover:bg-indigo-500 active:scale-[0.98] disabled:opacity-50"
            >
              {isAnalyzing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
              {isAnalyzing ? 'Analyzing...' : 'Recommend Skills'}
            </button>

            {(prompt || searchQuery || recommendation) && (
              <button
                type="button"
                onClick={handleClearSearch}
                className="flex items-center gap-1.5 rounded-xl border border-slate-700 bg-slate-800/80 px-4 py-3.5 text-sm font-semibold text-slate-300 transition hover:bg-slate-700 hover:text-white active:scale-[0.98]"
                title="Cancel search and view all skills"
              >
                <X className="h-4 w-4 text-rose-400" />
                Cancel Search
              </button>
            )}
          </form>

          {/* AI Recommendation Result & Shogunify Action Banner */}
          {recommendation && (
            <div className="mt-6 space-y-4 rounded-xl border border-indigo-500/30 bg-indigo-950/70 p-5 backdrop-blur-md">
              <div className="flex items-center gap-2 text-xs font-semibold text-indigo-300 uppercase tracking-wider">
                <ShieldCheck className="h-4 w-4 text-emerald-400" />
                AI Operational Intent Analysis
              </div>
              <p className="text-sm text-slate-200 leading-relaxed font-medium">
                {recommendation.explanation}
              </p>

              {/* Shogunify Action Card if custom skill creation is suggested */}
              {recommendation.shogunify_suggestion && (
                <div className="mt-4 flex flex-wrap items-center justify-between gap-4 rounded-xl border border-purple-500/40 bg-gradient-to-r from-purple-900/60 via-indigo-900/60 to-slate-900/90 p-4 shadow-md">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <Terminal className="h-4 w-4 text-purple-300" />
                      <span className="text-xs font-bold text-purple-200 uppercase tracking-wide">
                        Shogunify Generator Recommendation
                      </span>
                    </div>
                    <p className="text-xs text-slate-300">
                      {recommendation.shogunify_suggestion.description}
                    </p>
                    <code className="inline-block mt-1 rounded bg-black/40 px-2.5 py-1 font-mono text-xs text-purple-300 border border-purple-500/30">
                      {recommendation.shogunify_suggestion.command}
                    </code>
                  </div>

                  <button
                    type="button"
                    onClick={() => handleRunShogunify(recommendation.shogunify_suggestion!.command)}
                    className="flex items-center gap-2 rounded-lg bg-gradient-to-r from-purple-600 to-indigo-600 px-4 py-2.5 text-xs font-bold text-white shadow-lg transition hover:from-purple-500 hover:to-indigo-500 active:scale-95 shrink-0"
                  >
                    <Zap className="h-4 w-4 text-amber-300" />
                    ⚡ Run Shogunify Generator
                    <ArrowRight className="h-3.5 w-3.5" />
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Lower Half: Skills Categorization & Catalog */}
      <div className="space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 pb-4">
          <div>
            <h2 className="text-xl font-bold text-white">Available Skills Library</h2>
            <p className="text-xs text-slate-300">
              Browse and install pre-built skills for your department agents.
            </p>
          </div>

          {/* Category Filter Pills */}
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => setSelectedCategory('All')}
              className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
                selectedCategory === 'All'
                  ? 'bg-brand text-white shadow-xs'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              All Categories
            </button>
            {CATEGORIES.map((cat) => (
              <button
                key={cat}
                type="button"
                onClick={() => setSelectedCategory(cat)}
                className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
                  selectedCategory === cat
                    ? 'bg-brand text-white shadow-xs'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                {cat}
              </button>
            ))}
          </div>
        </div>

        {/* Skills Grid */}
        {skillsQuery.isLoading ? (
          <div className="flex justify-center py-16 text-slate-400">
            <Loader2 className="h-8 w-8 animate-spin" />
          </div>
        ) : filteredSkills.length === 0 ? (
          <div className="py-16 text-center text-slate-400">
            <Wrench className="mx-auto h-10 w-10 text-slate-300 mb-2" />
            <p className="text-sm font-medium">No matching skills found.</p>
            <p className="text-xs text-slate-400 mt-1">Try describing your need in the AI input box above.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {filteredSkills.map((skill) => {
              const IconComponent = getCategoryIcon(skill.category);
              const isInstalling = installingIds[skill.id];
              const isInstalled = skill.installed || installedIds[skill.id];
              const recItem = recommendation?.recommendations.find((r) => r.skill_id === skill.id);

              return (
                <div
                  key={skill.id}
                  className={`group relative flex flex-col justify-between rounded-2xl border p-6 shadow-sm transition hover:shadow-md bg-white dark:bg-slate-900 text-slate-900 dark:text-white ${
                    recItem ? 'border-emerald-400 ring-2 ring-emerald-400/20' : 'border-slate-200 dark:border-slate-800'
                  }`}
                >
                  <div className="space-y-4">
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200 transition group-hover:bg-brand group-hover:text-white">
                        <IconComponent className="h-5 w-5" />
                      </div>
                      <div className="flex items-center gap-2">
                        {recItem && (
                          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 dark:bg-emerald-950/80 px-2 py-0.5 text-[10px] font-bold text-emerald-800 dark:text-emerald-300">
                            {recItem.match_pct}% Match
                          </span>
                        )}
                        <span className="rounded-full bg-slate-100 dark:bg-slate-800 px-2.5 py-1 text-[11px] font-medium text-slate-600 dark:text-slate-300">
                          {skill.category}
                        </span>
                      </div>
                    </div>

                    <div>
                      <h3 className="text-base font-bold text-slate-900 dark:text-white group-hover:text-brand transition">
                        {skill.name}
                      </h3>
                      <p className="mt-2 text-xs text-slate-600 dark:text-slate-300 leading-relaxed line-clamp-3">
                        {skill.description}
                      </p>
                    </div>

                    {recItem && (
                      <p className="text-[11px] text-emerald-700 dark:text-emerald-300 bg-emerald-50 dark:bg-emerald-950/50 p-2 rounded-lg border border-emerald-200/60 dark:border-emerald-800/60 font-medium">
                        💡 {recItem.reason}
                      </p>
                    )}
                  </div>

                  <div className="mt-6 pt-4 border-t border-slate-100 flex items-center justify-between gap-3">
                    <span className="text-[10px] font-mono text-slate-400">
                      ID: {skill.id}
                    </span>

                    <button
                      type="button"
                      disabled={isInstalling || isInstalled}
                      onClick={() => handleInstall(skill)}
                      className={`flex items-center gap-1.5 rounded-lg px-4 py-2 text-xs font-semibold shadow-xs transition active:scale-95 ${
                        isInstalled
                          ? 'bg-emerald-50 text-emerald-700 border border-emerald-200 cursor-default'
                          : isInstalling
                          ? 'bg-indigo-50 text-indigo-700 border border-indigo-200'
                          : 'bg-brand text-white hover:bg-brand-hover'
                      }`}
                    >
                      {isInstalled ? (
                        <>
                          <Check className="h-3.5 w-3.5 text-emerald-600" />
                          Installed
                        </>
                      ) : isInstalling ? (
                        <>
                          <Loader2 className="h-3.5 w-3.5 animate-spin" />
                          Installing…
                        </>
                      ) : (
                        <>
                          <Download className="h-3.5 w-3.5" />
                          Add & Use
                        </>
                      )}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
