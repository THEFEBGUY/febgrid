import { describe, expect, it } from "vitest";

import {
  AI_CAPABILITIES_HEADING,
  displayAIModel,
  displayAIProvider,
  displayAIText,
} from "./aiDisplay";

describe("AI display labels", () => {
  it("brands the Groq provider without changing its internal value", () => {
    const provider = "groq";

    expect(displayAIProvider(provider)).toBe("FebGuyAI");
    expect(provider).toBe("groq");
  });

  it("brands the configured model without changing its internal value", () => {
    const model = "llama-3.3-70b-versatile";

    expect(displayAIModel(model)).toBe("FebGuyAI Model");
    expect(model).toBe("llama-3.3-70b-versatile");
  });

  it("sanitizes provider status copy for display", () => {
    expect(displayAIText("Groq is configured with llama-3.3-70b-versatile.")).toBe(
      "FebGuyAI is configured with FebGuyAI Model.",
    );
  });

  it("exposes the new safeguards heading", () => {
    expect(AI_CAPABILITIES_HEADING).toBe("FebGuyAI Capabilities & Safeguards");
  });
});
