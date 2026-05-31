import { useMemo } from "react";
import { Link, useParams } from "react-router-dom";
import { VirtualPhotoGrid } from "../components/VirtualPhotoGrid";
import type { PeoplePayload } from "../types";
import { resolveAssetUrl } from "../data/loader";

interface PersonPageProps {
  data: PeoplePayload;
}

export default function PersonPage({ data }: PersonPageProps) {
  const { personId } = useParams<{ personId: string }>();

  const person = useMemo(() => {
    if (!personId) return null;
    const decoded = decodeURIComponent(personId);
    return data.people.find((p) => p.id === decoded) ?? null;
  }, [personId, data.people]);

  if (!person) {
    return (
      <div className="container-page py-16 text-center">
        <h2 className="text-2xl font-semibold">Person not found</h2>
        <p className="mt-2 text-ink-300">
          We could not find anyone with that ID.
        </p>
        <Link to="/" className="btn-primary mt-6">
          Back to all faces
        </Link>
      </div>
    );
  }

  return (
    <div className="container-page py-8 sm:py-12">
      <Link
        to="/"
        className="btn-ghost mb-6 inline-flex items-center gap-2"
        aria-label="Back to all faces"
      >
        <span aria-hidden>&larr;</span>
        Back
      </Link>

      <header className="flex flex-col items-center gap-4 text-center sm:flex-row sm:items-center sm:justify-start sm:text-left">
        <img
          src={resolveAssetUrl(person.faceThumbnail)}
          alt={person.name}
          className="h-20 w-20 rounded-full border border-ink-700 object-cover sm:h-24 sm:w-24"
          draggable={false}
        />
        <div>
          <h1 className="text-3xl font-bold sm:text-4xl">{person.name}</h1>
          <p className="mt-1 text-sm text-ink-300">
            {person.photoCount.toLocaleString()}{" "}
            {person.photoCount === 1 ? "photo" : "photos"}
          </p>
        </div>
      </header>

      <section className="mt-8" aria-label={`Photos of ${person.name}`}>
        <VirtualPhotoGrid photos={person.photos} />
      </section>

      {person.photos.length === 0 && (
        <p className="mt-10 text-center text-ink-400">
          No photos linked yet.
        </p>
      )}

      <p className="mt-10 text-center text-xs text-ink-400">
        Tap a photo to open the original on Google Drive.
      </p>
    </div>
  );
}
