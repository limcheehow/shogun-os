import { useState } from 'react';
import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  Boxes,
  ChevronDown,
  Code2,
  Handshake,
  Kanban,
  LayoutDashboard,
  LifeBuoy,
  LogOut,
  Menu,
  Megaphone,
  Package,
  Shield,
  Users,
  UserCog,
  Wallet,
  X,
  type LucideIcon,
} from 'lucide-react';
import clsx from 'clsx';
import { departmentsApi, authApi } from '../lib/api';
import { useAuth } from '../lib/auth';
import { DEPARTMENT_CATALOG, type DepartmentKey, type Department } from '../lib/types';
import StatusBadge from './StatusBadge';

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

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  const deptsQuery = useQuery({
    queryKey: ['departments'],
    queryFn: () => departmentsApi.list(),
  });

  const accessQuery = useQuery({
    queryKey: ['my-access'],
    queryFn: () => authApi.myAccess(),
    staleTime: 30_000,
  });

  const rawDepts = deptsQuery.data || [];
  const allDepts: Department[] = Array.isArray(rawDepts) ? rawDepts : (rawDepts as { departments?: Department[] }).departments || [];
  const activeDepts = allDepts.filter((d) => d.active);
  const canManageStaff = user?.role === 'admin' || user?.role === 'hr_manager';

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const sidebar = (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-2.5 border-b border-sidebar-border px-4 py-4">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand text-sm font-bold text-white">
          S
        </div>
        <div>
          <div className="text-sm font-semibold text-sidebar-text">Shogun OS</div>
          <div className="text-[11px] text-sidebar-muted">Command portal</div>
        </div>
      </div>

      <nav className="flex-1 space-y-1 overflow-y-auto p-3">
        <NavLink
          to="/dashboard"
          onClick={() => setMobileOpen(false)}
          className={({ isActive }) =>
            clsx(
              'flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition',
              isActive
                ? 'bg-white/10 text-white'
                : 'text-sidebar-muted hover:bg-sidebar-hover hover:text-sidebar-text',
            )
          }
        >
          <LayoutDashboard className="h-4 w-4" />
          Dashboard
        </NavLink>

        {canManageStaff && (
          <NavLink
            to="/staff"
            onClick={() => setMobileOpen(false)}
            className={({ isActive }) =>
              clsx(
                'flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition',
                isActive
                  ? 'bg-white/10 text-white'
                  : 'text-sidebar-muted hover:bg-sidebar-hover hover:text-sidebar-text',
              )
            }
          >
            <UserCog className="h-4 w-4" />
            Staff
          </NavLink>
        )}

        <div className="px-3 pb-1 pt-4 text-[11px] font-semibold uppercase tracking-wider text-sidebar-muted/80">
          Departments
        </div>

        {activeDepts.length === 0 && (
          <div className="px-3 py-2 text-xs text-sidebar-muted">No active departments</div>
        )}

        {activeDepts.map((d) => {
          const meta = DEPARTMENT_CATALOG[d.key as DepartmentKey] || d;
          const Icon = ICONS[meta.icon] || Boxes;
          return (
            <NavLink
              key={d.key}
              to={`/department/${d.key}`}
              onClick={() => setMobileOpen(false)}
              className={({ isActive }) =>
                clsx(
                  'flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition',
                  isActive
                    ? 'bg-white/10 text-white'
                    : 'text-sidebar-muted hover:bg-sidebar-hover hover:text-sidebar-text',
                )
              }
            >
              <span
                className="flex h-6 w-6 items-center justify-center rounded-md text-white"
                style={{ backgroundColor: meta.color || d.color }}
              >
                <Icon className="h-3.5 w-3.5" />
              </span>
              <span className="flex-1 truncate">{meta.name}</span>
              <StatusBadge
                status={d.status || d.gateway_status}
                showLabel={false}
                size="sm"
              />
            </NavLink>
          );
        })}
      </nav>

      <div className="border-t border-sidebar-border p-3">
        <div className="rounded-lg bg-sidebar-hover px-3 py-2">
          <div className="truncate text-sm font-medium text-sidebar-text">
            {user?.name || 'User'}
          </div>
          <div className="truncate text-xs text-sidebar-muted">{user?.email}</div>
        </div>
      </div>
    </div>
  );

  return (
    <div className="flex h-full min-h-screen bg-surface-muted">
      <aside className="hidden w-64 shrink-0 border-r border-sidebar-border bg-sidebar md:block">
        {sidebar}
      </aside>

      {mobileOpen && (
        <div className="fixed inset-0 z-40 flex md:hidden">
          <div className="w-64 bg-sidebar shadow-xl">{sidebar}</div>
          <button
            type="button"
            className="flex-1 bg-black/40"
            aria-label="Close menu"
            onClick={() => setMobileOpen(false)}
          />
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-surface-border bg-white/90 px-4 backdrop-blur">
          <div className="flex items-center gap-2">
            <button
              type="button"
              className="btn-ghost !px-2 md:hidden"
              onClick={() => setMobileOpen((v) => !v)}
              aria-label="Toggle menu"
            >
              {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </button>
            <Link to="/dashboard" className="text-sm font-semibold text-slate-800 md:hidden">
              Shogun OS
            </Link>
          </div>

          <div className="relative ml-auto">
            <button
              type="button"
              className="flex items-center gap-2 rounded-lg px-2 py-1.5 hover:bg-slate-50"
              onClick={() => setMenuOpen((v) => !v)}
            >
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-light text-sm font-semibold text-brand">
                {(user?.name || user?.email || '?').charAt(0).toUpperCase()}
              </div>
              <div className="hidden text-left sm:block">
                <div className="text-sm font-medium text-slate-800">{user?.name}</div>
                <div className="text-xs text-slate-500">{user?.email}</div>
              </div>
              <ChevronDown className="h-4 w-4 text-slate-400" />
            </button>

            {menuOpen && (
              <>
                <button
                  type="button"
                  className="fixed inset-0 z-40 cursor-default"
                  aria-label="Close user menu"
                  onClick={() => setMenuOpen(false)}
                />
                <div className="absolute right-0 z-50 mt-1 w-52 overflow-hidden rounded-xl border border-surface-border bg-white py-1 shadow-lg">
                  <div className="border-b border-surface-border px-3 py-2 sm:hidden">
                    <div className="text-sm font-medium">{user?.name}</div>
                    <div className="text-xs text-slate-500">{user?.email}</div>
                  </div>
                  <button
                    type="button"
                    className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-slate-700 hover:bg-slate-50"
                    onClick={() => {
                      setMenuOpen(false);
                      void handleLogout();
                    }}
                  >
                    <LogOut className="h-4 w-4" />
                    Log out
                  </button>
                </div>
              </>
            )}
          </div>
        </header>

        <main className="flex-1 overflow-auto p-4 md:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
