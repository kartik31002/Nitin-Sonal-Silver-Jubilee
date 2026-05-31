import { memo } from "react";
import { Link } from "react-router-dom";
import type { Person } from "../types";
import { resolveAssetUrl } from "../data/loader";

interface FaceCardProps {
  person: Person;
}

function FaceCardBase({ person }: FaceCardProps) {
  return (
    <Link
      to={`/p/${encodeURIComponent(person.id)}`}
      className="face-card group"
      aria-label={`See ${person.photoCount} photos of ${person.name}`}
    >
      <div className="face-card__image">
        <img
          src={resolveAssetUrl(person.faceThumbnail)}
          alt={person.name}
          loading="lazy"
          decoding="async"
          className="h-full w-full object-cover transition group-hover:scale-[1.03]"
          draggable={false}
        />
      </div>
      <div className="flex w-full flex-col items-center gap-0.5">
        <span className="line-clamp-1 text-base font-semibold text-ink-50">
          {person.name}
        </span>
        <span className="text-xs text-ink-300">
          {person.photoCount.toLocaleString()}{" "}
          {person.photoCount === 1 ? "Photo" : "Photos"}
        </span>
      </div>
    </Link>
  );
}

export const FaceCard = memo(FaceCardBase);
