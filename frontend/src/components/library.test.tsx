import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { renderWithProviders } from "@/test/utils";
import { VerificationBadge, VerificationNotice } from "./knowledge";
import { ClassificationBadge } from "./methodology";
import { Recorder } from "./recorder";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));

describe("knowledge verification is always explicit", () => {
  it("labels every status in plain English", () => {
    renderWithProviders(<><VerificationBadge value="verified_tested" /><VerificationBadge value="ai_suggestion" /></>);
    expect(screen.getByText("Verified and tested")).toBeInTheDocument();
    expect(screen.getByText("AI suggestion — awaiting review")).toBeInTheDocument();
  });
  it("warns that AI suggestions must not be relied on", () => {
    renderWithProviders(<VerificationNotice value="ai_suggestion" />);
    expect(screen.getByText(/Do not rely on it until a person has verified it/)).toBeInTheDocument();
  });
  it("shows no notice for verified knowledge", () => {
    const { container } = renderWithProviders(<VerificationNotice value="verified_docs" />);
    expect(container).toBeEmptyDOMElement();
  });
});

describe("methodology deliverables", () => {
  it("labels classifications", () => {
    renderWithProviders(<><ClassificationBadge value="mandatory" /><ClassificationBadge value="not_applicable" /></>);
    expect(screen.getByText("Mandatory")).toBeInTheDocument();
    expect(screen.getByText("Not applicable")).toBeInTheDocument();
  });
});

describe("Recorder", () => {
  it("explains clearly when the browser cannot record", async () => {
    renderWithProviders(<Recorder onTranscribe={vi.fn()} busy={false} />);
    await userEvent.click(screen.getByRole("button", { name: /Record/ }));
    expect(screen.getByRole("alert")).toHaveTextContent("This browser cannot record audio");
  });
  it("is disabled with a reason when no transcription provider exists", () => {
    renderWithProviders(<Recorder onTranscribe={vi.fn()} busy={false} disabledReason="Recording needs a transcription provider." />);
    expect(screen.getByRole("button", { name: /Record/ })).toBeDisabled();
    expect(screen.getByText("Recording needs a transcription provider.")).toBeInTheDocument();
  });
});
