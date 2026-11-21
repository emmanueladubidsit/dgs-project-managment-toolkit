"use client";
import {
  BarChart3, BookOpen, CalendarDays, CheckSquare, FileText, FolderKanban, LayoutDashboard, Library,
  Menu, Mic, Moon, Plus, Settings, Sun, Target,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTheme } from "next-themes";
import { Suspense, use, useState, type ReactNode } from "react";
import { browser } from "react-dom";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { useHealth } from "@/lib/queries";
import { cn } from "@/lib/utils";
import { LoadingState } from "./common";
import { TaskFormDialog } from "./task-form-dialog";

type NavItem = { href: string; label: string; icon: typeof LayoutDashboard; later?: boolean };

// Delivery workflow first; supporting modules after; administration last and separated.
export const NAV: { group: string; items: NavItem[] }[] = [
  {
    group: "Delivery",
    items: [
      { href: "/", label: "Dashboard", icon: LayoutDashboard },
      { href: "/projects", label: "Projects", icon: FolderKanban },
      { href: "/tasks", label: "My Tasks", icon: CheckSquare },
      { href: "/planner", label: "Planner", icon: CalendarDays },
      { href: "/milestones", label: "Milestones", icon: Target },
      { href: "/reports", label: "Reports", icon: BarChart3 },
    ],
  },
  {
    group: "Knowledge",
    items: [
      { href: "/knowledge", label: "Knowledge & Research", icon: BookOpen, later: true },
      { href: "/methodologies", label: "Methodologies & Playbooks", icon: Library, later: true },
      { href: "/documents", label: "Documents & Artefacts", icon: FileText, later: true },
      { href: "/voice", label: "Voice & Writing", icon: Mic, later: true },
    ],
  },
];

function isActive(pathname: string | null, href: string) {
  if (!pathname) return false;
  return href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(`${href}/`);
}

function NavLinks({ pathname, onNavigate }: { pathname: string | null; onNavigate?: () => void }) {
  return (
    <nav aria-label="Main" className="flex flex-1 flex-col gap-6">
      {NAV.map((section) => (
        <div key={section.group}>
          <p className="mb-1 px-3 text-xs font-medium tracking-wide text-muted-foreground uppercase">{section.group}</p>
          <ul className="space-y-0.5">
            {section.items.map(({ href, label, icon: Icon, later }) => {
              const active = isActive(pathname, href);
              return (
                <li key={href}>
                  <Link href={href} onClick={onNavigate} aria-current={active ? "page" : undefined}
                    className={cn("flex items-center gap-2.5 rounded-md px-3 py-1.5 text-sm transition-colors",
                      active ? "bg-primary/10 font-medium text-primary" : "text-sidebar-foreground hover:bg-sidebar-accent")}>
                    <Icon className="size-4 shrink-0" aria-hidden />
                    <span className="truncate">{label}</span>
                    {later && <span className="ml-auto rounded bg-muted px-1.5 text-[10px] text-muted-foreground">Soon</span>}
                  </Link>
                </li>
              );
            })}
          </ul>
        </div>
      ))}
      <div className="mt-auto border-t pt-3">
        <Link href="/admin" onClick={onNavigate} aria-current={isActive(pathname, "/admin") ? "page" : undefined}
          className={cn("flex items-center gap-2.5 rounded-md px-3 py-1.5 text-sm",
            isActive(pathname, "/admin") ? "bg-primary/10 font-medium text-primary" : "text-muted-foreground hover:bg-sidebar-accent")}>
          <Settings className="size-4" aria-hidden /> Administration
        </Link>
      </div>
    </nav>
  );
}

function ActiveNav({ onNavigate }: { onNavigate?: () => void }) {
  return <NavLinks pathname={usePathname()} onNavigate={onNavigate} />;
}

/** usePathname suspends on routes with dynamic params, so the active state streams in. */
function SidebarNav({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <Suspense fallback={<NavLinks pathname={null} onNavigate={onNavigate} />}>
      <ActiveNav onNavigate={onNavigate} />
    </Suspense>
  );
}

function Brand() {
  return (
    <Link href="/" className="flex items-center gap-2 px-3 font-semibold">
      <span className="flex size-7 items-center justify-center rounded-md bg-primary text-xs font-bold text-primary-foreground" aria-hidden>DGS</span>
      <span className="leading-tight">Engineering<br /><span className="text-xs font-normal text-muted-foreground">Workspace</span></span>
    </Link>
  );
}

function ServerStatus() {
  const health = useHealth();
  const ok = health.data?.status === "ok";
  const label = health.isPending ? "Checking server…" : ok ? "Server connected" : "Server unavailable";
  return (
    <span className="flex items-center gap-1.5 text-xs text-muted-foreground" role="status">
      <span className={cn("size-2 rounded-full", health.isPending ? "bg-muted-foreground" : ok ? "bg-success" : "bg-destructive")} aria-hidden />
      <span className="hidden sm:inline">{label}</span>
      <span className="sr-only sm:hidden">{label}</span>
    </span>
  );
}

function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  return (
    <Button variant="ghost" size="icon-sm" aria-label="Toggle dark mode" onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}>
      <Sun className="hidden dark:block" /><Moon className="dark:hidden" />
    </Button>
  );
}

/** Pages depend on "today" and live local data, so they render in the browser only. */
function BrowserOnly({ children }: { children: ReactNode }) {
  use(browser("Workspace pages use the current date and live data from the local API."));
  return <>{children}</>;
}

function TodayLabel() {
  use(browser("Shows the viewer's current date."));
  return <>{new Date().toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "long", year: "numeric" })}</>;
}

export function AppShell({ children }: { children: ReactNode }) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [newTask, setNewTask] = useState(false);
  return (
    <div className="flex min-h-screen">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-50 focus:rounded focus:bg-background focus:px-3 focus:py-2">Skip to content</a>
      <aside className="sticky top-0 hidden h-screen w-60 shrink-0 flex-col gap-6 border-r bg-sidebar py-4 pr-2 pl-2 lg:flex">
        <Brand />
        <SidebarNav />
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-20 flex h-14 items-center gap-3 border-b bg-background/90 px-4 backdrop-blur lg:px-8">
          <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
            <SheetTrigger asChild>
              <Button variant="ghost" size="icon-sm" className="lg:hidden" aria-label="Open navigation"><Menu /></Button>
            </SheetTrigger>
            <SheetContent side="left" className="flex w-64 flex-col gap-6 bg-sidebar p-4">
              <SheetTitle className="sr-only">Navigation</SheetTitle>
              <Brand />
              <SidebarNav onNavigate={() => setMobileOpen(false)} />
            </SheetContent>
          </Sheet>
          <span className="hidden text-sm text-muted-foreground sm:inline">
            <Suspense fallback={null}><TodayLabel /></Suspense>
          </span>
          <div className="ml-auto flex items-center gap-3">
            <ServerStatus />
            <ThemeToggle />
            <Button size="sm" onClick={() => setNewTask(true)}><Plus /> New task</Button>
          </div>
        </header>
        <main id="main" className="mx-auto w-full max-w-7xl flex-1 px-4 py-6 lg:px-8">
          <Suspense fallback={<LoadingState rows={6} />}><BrowserOnly>{children}</BrowserOnly></Suspense>
        </main>
      </div>
      <TaskFormDialog open={newTask} onOpenChange={setNewTask} />
    </div>
  );
}
