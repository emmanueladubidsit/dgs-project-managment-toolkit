import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { renderWithProviders } from "@/test/utils";
import { ErrorState, ExplainedProgress, PriorityBadge, ProgressBar, StatusBadge } from "./common";

describe("common components", () => {
  it("labels statuses in British English", () => {
    renderWithProviders(<><StatusBadge status="in_review" /><StatusBadge status="todo" /></>);
    expect(screen.getByText("In Review")).toBeInTheDocument();
    expect(screen.getByText("To Do")).toBeInTheDocument();
  });
  it("gives priority an accessible name even without a visible label", () => {
    renderWithProviders(<PriorityBadge priority="critical" showLabel={false} />);
    expect(screen.getByText("Critical priority")).toBeInTheDocument();
  });
  it("exposes progress to assistive technology and clamps values", () => {
    renderWithProviders(<ProgressBar value={140} label="Build" />);
    const bar = screen.getByRole("progressbar", { name: "Build" });
    expect(bar).toHaveAttribute("aria-valuenow", "140");
    expect(bar.firstElementChild).toHaveStyle({ width: "100%" });
  });
  it("explains how progress was calculated", () => {
    renderWithProviders(<ExplainedProgress progress={{ percent: 25, method: "weighted", explanation: "25% across 2 task(s)",
      tasks_counted: 2, tasks_completed: 0, tasks_excluded: 0, total_weight: 4 }} />);
    expect(screen.getByRole("button", { name: /Progress 25%\. 25% across 2 task/ })).toBeInTheDocument();
  });
  it("shows the API message and retries", async () => {
    const retry = vi.fn();
    renderWithProviders(<ErrorState error={new Error("Project not found.")} onRetry={retry} />);
    expect(screen.getByRole("alert")).toHaveTextContent("Project not found.");
    await userEvent.click(screen.getByRole("button", { name: /Try again/ }));
    expect(retry).toHaveBeenCalledOnce();
  });
});
