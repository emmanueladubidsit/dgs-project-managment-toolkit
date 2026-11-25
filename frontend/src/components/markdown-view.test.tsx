import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MarkdownView } from "./markdown-view";

describe("MarkdownView", () => {
  it("renders headings, grouped lists and emphasis", () => {
    render(<MarkdownView source={"# Weekly report\n\n## Achievements\n\n### Project A\n\n- Mon 23 Nov: **Shipped** login\n- Added `api.py`\n\n_No risks recorded this week._"} />);
    expect(screen.getByRole("heading", { name: "Weekly report" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Achievements" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Project A" })).toBeInTheDocument();
    expect(screen.getAllByRole("listitem")).toHaveLength(2);
    expect(screen.getByText("Shipped").tagName).toBe("STRONG");
    expect(screen.getByText("api.py").tagName).toBe("CODE");
    expect(screen.getByText("No risks recorded this week.").tagName).toBe("EM");
  });

  it("never renders HTML from the content", () => {
    const { container } = render(<MarkdownView source={'<img src=x onerror="alert(1)"> <script>bad()</script>'} />);
    expect(container.querySelector("img, script")).toBeNull();
    expect(container.textContent).toContain("<img src=x");
  });

  it("keeps code fences as preformatted text", () => {
    const { container } = render(<MarkdownView source={"```python\nprint('hi')\n```"} />);
    expect(container.querySelector("pre code")?.textContent).toBe("print('hi')");
  });
});
