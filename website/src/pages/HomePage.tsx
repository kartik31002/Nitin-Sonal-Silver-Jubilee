import { useDeferredValue, useMemo, useState } from "react";
import { FaceCard } from "../components/FaceCard";
import { SearchBar } from "../components/SearchBar";
import type { PeoplePayload, Person } from "../types";

interface HomePageProps {
  data: PeoplePayload;
}

function matches(person: Person, query: string): boolean {
  if (!query) return true;
  const haystack = `${person.name} ${person.id}`.toLowerCase();
  return haystack.includes(query.toLowerCase());
}

export default function HomePage({ data }: HomePageProps) {
  const [query, setQuery] = useState("");
  const deferred = useDeferredValue(query);

  const filtered = useMemo(() => {
    const q = deferred.trim();
    if (!q) return data.people;
    return data.people.filter((p) => matches(p, q));
  }, [data.people, deferred]);

  const totalPhotos = useMemo(
    () => data.people.reduce((acc, person) => acc + person.photoCount, 0),
    [data.people],
  );

  return (
    <div className="container-page py-10 sm:py-14">
      <header className="mx-auto flex max-w-3xl flex-col items-center gap-4 text-center">
        <span className="rounded-full border border-ink-700 bg-ink-900/60 px-3 py-1 text-xs uppercase tracking-[0.16em] text-ink-300">
          Find Me
        </span>
        <h1 className="text-balance text-3xl font-bold leading-tight sm:text-5xl">
          {data.eventTitle}
        </h1>
        <p className="text-balance text-base text-ink-300 sm:text-lg">
          Who are you? Tap your face to see every photo you appear in.
        </p>
        <p className="text-xs text-ink-400">
          {data.people.length.toLocaleString()} people
          {" \u2022 "}
          {totalPhotos.toLocaleString()} photos
        </p>
      </header>

      <div className="mx-auto mt-8 max-w-xl">
        <SearchBar value={query} onChange={setQuery} placeholder="Search by name..." />
      </div>

      <section
        className="mt-10 grid gap-4 sm:gap-5"
        style={{
          gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))",
        }}
        aria-label="Faces"
      >
        {filtered.map((person) => (
          <FaceCard key={person.id} person={person} />
        ))}
      </section>

      {filtered.length === 0 && (
        <p className="mt-12 text-center text-ink-400">
          No one matches &ldquo;{deferred}&rdquo;.
        </p>
      )}
    </div>
  );
}
