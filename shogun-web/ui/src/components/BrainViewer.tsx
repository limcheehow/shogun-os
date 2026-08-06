import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
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
  Copy,
  Check,
  Eye,
  Code,
  ExternalLink,
  Table,
  BookOpen,
  Clock,
  FileCheck,
} from "lucide-react";
import toast from "react-hot-toast";
import { brainApi } from "../lib/api";

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
  snippet?: string;
}

function HighlightedText({
  text,
  highlight,
}: {
  text: string;
  highlight: string;
}) {
  if (!highlight || !highlight.trim()) return <>{text}</>;

  const escaped = highlight.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const regex = new RegExp(`(${escaped})`, "gi");
  const parts = text.split(regex);

  return (
    <>
      {parts.map((part, i) =>
        regex.test(part) ? (
          <mark
            key={i}
            className="bg-amber-300 text-slate-950 font-semibold px-1 py-0.5 rounded shadow-xs"
          >
            {part}
          </mark>
        ) : (
          part
        ),
      )}
    </>
  );
}

function renderHighlightedChildren(
  children: React.ReactNode,
  highlight: string,
) {
  if (!highlight.trim()) return children;
  if (typeof children === "string") {
    return <HighlightedText text={children} highlight={highlight} />;
  }
  if (Array.isArray(children)) {
    return (
      <>
        {children.map((child, idx) =>
          typeof child === "string" ? (
            <HighlightedText key={idx} text={child} highlight={highlight} />
          ) : (
            child
          ),
        )}
      </>
    );
  }
  return children;
}

