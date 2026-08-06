import { useState } from 'react';
import { MessageSquare, Minus } from 'lucide-react';
import Chat from './Chat';

interface FloatingChatProps {
  department: string;
  displayName: string;
  persona?: string;
  color?: string;
}

export default function FloatingChat({
  department,
  displayName,
  persona,
  color = '#6366f1',
}: FloatingChatProps) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col items-end">
      {isOpen ? (
        <div className="flex h-[540px] w-96 max-w-[calc(100vw-2rem)] max-h-[calc(100vh-6rem)] flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl transition-all animate-in fade-in slide-in-from-bottom-4 duration-200">
          {/* Header */}
          <div
            className="flex items-center justify-between px-4 py-3 text-white shadow-sm"
            style={{ backgroundColor: color }}
          >
            <div className="flex items-center gap-2.5 min-w-0">
              <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-white/20 text-white font-semibold text-xs shrink-0">
                {(displayName || '?').charAt(0)}
              </div>
              <div className="min-w-0">
                <div className="truncate text-sm font-semibold leading-tight">
                  {displayName} Agent
                </div>
                {persona && (
                  <div className="truncate text-[11px] text-white/80 leading-tight">
                    {persona}
                  </div>
                )}
              </div>
            </div>
            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={() => setIsOpen(false)}
                className="rounded-lg p-1 hover:bg-white/20 transition text-white"
                title="Minimize chat"
              >
                <Minus className="h-4 w-4" />
              </button>
            </div>
          </div>

          {/* Embedded Chat Container */}
          <div className="flex-1 overflow-hidden">
            <Chat department={department} />
          </div>
        </div>
      ) : (
        <button
          type="button"
          onClick={() => setIsOpen(true)}
          className="group flex items-center gap-2.5 rounded-full px-4 py-3 text-white shadow-xl transition hover:scale-105 active:scale-95"
          style={{ backgroundColor: color }}
          title={`Open ${displayName} Chat`}
        >
          <MessageSquare className="h-5 w-5" />
          <span className="text-sm font-semibold pr-1">Chat with {displayName}</span>
          <span className="relative flex h-2.5 w-2.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-white opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-white"></span>
          </span>
        </button>
      )}
    </div>
  );
}
