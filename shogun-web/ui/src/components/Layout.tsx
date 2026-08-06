import { useEffect, useState } from 'react';
import { Link, NavLink, Outlet, useLocation, useNavigate, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  BarChart3, Boxes, Brain, ChevronDown, ChevronLeft, ChevronRight,
  Code2, Handshake, History, Kanban, LayoutDashboard, LifeBuoy, LogOut,
  Megaphone, Moon, Package, Settings, Shield, Sun, Users, UserCog, Wallet,
  type LucideIcon,
} from 'lucide-react';
import clsx from 'clsx';
import { departmentsApi, authApi } from '../lib/api';
import { useAuth } from '../lib/auth';
import { DEPARTMENT_CATALOG, type DepartmentKey, type StatusLevel } from '../lib/types';
import logoBlue from '../assets/logos/samurai-logo-blue.png';
import logoDark from '../assets/logos/samurai-logo-dark.png';
import logoLight from '../assets/logos/samurai-logo-light.png';
import mobileLogo from '../assets/logos/samurai-mobile-logo.png';
import mobileLogoLight from '../assets/logos/samurai-mobile-light-logo.png';

const ICONS: Record<string, LucideIcon> = {
  Users, Wallet, Handshake, Megaphone, Shield, LifeBuoy, Code2, Kanban, Boxes, Package,
};

type Theme = 'blue' | 'dark' | 'light';

function getStoredTheme(): Theme {
  const t = (localStorage.getItem('samurai-theme') || 'blue') as Theme;
  if (t === 'blue' || t === 'dark' || t === 'light') return t;
  return 'blue';
}

function applyTheme(theme: Theme) {
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem('samurai-theme', theme);
}
applyTheme(getStoredTheme());

function StatusDot({ status }: { status?: string | null }) {
  const level: StatusLevel =
    status === 'active' || status === 'online' ? 'online'
      : status === 'degraded' || status === 'warning' ? 'degraded'
      : status === 'offline' || status === 'down' ? 'offline'
      : 'unknown';
  return <span className={clsx('sd-status-dot', level)} aria-label={level} />;
}

function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>(() => getStoredTheme());
  const pick = (t: Theme) => { setTheme(t); applyTheme(t); };
  return (
    <div className="sd-theme-seg" role="group" aria-label="Theme">
      <button type="button" className={theme === 'blue' ? 'active' : ''} onClick={() => pick('blue')} aria-label="Blue theme" title="Blue">
        <span style={{ width: '0.7rem', height: '0.7rem', borderRadius: '999px', background: 'linear-gradient(135deg,#1a284d,#0076a8)' }} />
      </button>
      <button type="button" className={theme === 'dark' ? 'active' : ''} onClick={() => pick('dark')} aria-label="Dark theme" title="Dark">
        <Moon size={13} />
      </button>
      <button type="button" className={theme === 'light' ? 'active' : ''} onClick={() => pick('light')} aria-label="Light theme" title="Light">
        <Sun size={13} />
      </button>
    </div>
  );
}

