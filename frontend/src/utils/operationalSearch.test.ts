import { describe, expect, it } from "vitest";

import {
  operationalSearchResultClassName,
  operationalSearchSecondaryClassName,
  operationalSearchTitleClassName,
} from "./operationalSearch";

describe("Operational Search interaction styles", () => {
  it("uses a high-contrast hover and pressed surface", () => {
    const resultClasses = operationalSearchResultClassName(false);

    expect(resultClasses).toContain("hover:bg-brand-600");
    expect(resultClasses).toContain("active:bg-brand-700");
    expect(resultClasses).not.toContain("hover:bg-brand-50");
    expect(operationalSearchTitleClassName(false)).toContain("group-hover:text-white");
    expect(operationalSearchSecondaryClassName(false)).toContain("group-hover:text-brand-100");
  });

  it("keeps keyboard-selected results readable and visually distinct", () => {
    const resultClasses = operationalSearchResultClassName(true);

    expect(resultClasses).toContain("bg-brand-700");
    expect(resultClasses).toContain("text-white");
    expect(resultClasses).toContain("focus-visible:outline-brand-300");
    expect(operationalSearchTitleClassName(true)).toContain("text-white");
    expect(operationalSearchSecondaryClassName(true)).toContain("text-brand-100");
  });
});
