import { useCallback, useEffect, useRef, useState } from 'react';
import { MessageSquare, PanelRightClose } from 'lucide-react';
import Chat from './Chat';

interface RightChatDockProps {
  department: string;
  displayName: string;
  persona?: string;
  color?: string;
}

export default function RightChatDock({
  department,
  displayName,
  persona,
  color = '#6366f1',
}: RightChatDockProps) {
  const [isOpen, setIsOpen] = useState(true);
  const [width, setWidth] = useState(380);
  const [isResizing, setIsResizing] = useState(false);
  const dragRef = useRef<HTMLDivElement>(null);

  const startResizing = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizing(true);
  }, []);

  useEffect(() => {
    if (!isResizing) return;

    const handleMouseMove = (e: MouseEvent) => {
      const newWidth = window.innerWidth - e.clientX;
      const minW = 280;
      const maxW = Math.min(850, window.innerWidth - 300);
      if (newWidth >= minW && newWidth <= maxW) {
        setWidth(newWidth);
      }
    };

    const handleMouseUp = () => {
      setIsResizing(false);
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isResizing]);

  if (!isOpen) {
    return (
      <button
        type="button"
        onClick={() => setIsOpen(true)}
        className="fixed right-0 top-20 z-40 flex items-center gap-2 rounded-l-xl border border-r-0 border-slate-200 bg-white py-3 px-2.5 shadow-lg transition hover:bg-slate-50 text-slate-700"
        title={`Open ${displayName} Assistant Dock`}
      >
        <div className="relative">
          <MessageSquare className="h-5 w-5 text-brand" />
          <span className="absolute -top-1 -right-1 flex h-2.5 w-2.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-brand opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-brand"></span>
          </span>
        </div>
      </button>
    );
  }

  return (
    <div className="relative flex shrink-0 h-full overflow-hidden">
      {/* Resizable center line drag handle */}
      <div
        ref={dragRef}
        onMouseDown={startResizing}
        onDoubleClick={() => setWidth(380)}
        className={`group relative w-3 -ml-1.5 cursor-col-resize select-none flex items-center justify-center z-20 transition-colors ${
          isResizing ? 'bg-brand/30' : 'hover:bg-brand/20'
        }`}
        title="Drag center line to resize dock (double-click to reset width)"
      >
        <div className="h-8 w-1 rounded-full bg-slate-300 group-hover:bg-brand transition-colors" />
      </div>

      {/* Main Dock Container */}
      <aside
        style={{ width: `${width}px` }}
        className="h-full border-l border-surface-border bg-white flex flex-col shadow-sm select-none overflow-hidden"
      >
        {/* Header */}
        <div
          className="flex items-center justify-between px-4 py-3 text-white shadow-sm shrink-0"
          style={{ backgroundColor: color }}
        >
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-white/20 text-white font-semibold text-xs shrink-0">
              {(displayName || '?').charAt(0)}
            </div>
            <div className="min-w-0">
              <div className="truncate text-sm font-semibold leading-tight">
                {displayName} Assistant
              </div>
              {persona && (
                <div className="truncate text-[11px] text-white/80 leading-tight">
                  {persona}
                </div>
              )}
            </div>
          </div>

          <button
            type="button"
            onClick={() => setIsOpen(false)}
            className="rounded-lg p-1 hover:bg-white/20 transition text-white"
            title="Collapse assistant panel"
          >
            <PanelRightClose className="h-4 w-4" />
          </button>
        </div>

        {/* Main Chat component */}
        <div className="flex-1 overflow-hidden">
          <Chat department={department} />
        </div>
      </aside>
    </div>
  );
}
