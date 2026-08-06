import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Download,
  File,
  FileImage,
  FileText,
  Loader2,
  X,
} from 'lucide-react';
import { docsApi, getToken } from '../lib/api';
import type { DocumentArtifact } from '../lib/types';

interface DocsViewerProps {
  department: string;
}

function formatBytes(n?: number) {
  if (n == null || Number.isNaN(n)) return '';
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

function fileIcon(mime?: string) {
  if (mime?.startsWith('image/')) return FileImage;
  if (mime?.includes('pdf') || mime?.includes('text') || mime?.includes('markdown'))
    return FileText;
  return File;
}

export default function DocsViewer({ department }: DocsViewerProps) {
  const [selected, setSelected] = useState<DocumentArtifact | null>(null);

  const listQuery = useQuery({
    queryKey: ['docs', department],
    queryFn: () => docsApi.list(department),
  });

  const docs = listQuery.data || [];

  const handleDownload = async (doc: DocumentArtifact) => {
    const url = doc.url || docsApi.downloadUrl(department, doc.id);
    const token = getToken();
    try {
      const res = await fetch(url, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok) throw new Error('Download failed');
      const blob = await res.blob();
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = doc.name || 'download';
      a.click();
      URL.revokeObjectURL(a.href);
    } catch {
      window.open(url, '_blank', 'noopener,noreferrer');
    }
  };

  const isImage = selected?.mime_type?.startsWith('image/');
  const isText =
    !!selected?.mime_type &&
    (selected.mime_type.includes('text') ||
      selected.mime_type.includes('json') ||
      selected.mime_type.includes('markdown'));

  const previewQuery = useQuery({
    queryKey: ['doc-preview', department, selected?.id],
    enabled: !!selected && isText,
    queryFn: async () => {
      const url =
        selected!.preview_url ||
        selected!.url ||
        docsApi.downloadUrl(department, selected!.id);
      const token = getToken();
      const res = await fetch(url, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok) throw new Error('Preview failed');
      return res.text();
    },
  });

  return (
    <div className="flex h-full min-h-[28rem] flex-col overflow-hidden rounded-xl border border-surface-border bg-white">
      <div className="flex items-center justify-between border-b border-surface-border px-4 py-3">
        <h3 className="font-semibold text-slate-900">Department Documents</h3>
        <span className="text-xs text-slate-500">{docs.length} items</span>
      </div>

      <div className="grid flex-1 grid-cols-1 overflow-hidden lg:grid-cols-[1fr_1.1fr]">
        <div className="overflow-y-auto border-b border-surface-border lg:border-b-0 lg:border-r">
          {listQuery.isLoading && (
            <div className="flex justify-center py-16 text-slate-400">
              <Loader2 className="h-6 w-6 animate-spin" />
            </div>
          )}
          {listQuery.isError && (
            <div className="m-4 rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
              Failed to load documents.
            </div>
          )}
          {!listQuery.isLoading && docs.length === 0 && (
            <div className="m-4 rounded-lg border border-dashed border-slate-200 bg-slate-50 px-4 py-10 text-center text-sm text-slate-500">
              No documents yet.
            </div>
          )}
          <ul className="divide-y divide-surface-border">
            {docs.map((doc, idx) => {
              const Icon = fileIcon(doc.mime_type);
              const active = selected?.id === doc.id;
              return (
                <li key={doc.id || `${doc.name}-${idx}`}>
                  <button
                    type="button"
                    className={`flex w-full items-start gap-3 px-4 py-3 text-left hover:bg-surface-muted ${
                      active ? 'bg-brand-light/60' : ''
                    }`}
                    onClick={() => setSelected(doc)}
                  >
                    <div className="mt-0.5 rounded-lg bg-slate-100 p-2 text-slate-600">
                      <Icon className="h-4 w-4" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="truncate font-medium text-slate-900">{doc.name}</div>
                      <div className="mt-0.5 flex flex-wrap gap-2 text-xs text-slate-500">
                        {doc.mime_type && <span>{doc.mime_type}</span>}
                        {doc.size_bytes != null && <span>{formatBytes(doc.size_bytes)}</span>}
                        {doc.updated_at && (
                          <span>{new Date(doc.updated_at).toLocaleDateString()}</span>
                        )}
                      </div>
                      {doc.description && (
                        <p className="mt-1 line-clamp-2 text-sm text-slate-600">
                          {doc.description}
                        </p>
                      )}
                    </div>
                  </button>
                </li>
              );
            })}
          </ul>
        </div>

        <div className="flex flex-col overflow-hidden bg-surface-muted">
          {!selected && (
            <div className="flex flex-1 items-center justify-center p-8 text-sm text-slate-500">
              Select a document to preview
            </div>
          )}
          {selected && (
            <>
              <div className="flex items-center gap-2 border-b border-surface-border bg-white px-4 py-3">
                <div className="min-w-0 flex-1">
                  <div className="truncate font-semibold text-slate-900">{selected.name}</div>
                  <div className="text-xs text-slate-500">
                    {[selected.mime_type, formatBytes(selected.size_bytes)]
                      .filter(Boolean)
                      .join(' · ')}
                  </div>
                </div>
                <button
                  type="button"
                  className="btn-secondary !py-1.5"
                  onClick={() => void handleDownload(selected)}
                >
                  <Download className="h-4 w-4" />
                  Download
                </button>
                <button
                  type="button"
                  className="btn-ghost !px-2"
                  onClick={() => setSelected(null)}
                  aria-label="Close preview"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
              <div className="flex-1 overflow-auto p-4">
                {isImage && (
                  <img
                    src={
                      selected.preview_url ||
                      selected.url ||
                      docsApi.downloadUrl(department, selected.id)
                    }
                    alt={selected.name}
                    className="mx-auto max-h-full max-w-full rounded-lg border border-surface-border bg-white object-contain shadow-sm"
                  />
                )}
                {isText && (
                  <div className="rounded-lg border border-surface-border bg-white p-4">
                    {previewQuery.isLoading && (
                      <div className="flex justify-center py-10 text-slate-400">
                        <Loader2 className="h-5 w-5 animate-spin" />
                      </div>
                    )}
                    {previewQuery.isError && (
                      <div className="text-sm text-rose-600">Could not load preview.</div>
                    )}
                    {previewQuery.data && (
                      <pre className="whitespace-pre-wrap break-words text-xs text-slate-700">
                        {previewQuery.data}
                      </pre>
                    )}
                  </div>
                )}
                {!isImage && !isText && (
                  <div className="flex h-full flex-col items-center justify-center gap-3 rounded-lg border border-dashed border-slate-300 bg-white p-8 text-center">
                    <File className="h-10 w-10 text-slate-300" />
                    <p className="text-sm text-slate-600">
                      Preview not available for this file type.
                    </p>
                    <button
                      type="button"
                      className="btn-primary"
                      onClick={() => void handleDownload(selected)}
                    >
                      <Download className="h-4 w-4" />
                      Download file
                    </button>
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
