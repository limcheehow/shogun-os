import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  ArrowLeft,
  Bot,
  Clock,
  Copy,
  Loader2,
  MessageSquare,
  Search,
  Sparkles,
  User,
  Wrench,
} from 'lucide-react';
import toast from 'react-hot-toast';
import { chatApi } from '../lib/api';
import type { ChatMessage, ChatSession, ChatToolCall } from '../lib/types';

interface ChatHistoryProps {
  department: string;
}

const IMPORTED_ID = 'imported';
const IMPORTED_TITLE = 'Imported history';

function ToolDetailCard({ tool }: { tool: ChatToolCall }) {
  const [showDetails, setShowDetails] = useState(false);

  return (
    <div className="rounded-xl border border-slate-200 bg-white overflow-hidden shadow-xs">
      <div
        className="flex items-center justify-between px-3 py-2 bg-slate-50 cursor-pointer hover:bg-slate-100/80 transition"
        onClick={() => setShowDetails((v) => !v)}
      >
        <div className="flex items-center gap-2">
          <Wrench className="h-3.5 w-3.5 text-brand" />
          <span className="text-xs font-mono font-semibold text-slate-800">{tool.name}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-semibold text-emerald-700 uppercase">
            {tool.status || 'Executed'}
          </span>
          <span className="text-[10px] text-slate-400">
            {showDetails ? 'Hide details ▲' : 'View details ▼'}
          </span>
        </div>
      </div>

      {showDetails && (
        <div className="p-3 border-t border-slate-200 bg-slate-900 space-y-2 text-xs font-mono">
          {tool.arguments !== undefined && (
            <div>
              <div className="text-[10px] uppercase font-semibold text-slate-400 mb-1">
                Inputs / Arguments:
              </div>
              <pre className="overflow-x-auto text-[11px] text-slate-200 bg-black/40 p-2 rounded-lg">
                {typeof tool.arguments === 'string'
                  ? tool.arguments
                  : JSON.stringify(tool.arguments, null, 2)}
              </pre>
            </div>
          )}
          {tool.result !== undefined && (
            <div>
              <div className="text-[10px] uppercase font-semibold text-slate-400 mb-1">
                Execution Result:
              </div>
              <pre className="max-h-48 overflow-auto text-[11px] text-slate-200 bg-black/40 p-2 rounded-lg">
                {typeof tool.result === 'string'
                  ? tool.result
                  : JSON.stringify(tool.result, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function deriveTitle(messages: ChatMessage[]): string {
  const firstUser = messages.find((m) => m.role === 'user' && m.content.trim().length > 0);
  if (!firstUser) return 'New session';
  const content = firstUser.content.trim();
  return content.length > 80 ? content.slice(0, 80) + '…' : content;
}

function buildSessions(all: ChatMessage[]): ChatSession[] {
  const byId = new Map<string, ChatMessage[]>();
  for (const m of all) {
    const key = m.session_id || IMPORTED_ID;
    if (!byId.has(key)) byId.set(key, []);
    byId.get(key)!.push(m);
  }
  const sessions: ChatSession[] = [];
  for (const [id, msgs] of byId) {
    const sorted = [...msgs].sort(
      (a, b) =>
        (a.created_at ? Date.parse(a.created_at) : 0) - (b.created_at ? Date.parse(b.created_at) : 0),
    );
    const created = sorted[0]?.created_at || new Date().toISOString();
    const updated = sorted[sorted.length - 1]?.created_at || created;
    const hasTools = sorted.some((m) => m.tool_calls && m.tool_calls.length > 0);
    sessions.push({
      id,
      title: id === IMPORTED_ID ? IMPORTED_TITLE : deriveTitle(sorted),
      created_at: created,
      updated_at: updated,
      message_count: sorted.length,
      has_tools: hasTools,
      messages: sorted,
    });
  }
  // Sort by updated_at desc; Imported history to the bottom.
  sessions.sort((a, b) => {
    if (a.id === IMPORTED_ID && b.id !== IMPORTED_ID) return 1;
    if (b.id === IMPORTED_ID && a.id !== IMPORTED_ID) return -1;
    return Date.parse(b.updated_at || b.created_at) - Date.parse(a.updated_at || a.created_at);
  });
  return sessions;
}

export default function ChatHistory({ department }: ChatHistoryProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const [filterType, setFilterType] = useState<'all' | 'tools'>('all');

  const historyQuery = useQuery({
    queryKey: ['chat-history', department],
    queryFn: () => chatApi.history(department),
  });

  const sessions = useMemo(() => {
    const raw = historyQuery.data;
    return buildSessions(Array.isArray(raw) ? raw : []);
  }, [historyQuery.data]);

  const filteredSessions = useMemo(() => {
    return sessions.filter((s) => {
      if (filterType === 'tools' && !s.has_tools) return false;
      if (!searchQuery.trim()) return true;
      const q = searchQuery.toLowerCase();
      return (
        s.title.toLowerCase().includes(q) ||
        s.messages.some((m) => m.content.toLowerCase().includes(q))
      );
    });
  }, [sessions, searchQuery, filterType]);

  const selectedSession = useMemo(() => {
    if (!selectedSessionId) return null;
    return sessions.find((s) => s.id === selectedSessionId) || null;
  }, [sessions, selectedSessionId]);

  const copyPromptText = (text: string) => {
    void navigator.clipboard.writeText(text).then(
      () => toast.success('Copied to clipboard'),
      () => toast.error('Copy failed'),
    );
  };

  return (
    <div className="flex h-full min-h-[34rem] flex-col overflow-hidden rounded-2xl border border-surface-border bg-white shadow-sm">
      {/* Top Header bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-surface-border p-4 bg-slate-50/50">
        <div className="flex items-center gap-2">
          {selectedSessionId && (
            <button
              type="button"
              className="btn-ghost !px-2 mr-1"
              onClick={() => setSelectedSessionId(null)}
            >
              <ArrowLeft className="h-4 w-4" />
              Back
            </button>
          )}
          <div>
            <h2 className="text-base font-semibold text-slate-900 flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-brand" />
              Department Chat History
            </h2>
            <p className="text-xs text-slate-500">
              {sessions.length} chat {sessions.length === 1 ? 'session' : 'sessions'} logged
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <div className="flex items-center gap-1 rounded-lg border border-slate-200 bg-white p-1">
            <button
              type="button"
              onClick={() => setFilterType('all')}
              className={`rounded-md px-2.5 py-1 text-xs font-medium transition ${
                filterType === 'all'
                  ? 'bg-slate-900 text-white'
                  : 'text-slate-600 hover:bg-slate-100'
              }`}
            >
              All Sessions
            </button>
            <button
              type="button"
              onClick={() => setFilterType('tools')}
              className={`rounded-md px-2.5 py-1 text-xs font-medium transition ${
                filterType === 'tools'
                  ? 'bg-slate-900 text-white'
                  : 'text-slate-600 hover:bg-slate-100'
              }`}
            >
              With Tools
            </button>
          </div>

          <div className="relative min-w-[220px]">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              className="input pl-9 text-xs py-1.5"
              placeholder="Search sessions…"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
        </div>
      </div>

      <div className="grid flex-1 grid-cols-1 overflow-hidden lg:grid-cols-[360px_1fr]">
        {/* Left pane: Session list */}
        <div className="border-r border-surface-border overflow-y-auto p-3 bg-slate-50/30">
          {historyQuery.isLoading && (
            <div className="flex justify-center py-16 text-slate-400">
              <Loader2 className="h-6 w-6 animate-spin" />
            </div>
          )}

          {!historyQuery.isLoading && filteredSessions.length === 0 && (
            <div className="py-16 px-4 text-center text-xs text-slate-400">
              {searchQuery ? `No sessions matching “${searchQuery}”` : 'No chat history logged yet.'}
            </div>
          )}

          {!historyQuery.isLoading && filteredSessions.length > 0 && (
            <div className="space-y-2">
              {filteredSessions.map((session) => {
                const isSelected = selectedSessionId === session.id;
                const dateLabel = session.updated_at
                  ? new Date(session.updated_at).toLocaleString()
                  : '';
                return (
                  <button
                    key={session.id}
                    type="button"
                    onClick={() => setSelectedSessionId(session.id)}
                    className={`flex w-full flex-col gap-1.5 rounded-xl p-3.5 text-left transition border ${
                      isSelected
                        ? 'border-brand/40 bg-brand/5 shadow-xs ring-1 ring-brand/20'
                        : 'border-slate-200/80 bg-white hover:border-slate-300 hover:shadow-xs'
                    }`}
                  >
                    <div className="flex items-center justify-between text-[11px]">
                      <span className="flex items-center gap-1 font-semibold text-slate-500">
                        <MessageSquare className="h-3.5 w-3.5 text-brand" />
                        Session
                      </span>
                      <span className="flex items-center gap-1 text-slate-400 font-mono text-[10px]">
                        <Clock className="h-3 w-3" />
                        {dateLabel}
                      </span>
                    </div>

                    <div className="text-xs font-semibold text-slate-900 line-clamp-2">
                      {session.title}
                    </div>

                    <div className="text-[11px] text-slate-500">
                      {session.message_count} message{session.message_count === 1 ? '' : 's'}
                    </div>

                    {session.has_tools && (
                      <div className="mt-1 flex items-center gap-1 text-[10px] font-semibold text-brand bg-brand/10 w-fit px-2 py-0.5 rounded-md">
                        <Wrench className="h-3 w-3" />
                        tools executed
                      </div>
                    )}
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* Right pane: Full session transcript */}
        <div className="overflow-y-auto p-6 bg-white">
          {!selectedSession && (
            <div className="flex h-full flex-col items-center justify-center text-center text-slate-400 py-16">
              <MessageSquare className="h-12 w-12 stroke-[1.5] text-slate-300 mb-3" />
              <p className="text-sm font-medium text-slate-600">Select a session to inspect</p>
              <p className="text-xs text-slate-400 mt-1 max-w-xs">
                Click any chat session on the left to view the full transcript — prompts, assistant
                responses, and executed tool calls.
              </p>
            </div>
          )}

          {selectedSession && (
            <div className="space-y-6">
              <div className="flex items-center justify-between border-b border-surface-border pb-3">
                <div>
                  <h3 className="text-sm font-semibold text-slate-900">{selectedSession.title}</h3>
                  <p className="text-[11px] text-slate-500 mt-0.5">
                    {selectedSession.message_count} message{selectedSession.message_count === 1 ? '' : 's'}
                    {selectedSession.updated_at && (
                      <> · last {new Date(selectedSession.updated_at).toLocaleString()}</>
                    )}
                  </p>
                </div>
                {selectedSession.id === IMPORTED_ID && (
                  <span className="rounded-md bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-slate-600 uppercase">
                    Legacy
                  </span>
                )}
              </div>

              {selectedSession.messages.map((m) =>
                m.role === 'user' ? (
                  <div key={m.id} className="rounded-2xl border border-brand/20 bg-brand/5 p-4 shadow-xs">
                    <div className="flex items-center justify-between mb-2 pb-2 border-b border-brand/10">
                      <span className="flex items-center gap-1.5 text-xs font-semibold text-brand">
                        <User className="h-3.5 w-3.5" /> User
                      </span>
                      <div className="flex items-center gap-2">
                        {m.created_at && (
                          <span className="text-[11px] text-slate-400 font-mono">
                            {new Date(m.created_at).toLocaleString()}
                          </span>
                        )}
                        <button
                          type="button"
                          className="btn-ghost !px-1.5 !py-0.5 text-[11px] text-slate-600"
                          onClick={() => copyPromptText(m.content)}
                          title="Copy text"
                        >
                          <Copy className="h-3 w-3" />
                        </button>
                      </div>
                    </div>
                    <div className="text-sm font-medium text-slate-900 whitespace-pre-wrap leading-relaxed">
                      {m.content}
                    </div>
                  </div>
                ) : m.role === 'assistant' ? (
                  <div key={m.id} className="rounded-2xl border border-surface-border bg-slate-50/50 p-5 shadow-xs">
                    <div className="flex items-center justify-between mb-3 pb-2.5 border-b border-surface-border">
                      <span className="flex items-center gap-1.5 text-xs font-semibold text-slate-800">
                        <Bot className="h-4 w-4 text-emerald-600" /> Assistant
                      </span>
                      {m.created_at && (
                        <span className="text-[11px] text-slate-400 font-mono">
                          {new Date(m.created_at).toLocaleString()}
                        </span>
                      )}
                    </div>

                    {m.content && (
                      <article className="prose-chat text-sm leading-relaxed text-slate-800">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.content}</ReactMarkdown>
                      </article>
                    )}

                    {m.tool_calls && m.tool_calls.length > 0 && (
                      <div className="mt-5 pt-4 border-t border-slate-200/80 space-y-3">
                        <div className="text-xs font-semibold text-slate-700 flex items-center gap-1.5">
                          <Wrench className="h-3.5 w-3.5 text-brand" />
                          Executed Tools ({m.tool_calls.length})
                        </div>
                        <div className="space-y-2">
                          {m.tool_calls.map((tool) => (
                            <ToolDetailCard key={tool.id} tool={tool} />
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ) : null,
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}