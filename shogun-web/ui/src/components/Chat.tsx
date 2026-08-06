import { useEffect, useMemo, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  ChevronDown,
  ChevronRight,
  Loader2,
  Plus,
  Send,
  Wrench,
  Wifi,
  WifiOff,
} from 'lucide-react';
import clsx from 'clsx';
import toast from 'react-hot-toast';
import { chatApi, useChatSocket } from '../lib/api';
import type { ChatMessage, ChatToolCall } from '../lib/types';

interface ChatProps {
  department: string;
}

function ToolCallCard({ call }: { call: ChatToolCall }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="mt-2 overflow-hidden rounded-lg border border-slate-200 bg-slate-50">
      <button
        type="button"
        className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs font-medium text-slate-700 hover:bg-slate-100"
        onClick={() => setOpen((v) => !v)}
      >
        <Wrench className="h-3.5 w-3.5 text-slate-500" />
        <span className="flex-1 truncate">{call.name}</span>
        <span
          className={clsx(
            'rounded-full px-1.5 py-0.5 text-[10px] uppercase tracking-wide',
            call.status === 'error'
              ? 'bg-rose-100 text-rose-700'
              : call.status === 'running'
                ? 'bg-sky-100 text-sky-700'
                : 'bg-emerald-100 text-emerald-700',
          )}
        >
          {call.status || 'done'}
        </span>
        {open ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
      </button>
      {open && (
        <div className="space-y-2 border-t border-slate-200 bg-white px-3 py-2 text-xs text-slate-600">
          {call.arguments !== undefined && (
            <div>
              <div className="mb-1 font-medium text-slate-500">Arguments</div>
              <pre className="overflow-x-auto rounded bg-slate-900 p-2 text-[11px] text-slate-100">
                {typeof call.arguments === 'string'
                  ? call.arguments
                  : JSON.stringify(call.arguments, null, 2)}
              </pre>
            </div>
          )}
          {call.result !== undefined && (
            <div>
              <div className="mb-1 font-medium text-slate-500">Result</div>
              <pre className="max-h-48 overflow-auto rounded bg-slate-900 p-2 text-[11px] text-slate-100">
                {typeof call.result === 'string'
                  ? call.result
                  : JSON.stringify(call.result, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function Chat({ department }: ChatProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [sending, setSending] = useState(false);
  const [currentSessionId, setCurrentSessionId] = useState<string>('');
  const [resetKey, setResetKey] = useState(0);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let alive = true;
    setLoadingHistory(true);
    chatApi
      .history(department)
      .then((data) => {
        if (!alive) return;
        const all = Array.isArray(data) ? data : [];
        // Pick the most recent session_id (by latest message created_at).
        const withIds = all.filter((m) => m.session_id);
        let resumeId = '';
        if (withIds.length > 0) {
          const latest = withIds.reduce((acc, m) => {
            const t = m.created_at ? Date.parse(m.created_at) : 0;
            return t > acc.t ? { id: m.session_id!, t } : acc;
          }, { id: '', t: 0 });
          resumeId = latest.id;
        }
        if (!resumeId) {
          resumeId = `sess-${Date.now()}`;
        }
        setCurrentSessionId(resumeId);
        setMessages(all.filter((m) => m.session_id === resumeId));
      })
      .catch(() => {
        if (alive) {
          setMessages([]);
          setCurrentSessionId(`sess-${Date.now()}`);
        }
      })
      .finally(() => {
        if (alive) setLoadingHistory(false);
      });
    return () => {
      alive = false;
    };
  }, [department]);

  const { connected, send } = useChatSocket(department, {
    resetKey,
    onEvent: (event) => {
      if (event.type === 'message') {
        setMessages((prev) => {
          const idx = prev.findIndex((m) => m.id === event.message.id);
          if (idx >= 0) {
            const next = [...prev];
            next[idx] = { ...next[idx], ...event.message, session_id: currentSessionId, streaming: false };
            return next;
          }
          return [...prev, { ...event.message, session_id: currentSessionId, streaming: false }];
        });
        setSending(false);
      } else if (event.type === 'delta') {
        setMessages((prev) => {
          const idx = prev.findIndex((m) => m.id === event.id);
          if (idx >= 0) {
            const next = [...prev];
            next[idx] = {
              ...next[idx],
              content: (next[idx].content || '') + event.content,
              streaming: true,
            };
            return next;
          }
          return [
            ...prev,
            {
              id: event.id,
              role: 'assistant',
              content: event.content,
              streaming: true,
              session_id: currentSessionId,
              created_at: new Date().toISOString(),
            },
          ];
        });
      } else if (event.type === 'tool_call') {
        setMessages((prev) => {
          const idx = prev.findIndex((m) => m.id === event.id);
          if (idx < 0) {
            return [
              ...prev,
              {
                id: event.id,
                role: 'assistant',
                content: '',
                tool_calls: [event.tool_call],
                session_id: currentSessionId,
                streaming: true,
              },
            ];
          }
          const next = [...prev];
          const existing = next[idx].tool_calls || [];
          const tIdx = existing.findIndex((t) => t.id === event.tool_call.id);
          const tool_calls =
            tIdx >= 0
              ? existing.map((t, i) => (i === tIdx ? { ...t, ...event.tool_call } : t))
              : [...existing, event.tool_call];
          next[idx] = { ...next[idx], tool_calls };
          return next;
        });
      } else if (event.type === 'done') {
        setMessages((prev) =>
          prev.map((m) => (m.id === event.id ? { ...m, streaming: false } : m)),
        );
        setSending(false);
      } else if (event.type === 'error') {
        toast.error(event.message || 'Chat error');
        setSending(false);
      }
    },
  });

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, sending]);

  // Auto-save the current session's messages whenever they change.
  useEffect(() => {
    if (loadingHistory || messages.length === 0 || !currentSessionId) return;
    const t = window.setTimeout(() => {
      const sessionMessages = messages.map((m) => ({ ...m, session_id: currentSessionId }));
      chatApi.saveMessages(department, sessionMessages).catch(() => {});
    }, 600);
    return () => window.clearTimeout(t);
  }, [messages, department, loadingHistory, currentSessionId]);

  const canSend = useMemo(
    () => input.trim().length > 0 && !sending,
    [input, sending],
  );

  const handleNewSession = () => {
    // Flush-save current session first.
    if (messages.length > 0 && currentSessionId) {
      const sessionMessages = messages.map((m) => ({ ...m, session_id: currentSessionId }));
      chatApi.saveMessages(department, sessionMessages).catch(() => {});
    }
    const newId = `sess-${Date.now()}`;
    setCurrentSessionId(newId);
    setMessages([]);
    setResetKey((k) => k + 1); // reconnect WS → fresh agent context
  };

  const handleSend = () => {
    const content = input.trim();
    if (!content) return;
    const id = `local-${Date.now()}`;
    const newMsg: ChatMessage = {
      id,
      role: 'user',
      content,
      created_at: new Date().toISOString(),
      session_id: currentSessionId,
    };
    setMessages((prev) => [...prev, newMsg]);
    setInput('');
    setSending(true);
    try {
      send(content);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to send');
      setSending(false);
    }
  };

  return (
    <div className="flex h-full min-h-[28rem] flex-col overflow-hidden rounded-xl border border-surface-border bg-white">
      <div className="flex items-center justify-between border-b border-surface-border px-4 py-2.5">
        <div className="text-sm font-medium text-slate-800">Chat</div>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={handleNewSession}
            title="Start a new session"
            className="flex items-center gap-1.5 rounded-lg border border-surface-border bg-white px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-surface-muted"
          >
            <Plus className="h-3.5 w-3.5" />
            New
          </button>
          <div className="flex items-center gap-1.5 text-xs text-slate-500">
            {connected ? (
              <>
                <Wifi className="h-3.5 w-3.5 text-emerald-500" /> Connected
              </>
            ) : (
              <>
                <WifiOff className="h-3.5 w-3.5 text-rose-500" /> Reconnecting
              </>
            )}
          </div>
        </div>
      </div>

      <div className="flex-1 space-y-4 overflow-y-auto px-4 py-4">
        {loadingHistory && (
          <div className="flex items-center justify-center py-12 text-slate-400">
            <Loader2 className="h-5 w-5 animate-spin" />
          </div>
        )}
        {!loadingHistory && messages.length === 0 && (
          <div className="rounded-lg border border-dashed border-slate-200 bg-slate-50 px-4 py-10 text-center text-sm text-slate-500">
            Start a conversation with this department agent.
          </div>
        )}
        {messages.map((m) => (
          <div
            key={m.id}
            className={clsx('flex', m.role === 'user' ? 'justify-end' : 'justify-start')}
          >
            <div
              className={clsx(
                'max-w-[85%] rounded-2xl px-3.5 py-2.5',
                m.role === 'user'
                  ? 'bg-brand text-white'
                  : 'border border-surface-border bg-surface-muted text-slate-800',
              )}
            >
              {m.role === 'assistant' ? (
                <div className="prose-chat">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.content || ' '}</ReactMarkdown>
                </div>
              ) : (
                <div className="whitespace-pre-wrap text-sm">{m.content}</div>
              )}
              {m.tool_calls?.map((tc) => (
                <ToolCallCard key={tc.id} call={tc} />
              ))}
              {m.streaming && (
                <div className="mt-1 flex items-center gap-1 text-[11px] text-slate-400">
                  <Loader2 className="h-3 w-3 animate-spin" /> Thinking…
                </div>
              )}
            </div>
          </div>
        ))}
        {sending && !messages.some((m) => m.streaming) && (
          <div className="flex justify-start">
            <div className="flex items-center gap-2 rounded-2xl border border-surface-border bg-surface-muted px-3.5 py-2.5 text-sm text-slate-500">
              <Loader2 className="h-4 w-4 animate-spin" />
              Assistant is responding…
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="border-t border-surface-border p-3">
        <form
          className="flex items-end gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
        >
          <textarea
            className="input min-h-[44px] max-h-36 resize-y"
            rows={1}
            placeholder="Message the department agent…"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
          />
          <button type="submit" className="btn-primary h-11 px-4" disabled={!canSend}>
            {sending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
          </button>
        </form>
      </div>
    </div>
  );
}
