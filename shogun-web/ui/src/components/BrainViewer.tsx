import { useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  ArrowLeft,
  ChevronDown,
  ChevronRight,
  File,
  FileCode,
  FileText,
  Folder,
  FolderOpen,
  Loader2,
  Search,
} from 'lucide-react';
import { brainApi } from '../lib/api';

interface BrainViewerProps {
  department: string;
}

interface FileItem {
  name: string;
  rel_path?: string;
  full_path?: string;
  folder?: string;
  slug?: string;
  title?: string;
  ext?: string;
  category?: string;
}

export default function BrainViewer({ department }: BrainViewerProps) {
  const [query, setQuery] = useState('');
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [openFolders, setOpenFolders] = useState<Record<string, boolean>>({});

  useEffect(() => {
    setSelectedPath(null);
    setQuery('');
  }, [department]);

  const listQuery = useQuery({
    queryKey: ['brain-tree', department],
    queryFn: () => brainApi.list(department),
  });

  const contentQuery = useQuery({
    queryKey: ['brain-file-content', department, selectedPath],
    queryFn: () => brainApi.getFileContent(department, selectedPath!),
    enabled: !!selectedPath,
  });

  const { files } = useMemo(() => {
    const rawFiles: FileItem[] = listQuery.data?.files || [];
    const filteredFiles = rawFiles.filter((f) => {
      if (!query.trim()) return true;
      const q = query.toLowerCase();
      return (
        f.name.toLowerCase().includes(q) ||
        (f.rel_path && f.rel_path.toLowerCase().includes(q)) ||
        (f.title && f.title.toLowerCase().includes(q))
      );
    });

    return { files: filteredFiles };
  }, [listQuery.data, query]);

  // Group files by folder
  const groupedFiles = useMemo(() => {
    const groups: Record<string, FileItem[]> = { Root: [] };
    files.forEach((file) => {
      const folderKey = file.folder ? file.folder : 'Root';
      if (!groups[folderKey]) {
        groups[folderKey] = [];
      }
      groups[folderKey].push(file);
    });
    return groups;
  }, [files]);

  const toggleFolder = (folderName: string) => {
    setOpenFolders((prev) => ({
      ...prev,
      [folderName]: prev[folderName] === undefined ? false : !prev[folderName],
    }));
  };

  const getFileIcon = (ext?: string) => {
    if (!ext) return File;
    if (['.md', '.txt', '.doc', '.docx'].includes(ext)) return FileText;
    if (['.yaml', '.yml', '.json', '.js', '.ts', '.py', '.sh', '.bat'].includes(ext)) return FileCode;
    return File;
  };

  const selectedFile = useMemo(() => {
    if (!selectedPath) return null;
    return files.find(
      (f) => f.full_path === selectedPath || f.rel_path === selectedPath || f.slug === selectedPath,
    );
  }, [files, selectedPath]);

  return (
    <div className="flex h-full min-h-[32rem] flex-col overflow-hidden rounded-xl border border-surface-border bg-white shadow-sm">
      {/* Header bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-surface-border p-4 bg-slate-50/50">
        <div className="flex items-center gap-2">
          {selectedPath && (
            <button
              type="button"
              className="btn-ghost !px-2 mr-1"
              onClick={() => setSelectedPath(null)}
            >
              <ArrowLeft className="h-4 w-4" />
              Back
            </button>
          )}
          <div>
            <h2 className="text-base font-semibold text-slate-900">
              Department Brain Explorer
            </h2>
            <p className="text-xs text-slate-500">
              {files.length} {files.length === 1 ? 'file' : 'files'} available
            </p>
          </div>
        </div>

        <div className="relative min-w-[220px]">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            className="input pl-9 text-xs py-1.5"
            placeholder="Search folders and files…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
      </div>

      <div className="grid flex-1 grid-cols-1 overflow-hidden lg:grid-cols-[300px_1fr]">
        {/* Left pane: File & Folder Tree */}
        <div className="border-r border-surface-border overflow-y-auto p-3 bg-slate-50/30">
          {listQuery.isLoading && (
            <div className="flex justify-center py-12 text-slate-400">
              <Loader2 className="h-5 w-5 animate-spin" />
            </div>
          )}

          {!listQuery.isLoading && files.length === 0 && (
            <div className="py-8 px-4 text-center text-xs text-slate-400">
              No files found in this department.
            </div>
          )}

          {!listQuery.isLoading && files.length > 0 && (
            <div className="space-y-3">
              {Object.entries(groupedFiles).map(([folderName, folderFiles]) => {
                if (folderFiles.length === 0) return null;
                const isOpen = openFolders[folderName] !== false;

                return (
                  <div key={folderName} className="space-y-1">
                    {folderName !== 'Root' && (
                      <button
                        type="button"
                        className="flex w-full items-center gap-1.5 rounded-md px-2 py-1 text-left text-xs font-semibold text-slate-700 hover:bg-slate-100"
                        onClick={() => toggleFolder(folderName)}
                      >
                        {isOpen ? (
                          <>
                            <ChevronDown className="h-3.5 w-3.5 text-slate-400" />
                            <FolderOpen className="h-3.5 w-3.5 text-amber-500" />
                          </>
                        ) : (
                          <>
                            <ChevronRight className="h-3.5 w-3.5 text-slate-400" />
                            <Folder className="h-3.5 w-3.5 text-amber-500" />
                          </>
                        )}
                        <span className="truncate">{folderName}</span>
                        <span className="ml-auto text-[10px] text-slate-400">
                          {folderFiles.length}
                        </span>
                      </button>
                    )}

                    {(folderName === 'Root' || isOpen) && (
                      <div className={folderName !== 'Root' ? 'pl-4 space-y-0.5' : 'space-y-0.5'}>
                        {folderFiles.map((file) => {
                          const fileKey = file.full_path || file.rel_path || file.slug || file.name;
                          const isSelected = selectedPath === fileKey;
                          const IconComp = getFileIcon(file.ext);

                          return (
                            <button
                              key={fileKey}
                              type="button"
                              onClick={() => setSelectedPath(fileKey)}
                              className={`flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-left text-xs transition ${
                                isSelected
                                  ? 'bg-brand/10 font-medium text-brand ring-1 ring-brand/30'
                                  : 'text-slate-700 hover:bg-slate-100'
                              }`}
                            >
                              <IconComp className="h-3.5 w-3.5 shrink-0 text-slate-500" />
                              <span className="flex-1 truncate">{file.name}</span>
                              {file.ext && (
                                <span className="rounded bg-slate-200/60 px-1 py-0.5 text-[9px] font-mono text-slate-600 uppercase">
                                  {file.ext.replace('.', '')}
                                </span>
                              )}
                            </button>
                          );
                        })}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Right pane: Preview Content */}
        <div className="overflow-y-auto p-6 bg-white">
          {!selectedPath && (
            <div className="flex h-full flex-col items-center justify-center text-center text-slate-400 py-16">
              <FileText className="h-12 w-12 stroke-[1.5] text-slate-300 mb-3" />
              <p className="text-sm font-medium text-slate-600">Select a file to preview</p>
              <p className="text-xs text-slate-400 mt-1 max-w-xs">
                Click any document or configuration file on the left to view its complete contents.
              </p>
            </div>
          )}

          {selectedPath && (
            <div>
              <div className="mb-4 pb-3 border-b border-surface-border flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-semibold text-slate-900">
                    {selectedFile?.name || selectedPath.split('/').pop()}
                  </h3>
                  <p className="text-xs text-slate-400 font-mono mt-0.5">{selectedPath}</p>
                </div>
              </div>

              {contentQuery.isLoading && (
                <div className="flex justify-center py-16 text-slate-400">
                  <Loader2 className="h-6 w-6 animate-spin" />
                </div>
              )}

              {contentQuery.isError && (
                <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                  Failed to load file preview.
                </div>
              )}

              {contentQuery.data && (
                <div>
                  {['.md', '.markdown'].includes(contentQuery.data.ext) ? (
                    <article className="prose-chat max-w-none">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {contentQuery.data.content || '_File is empty_'}
                      </ReactMarkdown>
                    </article>
                  ) : (
                    <pre className="rounded-xl border border-slate-200 bg-slate-900 p-4 font-mono text-xs text-slate-100 overflow-x-auto">
                      <code>{contentQuery.data.content || '# Empty file'}</code>
                    </pre>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
