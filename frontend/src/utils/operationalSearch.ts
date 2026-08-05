const RESULT_BASE =
  "group block w-full px-4 py-2.5 text-left transition-colors duration-150 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-brand-300";

export function operationalSearchResultClassName(isSelected: boolean): string {
  return isSelected
    ? `${RESULT_BASE} bg-brand-700 text-white`
    : `${RESULT_BASE} bg-transparent hover:bg-brand-600 active:bg-brand-700`;
}

export function operationalSearchTitleClassName(isSelected: boolean): string {
  return isSelected ? "block truncate text-sm font-bold text-white" : "block truncate text-sm font-bold text-ink-950 group-hover:text-white group-active:text-white";
}

export function operationalSearchSecondaryClassName(isSelected: boolean): string {
  return isSelected
    ? "text-brand-100"
    : "text-ink-500 group-hover:text-brand-100 group-active:text-brand-100";
}
