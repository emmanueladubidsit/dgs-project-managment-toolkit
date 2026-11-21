"use client";
// Reusable page-level building blocks: headers, badges, progress, empty/loading/error states.
import { AlertTriangle, Inbox, RefreshCw } from "lucide-react";
import type { ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { errorMessage } from "@/lib/api";
import { PRIORITY_LABEL, STATUS_LABEL } from "@/lib/format";
import type { Priority, Progress, TaskStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

export function PageHeader({ title, description, actions }: { title: string; description?: ReactNode; actions?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div className="min-w-0">
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        {description && <p className="mt-1 text-sm text-muted-foreground">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}

export function Section({ title, actions, children, className }: { title: ReactNode; actions?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={cn("rounded-xl border bg-card p-4", className)}>
      <div className="mb-3 flex items-center justify-between gap-2">
        <h2 className="text-sm font-semibold">{title}</h2>
        {actions}
      </div>
      {children}
    </section>
  );
}

const STATUS_CLASS: Record<TaskStatus, string> = {
  todo: "bg-status-todo/12 text-status-todo border-status-todo/30",
  in_progress: "bg-status-in-progress/12 text-status-in-progress border-status-in-progress/30",
  blocked: "bg-status-blocked/12 text-status-blocked border-status-blocked/30",
  in_review: "bg-status-in-review/12 text-status-in-review border-status-in-review/30",
  completed: "bg-status-completed/12 text-status-completed border-status-completed/30",
  cancelled: "bg-status-cancelled/12 text-status-cancelled border-status-cancelled/30 line-through",
};

export const STATUS_DOT: Record<TaskStatus, string> = {
  todo: "bg-status-todo",
  in_progress: "bg-status-in-progress",
  blocked: "bg-status-blocked",
  in_review: "bg-status-in-review",
  completed: "bg-status-completed",
  cancelled: "bg-status-cancelled",
};

export function StatusBadge({ status }: { status: TaskStatus }) {
  return (
    <span className={cn("inline-flex items-center gap-1.5 rounded-md border px-1.5 py-0.5 text-xs font-medium whitespace-nowrap", STATUS_CLASS[status])}>
      <span className={cn("size-1.5 rounded-full", STATUS_DOT[status])} aria-hidden />
      {STATUS_LABEL[status]}
    </span>
  );
}

const PRIORITY_CLASS: Record<Priority, string> = {
  critical: "text-priority-critical",
  high: "text-priority-high",
  medium: "text-priority-medium",
  low: "text-priority-low",
};
const PRIORITY_BARS: Record<Priority, number> = { critical: 4, high: 3, medium: 2, low: 1 };

export function PriorityBadge({ priority, showLabel = true }: { priority: Priority; showLabel?: boolean }) {
  return (
    <span className={cn("inline-flex items-center gap-1 text-xs font-medium whitespace-nowrap", PRIORITY_CLASS[priority])} title={`${PRIORITY_LABEL[priority]} priority`}>
      <span className="flex items-end gap-px" aria-hidden>
        {[1, 2, 3, 4].map((i) => (
          <span key={i} className={cn("w-[3px] rounded-sm bg-current", i > PRIORITY_BARS[priority] && "opacity-20")} style={{ height: 3 + i * 2 }} />
        ))}
      </span>
      {showLabel ? PRIORITY_LABEL[priority] : <span className="sr-only">{PRIORITY_LABEL[priority]} priority</span>}
    </span>
  );
}

export function ProgressBar({ value, className, label }: { value: number; className?: string; label?: string }) {
  return (
    <div
      className={cn("h-1.5 w-full overflow-hidden rounded-full bg-muted", className)}
      role="progressbar"
      aria-valuenow={Math.round(value)}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label={label ?? "Progress"}
    >
      <div className="h-full rounded-full bg-primary transition-[width]" style={{ width: `${Math.min(100, Math.max(0, value))}%` }} />
    </div>
  );
}

/** Progress with its calculation explained on hover/focus — progress is never a black box. */
export function ExplainedProgress({ progress, className }: { progress: Progress; className?: string }) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <button type="button" className={cn("flex w-full items-center gap-2 text-left", className)} aria-label={`Progress ${progress.percent}%. ${progress.explanation}`}>
          <ProgressBar value={progress.percent} />
          <span className="w-10 shrink-0 text-right text-xs tabular-nums text-muted-foreground">{Math.round(progress.percent)}%</span>
        </button>
      </TooltipTrigger>
      <TooltipContent className="max-w-xs">{progress.explanation}</TooltipContent>
    </Tooltip>
  );
}

export function EmptyState({ title, description, action, icon }: { title: string; description?: ReactNode; action?: ReactNode; icon?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-dashed px-6 py-10 text-center">
      <div className="mb-3 text-muted-foreground">{icon ?? <Inbox className="size-6" aria-hidden />}</div>
      <p className="font-medium">{title}</p>
      {description && <p className="mt-1 max-w-md text-sm text-muted-foreground">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  return (
    <div role="alert" className="flex flex-col items-center rounded-xl border border-destructive/30 bg-destructive/5 px-6 py-8 text-center">
      <AlertTriangle className="mb-2 size-6 text-destructive" aria-hidden />
      <p className="font-medium">This could not be loaded</p>
      <p className="mt-1 text-sm text-muted-foreground">{errorMessage(error)}</p>
      {onRetry && (
        <Button variant="outline" size="sm" className="mt-4" onClick={onRetry}>
          <RefreshCw /> Try again
        </Button>
      )}
    </div>
  );
}

export function LoadingState({ rows = 4 }: { rows?: number }) {
  return (
    <div className="space-y-2" aria-busy="true" aria-label="Loading">
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} className="h-10 w-full" />
      ))}
    </div>
  );
}

/** Renders loading / error / content for a TanStack query. */
export function QueryView<T>({ query, children, rows }: {
  query: { data: T | undefined; isPending: boolean; error: unknown; refetch: () => unknown };
  children: (data: T) => ReactNode;
  rows?: number;
}) {
  if (query.isPending) return <LoadingState rows={rows} />;
  if (query.error || query.data === undefined) return <ErrorState error={query.error} onRetry={() => query.refetch()} />;
  return <>{children(query.data)}</>;
}

export const NONE = "__none__";