function MarkdownDocumentViewer({
  content,
  filename,
  searchQuery,
}: {
  content: string;
  filename: string;
  searchQuery: string;
}) {
  const wordCount = useMemo(() => {
    return content.trim().split(/\s+/).filter(Boolean).length;
  }, [content]);

  const readTimeMinutes = Math.max(1, Math.ceil(wordCount / 200));

  const components = useMemo(() => {
    return {
      h1: ({ children }: { children?: React.ReactNode }) => (
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white border-b border-slate-200 dark:border-slate-800 pb-2.5 mb-4 mt-6 flex items-center gap-2">
          <span className="h-6 w-1.5 rounded-full bg-indigo-500 inline-block"></span>
          <span>{renderHighlightedChildren(children, searchQuery)}</span>
        </h1>
      ),
      h2: ({ children }: { children?: React.ReactNode }) => (
        <h2 className="text-lg font-bold text-slate-900 dark:text-white border-b border-slate-100 dark:border-slate-800 pb-2 mb-3 mt-6 flex items-center gap-2">
          <span className="h-4 w-1 rounded-full bg-indigo-400 inline-block"></span>
          <span>{renderHighlightedChildren(children, searchQuery)}</span>
        </h2>
      ),
      h3: ({ children }: { children?: React.ReactNode }) => (
        <h3 className="text-base font-semibold text-slate-800 dark:text-slate-100 mb-2 mt-4">
          {renderHighlightedChildren(children, searchQuery)}
        </h3>
      ),
      p: ({ children }: { children?: React.ReactNode }) => (
        <p className="text-sm text-slate-700 dark:text-slate-200 leading-relaxed mb-4">
          {renderHighlightedChildren(children, searchQuery)}
        </p>
      ),
      ul: ({ children }: { children?: React.ReactNode }) => (
        <ul className="my-3 space-y-1.5 pl-5 list-disc text-sm text-slate-700 dark:text-slate-200 leading-relaxed marker:text-indigo-400">
          {children}
        </ul>
      ),
      ol: ({ children }: { children?: React.ReactNode }) => (
        <ol className="my-3 space-y-1.5 pl-5 list-decimal text-sm text-slate-700 dark:text-slate-200 leading-relaxed marker:font-semibold marker:text-indigo-400">
          {children}
        </ol>
      ),
      li: ({ children }: { children?: React.ReactNode }) => (
        <li className="pl-1">
          {renderHighlightedChildren(children, searchQuery)}
        </li>
      ),
      blockquote: ({ children }: { children?: React.ReactNode }) => (
        <blockquote className="my-4 border-l-4 border-indigo-500 bg-indigo-50/60 dark:bg-indigo-950/60 p-4 rounded-r-xl text-xs sm:text-sm text-indigo-950 dark:text-indigo-200 italic shadow-xs">
          {renderHighlightedChildren(children, searchQuery)}
        </blockquote>
      ),
      code: ({
        inline,
        className,
        children,
        ...props
      }: {
        inline?: boolean;
        className?: string;
        children?: React.ReactNode;
      }) => {
        if (inline) {
          return (
            <code className="rounded-md bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 font-mono text-xs text-indigo-700 dark:text-indigo-300 border border-slate-200/80 dark:border-slate-700 font-medium">
              {renderHighlightedChildren(children, searchQuery)}
            </code>
          );
        }
        return (
          <code className={className} {...props}>
            {renderHighlightedChildren(children, searchQuery)}
          </code>
        );
      },
      pre: ({ children }: { children?: React.ReactNode }) => (
        <pre className="my-4 overflow-x-auto rounded-xl bg-slate-900 p-4 font-mono text-xs text-slate-100 shadow-md border border-slate-800 leading-relaxed">
          {children}
        </pre>
      ),
      table: ({ children }: { children?: React.ReactNode }) => (
        <div className="my-4 overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-xs">
          <table className="w-full text-left text-xs border-collapse">
            {children}
          </table>
        </div>
      ),
      th: ({ children }: { children?: React.ReactNode }) => (
        <th className="bg-slate-100/90 dark:bg-slate-800 text-slate-900 dark:text-white font-bold px-4 py-2.5 border-b border-r border-slate-200 dark:border-slate-700 last:border-r-0 whitespace-nowrap">
          {renderHighlightedChildren(children, searchQuery)}
        </th>
      ),
      td: ({ children }: { children?: React.ReactNode }) => (
        <td className="px-4 py-2.5 text-slate-700 dark:text-slate-200 border-b border-r border-slate-100 dark:border-slate-800 last:border-r-0 hover:bg-slate-50/60 dark:hover:bg-slate-800/60">
          {renderHighlightedChildren(children, searchQuery)}
        </td>
      ),
      hr: () => (
        <hr className="my-6 border-t-2 border-slate-200/70 dark:border-slate-800" />
      ),
      a: ({
        href,
        children,
      }: {
        href?: string;
        children?: React.ReactNode;
      }) => (
        <a
          href={href}
          target="_blank"
          rel="noreferrer"
          className="text-indigo-600 dark:text-indigo-400 font-medium hover:underline underline-offset-2"
        >
          {renderHighlightedChildren(children, searchQuery)}
        </a>
      ),
      strong: ({ children }: { children?: React.ReactNode }) => (
        <strong className="font-semibold text-slate-900 dark:text-white">
          {renderHighlightedChildren(children, searchQuery)}
        </strong>
      ),
      em: ({ children }: { children?: React.ReactNode }) => (
        <em className="italic text-slate-800 dark:text-slate-200">
          {renderHighlightedChildren(children, searchQuery)}
        </em>
      ),
    };
  }, [searchQuery]);

  return (
    <div className="space-y-6">
      {/* Tidy Metadata Banner */}
      <div className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-indigo-100 dark:border-indigo-900/60 bg-gradient-to-r from-indigo-50/80 via-slate-50 to-white dark:from-slate-900 dark:via-slate-800 dark:to-slate-900 p-4 shadow-xs text-slate-900 dark:text-white">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-600 text-white shadow-sm">
            <BookOpen className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="inline-flex items-center gap-1 rounded bg-indigo-100 dark:bg-indigo-950 px-2 py-0.5 text-[10px] font-semibold text-indigo-700 dark:text-indigo-300 uppercase">
                Markdown
              </span>
              <span className="text-xs font-semibold text-slate-900 dark:text-white">
                {filename}
              </span>
            </div>
            <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
              Formatted Department Document
            </p>
          </div>
        </div>

        <div className="flex items-center gap-4 text-xs text-slate-500 dark:text-slate-400 font-medium">
          <div className="flex items-center gap-1.5">
            <FileCheck className="h-3.5 w-3.5 text-indigo-500" />
            {wordCount} words
          </div>
          <div className="flex items-center gap-1.5">
            <Clock className="h-3.5 w-3.5 text-indigo-500" />~{readTimeMinutes}{" "}
            min read
          </div>
        </div>
      </div>

      {/* Main Beautiful Document Body */}
      <article className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 p-6 sm:p-8 shadow-sm">
        <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
          {content || "_File is empty_"}
        </ReactMarkdown>
      </article>
    </div>
  );
}