function DepartmentNavItem({
  deptKey, deptName, icon: Icon, color, status, isAdmin, currentPath, currentTab, onNavigate, collapsed,
}: {
  deptKey: string; deptName: string; icon: LucideIcon; color: string; status: string;
  isAdmin: boolean; currentPath: string; currentTab: string; onNavigate: () => void; collapsed: boolean;
}) {
  const isCurrentDept = currentPath === `/department/${deptKey}`;
  const [expanded, setExpanded] = useState(isCurrentDept);

  useEffect(() => { if (isCurrentDept) setExpanded(true); }, [isCurrentDept]);

  if (collapsed) {
    return (
      <NavLink
        to={`/department/${deptKey}?tab=dashboard`}
        onClick={onNavigate}
        className={clsx('sd-nav-item', isCurrentDept && 'active')}
        style={{ borderLeftColor: isCurrentDept ? color : 'transparent' }}
        title={deptName}
      >
        <span className="sd-nav-dept-icon" style={{ backgroundColor: color }}><Icon className="h-3.5 w-3.5" /></span>
      </NavLink>
    );
  }

  const subItems = [
    { id: 'dashboard', label: 'Dashboard', icon: BarChart3 },
    { id: 'chat-history', label: 'Chat History', icon: History },
    { id: 'brain', label: 'Brain', icon: Brain },
    ...(isAdmin ? [{ id: 'settings', label: 'Settings', icon: Settings }] : []),
  ];

  return (
    <div>
      <div className="flex items-center">
        <NavLink
          to={`/department/${deptKey}?tab=dashboard`}
          onClick={onNavigate}
          className={clsx('sd-nav-item flex-1', isCurrentDept && 'active')}
          style={{ borderLeftColor: isCurrentDept ? color : 'transparent' }}
        >
          <span className="sd-nav-dept-icon" style={{ backgroundColor: color }}><Icon className="h-3.5 w-3.5" /></span>
          <span className="sd-nav-label">{deptName}</span>
          <StatusDot status={status} />
        </NavLink>
        <div className="sd-icon-btn !h-7 !w-7" title="Expand">
          <button
            type="button"
            onClick={() => setExpanded((v) => !v)}
            className="flex items-center justify-center h-full w-full"
            aria-label="Toggle sub-menu"
          >
            {expanded ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
          </button>
        </div>
      </div>
      {expanded && (
        <div className="sd-subnav">
          {subItems.map((sub) => {
            const SubIcon = sub.icon;
            const isSubActive = isCurrentDept && (currentTab === sub.id || (!currentTab && sub.id === 'dashboard'));
            return (
              <Link
                key={sub.id}
                to={`/department/${deptKey}?tab=${sub.id}`}
                onClick={onNavigate}
                className={clsx('sd-subnav-item', isSubActive && 'active')}
              >
                <SubIcon className="h-3.5 w-3.5 shrink-0" />
                <span>{sub.label}</span>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const currentTab = searchParams.get('tab') || 'dashboard';
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem('samurai-sidebar-collapsed') === '1');
  const [menuOpen, setMenuOpen] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    localStorage.setItem('samurai-sidebar-collapsed', collapsed ? '1' : '0');
  }, [collapsed]);

  const isDeptPage = location.pathname.startsWith('/department/');
  const currentDeptKey = isDeptPage
    ? (location.pathname.split('/')[2] || '').toLowerCase() as DepartmentKey
    : null;
  const currentDeptMeta = currentDeptKey ? DEPARTMENT_CATALOG[currentDeptKey] : null;
  const currentDeptName = currentDeptKey
    ? currentDeptMeta?.name || (currentDeptKey.charAt(0).toUpperCase() + currentDeptKey.slice(1))
    : '';
  const currentDeptPersona = currentDeptMeta?.persona || '';
  const currentDeptColor = currentDeptMeta?.color || '#6366f1';

  const deptStatusQuery = useQuery({
    queryKey: ['department-status', currentDeptKey],
    queryFn: () => departmentsApi.status(currentDeptKey!),
    enabled: !!currentDeptKey,
    refetchInterval: 30_000,
  });
  const gatewayStatus = deptStatusQuery.data?.gateway_status || 'active';

  const deptsQuery = useQuery({ queryKey: ['departments'], queryFn: () => departmentsApi.list() });
  const accessQuery = useQuery({ queryKey: ['my-access'], queryFn: () => authApi.myAccess(), staleTime: 30_000 });

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const rawDepts = deptsQuery.data || [];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const allDepts: any[] = Array.isArray(rawDepts) ? rawDepts : (rawDepts as { departments?: any[] }).departments || [];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const activeDepts = allDepts.filter((d: any) => d.active || d.status === 'active');
  const isAdmin = user?.role === 'admin' || user?.role === 'owner';
  const canManageStaff = isAdmin || user?.role === 'hr_manager';

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const theme: Theme = (localStorage.getItem('samurai-theme') as Theme) || 'blue';
  const logoSrc = theme === 'light' ? logoLight : theme === 'dark' ? logoDark : logoBlue;
  const mobileLogoSrc = theme === 'light' ? mobileLogoLight : mobileLogo;

  const sidebar = (
    <div className="flex h-full flex-col">
      <div className="sd-sidebar-head">
        <img src={collapsed ? mobileLogoSrc : logoSrc} alt="SamurAI" style={{ width: collapsed ? '2rem' : 'min(230px, 100%)' }} />
      </div>

      <nav className="sd-sidebar-nav">
        <NavLink to="/dashboard" onClick={() => setMobileOpen(false)} className={({ isActive }) => clsx('sd-nav-item', isActive && 'active')}>
          <span className="sd-nav-icon"><LayoutDashboard className="h-4 w-4" /></span>
          {!collapsed && <span className="sd-nav-label">Dashboard</span>}
        </NavLink>
        {canManageStaff && (
          <NavLink to="/staff" onClick={() => setMobileOpen(false)} className={({ isActive }) => clsx('sd-nav-item', isActive && 'active')}>
            <span className="sd-nav-icon"><UserCog className="h-4 w-4" /></span>
            {!collapsed && <span className="sd-nav-label">Staff</span>}
          </NavLink>
        )}

        <div className="sd-sidebar-section">{collapsed ? '' : 'Departments'}</div>
        {activeDepts.length === 0 && !collapsed && (
          <div className="px-3 py-2 text-xs" style={{ color: 'var(--samurai-muted)' }}>No active departments</div>
        )}
        {activeDepts.map((d) => {
          const keyName = (d.key || d.name || '') as DepartmentKey;
          const meta = DEPARTMENT_CATALOG[keyName] || d;
          const Icon = ICONS[meta.icon] || Boxes;
          const deptName = DEPARTMENT_CATALOG[keyName]?.name || (d.name ? d.name.charAt(0).toUpperCase() + d.name.slice(1) : d.key);
          const color = meta.color || d.color || '#6366f1';
          const status = d.status || d.gateway_status;
          return (
            <DepartmentNavItem
              key={d.key || d.name}
              deptKey={d.key || d.name}
              deptName={deptName}
              icon={Icon}
              color={color}
              status={status}
              isAdmin={isAdmin}
              currentPath={location.pathname}
              currentTab={currentTab}
              onNavigate={() => setMobileOpen(false)}
              collapsed={collapsed}
            />
          );
        })}
      </nav>

      <div className="sd-sidebar-footer">
        <div className="sd-user-tile">
          <div className="sd-user-avatar">{(user?.name || user?.email || '?').charAt(0).toUpperCase()}</div>
          <div className="sd-user-meta">
            <div className="sd-user-name">{user?.name || 'User'}</div>
            <div className="sd-user-email">{user?.email}</div>
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <div className="sd-app-frame">
      <div className={clsx('sd-sidebar-shell', collapsed && 'collapsed')} style={{ position: 'relative' }}>
        {sidebar}
        <button
          type="button"
          className="sd-sidebar-collapse"
          onClick={() => setCollapsed((v) => !v)}
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          title={collapsed ? 'Expand' : 'Collapse'}
        >
          {collapsed ? <ChevronRight className="h-3.5 w-3.5" /> : <ChevronLeft className="h-3.5 w-3.5" />}
        </button>
      </div>

      {mobileOpen && (
        <div className="fixed inset-0 z-40 flex md:hidden" style={{ background: 'rgba(0,0,0,0.45)' }} onClick={() => setMobileOpen(false)}>
          <div className="sd-sidebar-shell" style={{ width: '15rem', position: 'relative' }} onClick={(e) => e.stopPropagation()}>
            {sidebar}
          </div>
        </div>
      )}

      <div className="sd-main-column">
        <header className="sd-topbar">
          <div className="sd-topbar-left">
            {isDeptPage && currentDeptKey ? (
              <>
                <span className="sd-nav-dept-icon" style={{ backgroundColor: currentDeptColor, width: '1.75rem', height: '1.75rem' }}>
                  {(currentDeptName || '?').charAt(0)}
                </span>
                <span className="sd-topbar-title">{currentDeptName}</span>
                {currentDeptPersona && <span className="sd-topbar-persona">{currentDeptPersona}</span>}
                <StatusDot status={gatewayStatus} />
                <span className="sd-topbar-persona">{`Gateway · ${gatewayStatus}`}</span>
              </>
            ) : (
              <>
                <span className="sd-topbar-kicker">Shogun OS</span>
                <span className="sd-topbar-title">{location.pathname.startsWith('/staff') ? 'Staff' : 'Command Portal'}</span>
              </>
            )}
          </div>

          <div className="sd-topbar-right">
            <ThemeToggle />
            <div className="sd-menu">
              <button
                type="button"
                className="sd-icon-btn"
                onClick={() => setMenuOpen((v) => !v)}
                aria-label="Account menu"
              >
                <ChevronDown className="h-4 w-4" />
              </button>
              {menuOpen && (
                <>
                  <button type="button" className="fixed inset-0 z-40 cursor-default" aria-label="Close menu" onClick={() => setMenuOpen(false)} />
                  <div className="sd-menu-pop">
                    <div className="sd-menu-head">
                      <div className="sd-menu-head-name">{user?.name}</div>
                      <div className="sd-menu-head-email">{user?.email}</div>
                    </div>
                    <button
                      type="button"
                      className="sd-menu-item"
                      onClick={() => { setMenuOpen(false); void handleLogout(); }}
                    >
                      <LogOut className="h-4 w-4" /> Log out
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        </header>

        <main className={clsx('sd-page', isDeptPage && 'sd-page-tight')}>
          <Outlet />
        </main>
      </div>
    </div>
  );
}