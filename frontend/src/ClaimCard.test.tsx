// @vitest-environment jsdom
import { it, expect, vi } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { ClaimCard } from "./ClaimCard";
it("keeps unsupported claims visibly withheld and opens the actual source citation", () => {
  const onEvidence = vi.fn();
  const citation = {
    chunk_id: "c1",
    document_id: "d1",
    document_name: "report.pdf",
    page_number: 2,
    quote: "The trial enrolled 120 adults.",
    integrity: true,
    relation: "insufficient",
  };
  render(
    <ClaimCard
      claim={{
        id: "c1",
        text: "The trial enrolled 300 adults.",
        verdict: "contradicted",
        explanation: "The source says 120.",
        citations: [citation],
        counter_evidence: [],
      }}
      index={0}
      onEvidence={onEvidence}
    />,
  );
  expect(screen.getByText("Contradicted · withheld")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: /report.pdf/ }));
  expect(onEvidence).toHaveBeenCalledWith(citation);
  cleanup();
});
it("renders document-supplied HTML as inert text", () => {
  const content = "<img src=x onerror=alert(1)>";
  const { container } = render(
    <ClaimCard
      claim={{
        id: "c2",
        text: content,
        verdict: "insufficient",
        explanation: "No support",
        citations: [],
        counter_evidence: [],
      }}
      index={1}
      onEvidence={() => {}}
    />,
  );
  expect(screen.getByText(content)).toBeTruthy();
  expect(container.querySelector("img")).toBeNull();
  cleanup();
});