function CsvViewer({
  content,
  searchQuery,
}: {
  content: string;
  searchQuery: string;
}) {
  const [csvFilter, setCsvFilter] = useState("");
  const rows = useMemo(() => {
    return content
      .split("\n")
      .map((r) => r.trim())
      .filter(Boolean)
      .map((r) =>
        r.split(",").map((cell) => cell.trim().replace(/^["']|["']$/g, "")),
      );
  }, [content]);

  if (rows.length === 0) {
    return (
      <div className="text-xs text-slate-400 py-8 text-center">
        Empty CSV file
      </div>
    );
  }

  const headers = rows[0];
  const dataRows = rows.slice(1);
  const activeQuery = csvFilter || searchQuery;

  const filteredData = dataRows.filter((r) =>
    !activeQuery
      ? true
      : r.some((cell) =>
          cell.toLowerCase().includes(activeQuery.toLowerCase()),
        ),
  );

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-xs font-semibold text-slate-700">
          <Table className="h-4 w-4 text-emerald-600" />
          Data Table ({dataRows.length} rows)
        </div>
        <input
          type="text"
          value={csvFilter}
          onChange={(e) => setCsvFilter(e.target.value)}
          placeholder="Filter rows..."
          className="rounded-lg border border-slate-200 px-3 py-1 text-xs focus:outline-none"
        />
      </div>

      <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
        <table className="w-full text-left text-xs text-slate-700">
          <thead className="bg-slate-50 border-b border-slate-200 text-slate-900 font-semibold">
            <tr>
              <th className="px-3 py-2 w-10 text-slate-400">#</th>
              {headers.map((h, i) => (
                <th
                  key={i}
                  className="px-3 py-2 border-r last:border-0 border-slate-200 whitespace-nowrap"
                >
                  <HighlightedText text={h} highlight={activeQuery} />
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {filteredData.map((row, rIdx) => (
              <tr key={rIdx} className="hover:bg-slate-50/80">
                <td className="px-3 py-2 text-[10px] text-slate-400 font-mono">
                  {rIdx + 1}
                </td>
                {headers.map((_, cIdx) => (
                  <td
                    key={cIdx}
                    className="px-3 py-2 border-r last:border-0 border-slate-100 whitespace-nowrap"
                  >
                    <HighlightedText
                      text={row[cIdx] !== undefined ? row[cIdx] : ""}
                      highlight={activeQuery}
                    />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function HtmlViewer({
  content,
  filePath,
  searchQuery,
}: {
  content: string;
  filePath: string;
  searchQuery: string;
}) {
  const [mode, setMode] = useState<"rendered" | "code">("rendered");

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between border-b border-slate-200 pb-3">
        <div className="flex items-center gap-1 rounded-lg bg-slate-100 p-1">
          <button
            type="button"
            onClick={() => setMode("rendered")}
            className={`flex items-center gap-1.5 rounded-md px-3 py-1 text-xs font-semibold transition ${
              mode === "rendered"
                ? "bg-white text-slate-900 shadow-sm"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            <Eye className="h-3.5 w-3.5" />
            Rendered HTML View
          </button>
          <button
            type="button"
            onClick={() => setMode("code")}
            className={`flex items-center gap-1.5 rounded-md px-3 py-1 text-xs font-semibold transition ${
              mode === "code"
                ? "bg-white text-slate-900 shadow-sm"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            <Code className="h-3.5 w-3.5" />
            HTML Source Code
          </button>
        </div>
      </div>

      {mode === "rendered" ? (
        <div className="rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden min-h-[400px]">
          <iframe
            title={filePath}
            srcDoc={content}
            className="w-full h-[500px] border-0"
            sandbox="allow-same-origin allow-scripts"
          />
        </div>
      ) : (
        <pre className="rounded-xl border border-slate-200 bg-slate-900 p-4 font-mono text-xs text-slate-100 overflow-x-auto max-h-[500px]">
          <code>
            {searchQuery.trim()
              ? content.split("\n").map((line, idx) => (
                  <div key={idx}>
                    <HighlightedText text={line} highlight={searchQuery} />
                  </div>
                ))
              : content}
          </code>
        </pre>
      )}
    </div>
  );
}

function PdfViewer({ path, filename }: { path: string; filename: string }) {
  const pdfUrl = `/api/departments/finance/brain/file-content?path=${encodeURIComponent(path)}`;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between rounded-xl border border-slate-200 bg-slate-50 p-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-rose-100 text-rose-600 font-bold">
            PDF
          </div>
          <div>
            <h4 className="text-sm font-bold text-slate-900">{filename}</h4>
            <p className="text-xs text-slate-500">PDF Document Viewer</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <a
            href={pdfUrl}
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-100 shadow-sm"
          >
            <ExternalLink className="h-3.5 w-3.5" />
            Open Fullscreen
          </a>
        </div>
      </div>

      <div className="rounded-xl border border-slate-200 bg-slate-900/5 shadow-sm overflow-hidden">
        <iframe
          title={filename}
          src={pdfUrl}
          className="w-full h-[600px] border-0"
        />
      </div>
    </div>
  );
}

export default function BrainViewer({ department }: BrainViewerProps) {
  const [query, setQuery] = useState("");
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [openFolders, setOpenFolders] = useState<Record<string, boolean>>({});
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    setSelectedPath(null);
    setQuery("");
  }, [department]);

  const listQuery = useQuery({
    queryKey: ["brain-tree", department, query],
    queryFn: () => brainApi.list(department, query),
  });

  const contentQuery = useQuery({
    queryKey: ["brain-file-content", department, selectedPath],
    queryFn: () => brainApi.getFileContent(department, selectedPath!),
    enabled: !!selectedPath,
  });

  const files: FileItem[] = useMemo(() => {
    return listQuery.data?.files || [];
  }, [listQuery.data]);

  // Group files by folder
  const groupedFiles = useMemo(() => {
    const groups: Record<string, FileItem[]> = { Root: [] };
    files.forEach((file) => {
      const folderKey = file.folder ? file.folder : "Root";
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
    if ([".md", ".txt", ".doc", ".docx"].includes(ext)) return FileText;
    if (
      [
        ".yaml",
        ".yml",
        ".json",
        ".js",
        ".ts",
        ".py",
        ".sh",
        ".bat",
        ".html",
        ".htm",
      ].includes(ext)
    )
      return FileCode;
    return File;
  };

  const selectedFile = useMemo(() => {
    if (!selectedPath) return null;
    return files.find(
      (f) =>
        f.full_path === selectedPath ||
        f.rel_path === selectedPath ||
        f.slug === selectedPath,
    );
  }, [files, selectedPath]);

  const handleCopyContent = () => {
    if (contentQuery.data?.content) {
      navigator.clipboard.writeText(contentQuery.data.content);
      setCopied(true);
      toast.success("Copied content to clipboard");
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="flex h-full min-h-[36rem] flex-col text-white space-y-4">
      {/* Header bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-700/60 pb-4 text-white">
        <div className="flex items-center gap-2">
          {selectedPath && (
            <button
              type="button"
              className="btn-ghost !px-2 mr-1 text-slate-300 hover:text-white"
              onClick={() => setSelectedPath(null)}
            >
              <ArrowLeft className="h-4 w-4" />
              Back
            </button>
          )}
          <div>
            <h2 className="text-xl font-bold text-white">Department Brain</h2>
            <p className="text-xs text-slate-300 mt-1">
              {files.length} {files.length === 1 ? "file" : "files"}{" "}
              {query ? `matching "${query}"` : "available"}
            </p>
          </div>
        </div>

        <div className="relative min-w-[260px]">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            className="input pl-9 text-xs py-1.5"
            placeholder="Search filenames & full-text content…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
      </div>

      <div className="grid flex-1 grid-cols-1 overflow-hidden lg:grid-cols-[320px_1fr]">
        {/* Left pane: Clean File & Folder Tree (No background) */}
        <div className="border-r border-slate-200 dark:border-slate-800 overflow-y-auto p-3 bg-transparent text-slate-900 dark:text-white">
          {listQuery.isLoading && (
            <div className="flex justify-center py-12 text-slate-400">
              <Loader2 className="h-5 w-5 animate-spin" />
            </div>
          )}

          {!listQuery.isLoading && files.length === 0 && (
            <div className="py-8 px-4 text-center text-xs text-slate-500 dark:text-slate-400">
              {query
                ? `No files containing "${query}"`
                : "No files found in this department."}
            </div>
          )}

          {!listQuery.isLoading && files.length > 0 && (
            <div className="space-y-3">
              {Object.entries(groupedFiles).map(([folderName, folderFiles]) => {
                if (folderFiles.length === 0) return null;
                const isOpen = openFolders[folderName] !== false;

                return (
                  <div key={folderName} className="space-y-1">
                    {folderName !== "Root" && (
                      <button
                        type="button"
                        className="flex w-full items-center gap-1.5 rounded-md px-2 py-1 text-left text-xs font-semibold text-slate-900 dark:text-white hover:bg-slate-100/60 dark:hover:bg-slate-800/60"
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
                        <span className="ml-auto text-[10px] text-slate-400 dark:text-slate-500">
                          {folderFiles.length}
                        </span>
                      </button>
                    )}

                    {(folderName === "Root" || isOpen) && (
                      <div
                        className={
                          folderName !== "Root"
                            ? "pl-4 space-y-0.5"
                            : "space-y-0.5"
                        }
                      >
                        {folderFiles.map((file) => {
                          const fileKey =
                            file.full_path ||
                            file.rel_path ||
                            file.slug ||
                            file.name;
                          const isSelected = selectedPath === fileKey;
                          const IconComp = getFileIcon(file.ext);

                          return (
                            <button
                              key={fileKey}
                              type="button"
                              onClick={() => setSelectedPath(fileKey)}
                              className={`flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-left text-xs transition ${
                                isSelected
                                  ? "bg-brand/10 dark:bg-brand/20 font-bold text-brand ring-1 ring-brand/30"
                                  : "text-slate-800 dark:text-slate-200 hover:bg-slate-100/60 dark:hover:bg-slate-800/60"
                              }`}
                            >
                              <IconComp className="h-3.5 w-3.5 shrink-0 text-slate-500 dark:text-slate-400" />
                              <span className="flex-1 truncate">
                                <HighlightedText
                                  text={file.name}
                                  highlight={query}
                                />
                              </span>
                              {file.ext && (
                                <span className="rounded bg-slate-200/60 dark:bg-slate-800 px-1 py-0.5 text-[9px] font-mono text-slate-700 dark:text-slate-300 uppercase">
                                  {file.ext.replace(".", "")}
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

        {/* Right pane: Tidy Document Preview Content (Dark mode dark bg/white text, Light mode light bg/dark text) */}
        <div className="overflow-y-auto p-6 bg-white dark:bg-slate-900 text-slate-900 dark:text-white">
          {!selectedPath && (
            <div className="flex h-full flex-col items-center justify-center text-center text-slate-400 py-16">
              <FileText className="h-12 w-12 stroke-[1.5] text-slate-300 dark:text-slate-600 mb-3" />
              <p className="text-sm font-medium text-slate-700 dark:text-slate-300">
                Select a document to view
              </p>
              <p className="text-xs text-slate-400 dark:text-slate-500 mt-1 max-w-xs">
                Click any Markdown, PDF, HTML, or CSV file on the left to
                preview formatted document content.
              </p>
            </div>
          )}

          {selectedPath && (
            <div className="space-y-6">
              <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-4">
                <div>
                  <h3 className="text-lg font-bold text-slate-900 dark:text-white">
                    <HighlightedText
                      text={
                        selectedFile?.name ||
                        selectedPath.split("/").pop() ||
                        ""
                      }
                      highlight={query}
                    />
                  </h3>
                  <p className="text-xs text-slate-500 dark:text-slate-400 font-mono mt-0.5">
                    {selectedPath}
                  </p>
                </div>

                {contentQuery.data && (
                  <button
                    type="button"
                    onClick={handleCopyContent}
                    className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-sm hover:bg-slate-50 active:scale-95"
                  >
                    {copied ? (
                      <Check className="h-3.5 w-3.5 text-emerald-600" />
                    ) : (
                      <Copy className="h-3.5 w-3.5" />
                    )}
                    {copied ? "Copied" : "Copy Content"}
                  </button>
                )}
              </div>

              {contentQuery.isLoading && (
                <div className="flex justify-center py-16 text-slate-400">
                  <Loader2 className="h-6 w-6 animate-spin" />
                </div>
              )}

              {contentQuery.isError && (
                <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                  Failed to load file content.
                </div>
              )}

              {contentQuery.data && (
                <div>
                  {/* Tidy PDF Viewer */}
                  {contentQuery.data.ext === ".pdf" ? (
                    <PdfViewer
                      path={selectedPath}
                      filename={contentQuery.data.name}
                    />
                  ) : /* Tidy HTML Viewer */
                  [".html", ".htm"].includes(contentQuery.data.ext) ? (
                    <HtmlViewer
                      content={contentQuery.data.content}
                      filePath={selectedPath}
                      searchQuery={query}
                    />
                  ) : /* Tidy CSV Viewer */
                  contentQuery.data.ext === ".csv" ? (
                    <CsvViewer
                      content={contentQuery.data.content}
                      searchQuery={query}
                    />
                  ) : /* Tidy Markdown Viewer */
                  [".md", ".markdown"].includes(contentQuery.data.ext) ? (
                    <MarkdownDocumentViewer
                      content={contentQuery.data.content}
                      filename={contentQuery.data.name}
                      searchQuery={query}
                    />
                  ) : (
                    /* General Tidy Code / Text Viewer with Search Term Highlighting */
                    <pre className="rounded-xl border border-slate-200 bg-slate-900 p-4 font-mono text-xs text-slate-100 overflow-x-auto max-h-[600px]">
                      <code>
                        {query.trim()
                          ? contentQuery.data.content
                              .split("\n")
                              .map((line, idx) => (
                                <div key={idx}>
                                  <HighlightedText
                                    text={line}
                                    highlight={query}
                                  />
                                </div>
                              ))
                          : contentQuery.data.content || "# Empty file"}
                      </code>
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
