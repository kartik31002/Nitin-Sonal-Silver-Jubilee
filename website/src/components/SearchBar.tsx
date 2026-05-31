import { memo } from "react";

interface SearchBarProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}

function SearchBarBase({ value, onChange, placeholder }: SearchBarProps) {
  return (
    <label className="relative block w-full">
      <span className="sr-only">Search by name</span>
      <svg
        aria-hidden="true"
        viewBox="0 0 20 20"
        fill="currentColor"
        className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-ink-400"
      >
        <path
          fillRule="evenodd"
          d="M9 3.5a5.5 5.5 0 1 0 3.484 9.785l3.115 3.115a1 1 0 0 0 1.415-1.415l-3.115-3.115A5.5 5.5 0 0 0 9 3.5Zm-3.5 5.5a3.5 3.5 0 1 1 7 0 3.5 3.5 0 0 1-7 0Z"
          clipRule="evenodd"
        />
      </svg>
      <input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        type="search"
        placeholder={placeholder ?? "Search by name"}
        className="block w-full rounded-full border border-ink-700 bg-ink-900/80 py-3 pl-12 pr-4 text-base text-ink-50 placeholder:text-ink-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/60"
      />
    </label>
  );
}

export const SearchBar = memo(SearchBarBase);
