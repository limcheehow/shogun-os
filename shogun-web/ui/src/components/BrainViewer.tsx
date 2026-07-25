import { useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { ArrowLeft, Link2, Loader2, Search } from 'lucide-react';
import { brainApi } from '../lib/api';
import type { BrainPage } from '../lib/types';

interface BrainViewerProps {
  department: string;
}

export default function BrainViewer({ department }: BrainViewerProps) {
  const [query, setQuery] = useState('');
  const [selectedSlug, setSelectedSlug] = useState<string | null>(null);
  const [debounced, setDebounced] = useState('');

  useEffect(() => {
    const t = window.setTimeout(() => setDebounced(query.trim()), 250);
    return () => window.clearTimeout(t);
  }, [query]);

  useEffect(() => {
    setSelectedSlug(null);
    setQuery('');
  }, [department]);

  const listQuery = useQuery({
    queryKey: ['brain', department, debounced],
    queryFn: async () => {
      if (debounced) return brainApi.search(department, debounced);
      return brainApi.list(department);
    },
  });

  const pageQuery = useQuery({
    queryKey: ['brain-page', department, selectedSlug],
    queryFn: () => brainApi.get(department, selectedSlug!),
    enabled: !!selectedSlug,
  });

  const backlinksQuery = useQuery({
    queryKey: ['brain-backlinks', department, selectedSlug],
    queryFn: () => brainApi.backlinks(department, selectedSlug!),
    enabled: !!selectedSlug,
  });

  const pages = useMemo(() => listQuery.data || [], [listQuery.data]);

  if (selectedSlug) {
    const page: BrainPage | undefined = pageQuery.data;
    return (
      <div className="flex h-full min-h-[28rem] flex-col overflow-hidden rounded-xl border border-surface-border bg-white">
        <div className="flex items-center gap-3 border-b border-surface-border px-4 py-3">
          <button type="button" className="btn-ghost !px-2" onClick={() => setSelectedSlug(null)}>
            <ArrowLeft className="h-4 w-4" />
            Back
          </button>
          <div className="min-w-0 flex-1">
            <div className="truncate font-semibold text-slate-900">
              {page?.title || selectedSlug}
            </div>
            <div className="truncate text-xs text-slate-500">{selectedSlug}</div>
          </div>
        </div>

        <div className="grid flex-1 grid-cols-1 overflow-hidden lg:grid-cols-[1fr_240px]">
          <div className="overflow-y-auto p-5">
            {pageQuery.isLoading && (
              <div className="flex justify-center py-16 text-slate-400">
                <Loader2 className="h-6 w-6 animate-spin" />
              </div>
            )}
            {pageQuery.isError && (
              <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                Failed to load page.
              </div>
            )}
            {page && (
              <article className="prose-chat max-w-none">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {page.content || page.summary || '_No content_'}
                </ReactMarkdown>
              </article>
            )}
          </div>

          <aside className="border-t border-surface-border bg-surface-muted p-4 lg:border-l lg:border-t-0">
            <div className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500">
              <Link2 className="h-3.5 w-3.5" />
              Backlinks
            </div>
            {backlinksQuery.isLoading && (
              <div className="text-xs text-slate-400">Loading…</div>
            )}
            {(backlinksQuery.data || []).length === 0 && !backlinksQuery.isLoading && (
              <div className="text-xs text-slate-400">No backlinks</div>
            )}
            <ul className="space-y-1">
              {(backlinksQuery.data || []).map((b) => (
                <li key={b.slug}>
                  <button
                    type="button"
                    className="w-full rounded-md px-2 py-1.5 text-left text-sm text-slate-700 hover:bg-white"
                    onClick={() => setSelectedSlug(b.slug)}
                  >
                    <div className="font-medium">{b.title || b.slug}</div>
                    {b.link_type && (
                      <div className="text-[11px] text-slate-400">{b.link_type}</div>
                    )}
                  </button>
                </li>
              ))}
            </ul>
          </aside>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full min-h-[28rem] flex-col overflow-hidden rounded-xl border border-surface-border bg-white">
      <div className="border-b border-surface-border p-4">
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            className="input pl-9"
            placeholder="Search brain pages…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        {listQuery.isLoading && (
          <div className="flex justify-center py-16 text-slate-400">
            <Loader2 className="h-6 w-6 animate-spin" />
          </div>
        )}
        {listQuery.isError && (
          <div className="m-4 rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            Failed to load brain pages.
          </div>
        )}
        {!listQuery.isLoading && pages.length === 0 && (
          <div className="m-4 rounded-lg border border-dashed border-slate-200 bg-slate-50 px-4 py-10 text-center text-sm text-slate-500">
            No pages found{debounced ? ` for “${debounced}”` : ''}.
          </div>
        )}
        <ul className="divide-y divide-surface-border">
          {pages.map((p) => (
            <li key={p.slug}>
              <button
                type="button"
                className="w-full px-4 py-3 text-left hover:bg-surface-muted"
                onClick={() => setSelectedSlug(p.slug)}
              >
                <div className="font-medium text-slate-900">{p.title || p.slug}</div>
                <div className="mt-0.5 flex flex-wrap items-center gap-2 text-xs text-slate-500">
                  <span className="truncate">{p.slug}</span>
                  {p.type && (
                    <span className="rounded-full bg-slate-100 px-2 py-0.5 text-slate-600">
                      {p.type}
                    </span>
                  )}
                  {p.updated_at && (
                    <span>{new Date(p.updated_at).toLocaleString()}</span>
                  )}
                </div>
                {p.summary && (
                  <p className="mt-1 line-clamp-2 text-sm text-slate-600">{p.summary}</p>
                )}
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
