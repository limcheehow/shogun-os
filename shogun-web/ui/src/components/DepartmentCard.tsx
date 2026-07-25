import { Link } from 'react-router-dom';
import {
  Boxes,
  Code2,
  Handshake,
  Kanban,
  LifeBuoy,
  Megaphone,
  MessageSquare,
  Package,
  Shield,
  Users,
  Wallet,
  Brain,
  FileText,
  type LucideIcon,
} from 'lucide-react';
import StatusBadge from './StatusBadge';
import type { Department } from '../lib/types';
import { DEPARTMENT_CATALOG } from '../lib/types';

const ICONS: Record<string, LucideIcon> = {
  Users,
  Wallet,
  Handshake,
  Megaphone,
  Shield,
  LifeBuoy,
  Code2,
  Kanban,
  Boxes,
  Package,
};

interface DepartmentCardProps {
  department: Department;
  onAdd?: () => void;
}

export default function DepartmentCard({ department, onAdd }: DepartmentCardProps) {
  const meta = DEPARTMENT_CATALOG[department.key] || department;
  const Icon = ICONS[meta.icon] || Boxes;
  const color = meta.color || department.color || '#6366f1';

  if (!department.active) {
    return (
      <div className="card flex flex-col justify-between p-5 opacity-90">
        <div className="flex items-start gap-3">
          <div
            className="flex h-10 w-10 items-center justify-center rounded-xl text-white"
            style={{ backgroundColor: color }}
          >
            <Icon className="h-5 w-5" />
          </div>
          <div>
            <h3 className="font-semibold text-slate-900">{meta.name}</h3>
            <p className="text-sm text-slate-500">{meta.persona}</p>
            <p className="mt-2 text-sm text-slate-600 line-clamp-2">{meta.description}</p>
          </div>
        </div>
        <button type="button" className="btn-secondary mt-4 w-full" onClick={onAdd}>
          Add Department
        </button>
      </div>
    );
  }

  return (
    <div className="card group flex flex-col p-5 transition hover:shadow-md">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <div
            className="flex h-10 w-10 items-center justify-center rounded-xl text-white"
            style={{ backgroundColor: color }}
          >
            <Icon className="h-5 w-5" />
          </div>
          <div>
            <h3 className="font-semibold text-slate-900">{meta.name}</h3>
            <p className="text-sm text-slate-500">{meta.persona}</p>
          </div>
        </div>
        <StatusBadge status={department.status || department.gateway_status} />
      </div>

      <p className="mt-3 flex-1 text-sm text-slate-600 line-clamp-2">{meta.description}</p>

      <div className="mt-4 grid grid-cols-3 gap-2">
        <Link
          to={`/department/${department.key}?tab=chat`}
          className="btn-secondary !px-2 !py-1.5 text-xs"
        >
          <MessageSquare className="h-3.5 w-3.5" />
          Chat
        </Link>
        <Link
          to={`/department/${department.key}?tab=brain`}
          className="btn-secondary !px-2 !py-1.5 text-xs"
        >
          <Brain className="h-3.5 w-3.5" />
          Brain
        </Link>
        <Link
          to={`/department/${department.key}?tab=docs`}
          className="btn-secondary !px-2 !py-1.5 text-xs"
        >
          <FileText className="h-3.5 w-3.5" />
          Docs
        </Link>
      </div>
    </div>
  );
}
