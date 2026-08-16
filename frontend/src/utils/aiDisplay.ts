import { formatLabel } from "./format";

export const AI_CAPABILITIES_HEADING = "FebGuyAI Capabilities & Safeguards";

export function displayAIProvider(provider: string | null | undefined): string {
  if (!provider) return "AI";
  return provider.toLowerCase() === "groq" ? "FebGuyAI" : formatLabel(provider);
}

export function displayAIModel(model: string | null | undefined): string {
  if (!model) return "Not configured";
  return model.toLowerCase() === "openai/gpt-oss-120b" ? "FebGuyAI Model" : model;
}

export function displayAIText(value: string | null | undefined): string | null {
  if (!value) return null;
  return value
    .replace(/openai\/gpt-oss-120b/gi, "FebGuyAI Model")
    .replace(/\bGroq\b/gi, "FebGuyAI");
}
