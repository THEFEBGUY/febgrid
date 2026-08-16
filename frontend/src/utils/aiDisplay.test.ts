import { describe, expect, it } from "vitest";

import {
  AI_CAPABILITIES_HEADING,
  displayAIModel,
  displayAIProvider,
  displayAIText,
} from "./aiDisplay";

describe("aiDisplay", () => {
  it("formats AI provider", () => {
    expect(displayAIProvider("groq")).toBe("FebGuyAI");
    expect(displayAIProvider("anthropic")).toBe("Anthropic");
    expect(displayAIProvider(null)).toBe("AI");
  });

  it("formats AI model", () => {
    const model = "openai/gpt-oss-120b";
    expect(displayAIModel(model)).toBe("FebGuyAI Model");
    expect(displayAIModel("gpt-4")).toBe("gpt-4");
    expect(displayAIModel(null)).toBe("Not configured");
  });

  it("filters AI text", () => {
    expect(displayAIText("Groq is configured with openai/gpt-oss-120b.")).toBe(
      "FebGuyAI is configured with FebGuyAI Model."
    );
    expect(displayAIText(null)).toBeNull();
  });

  it("exposes the new safeguards heading", () => {
    expect(AI_CAPABILITIES_HEADING).toBe("FebGuyAI Capabilities & Safeguards");
  });
});
