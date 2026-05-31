import { memo } from "react";
import type { CSSProperties } from "react";
import type { PersonPhoto } from "../types";
import { resolveAssetUrl } from "../data/loader";

interface PhotoTileProps {
  photo: PersonPhoto;
  style: CSSProperties;
  onClick: (photo: PersonPhoto) => void;
}

function PhotoTileBase({ photo, style, onClick }: PhotoTileProps) {
  return (
    <button
      type="button"
      style={style}
      onClick={() => onClick(photo)}
      className="group absolute overflow-hidden rounded-xl border border-ink-800 bg-ink-900 transition hover:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 focus:ring-offset-ink-950"
      aria-label="Open full-size photo in Google Drive"
    >
      <img
        src={resolveAssetUrl(photo.thumbnail)}
        alt=""
        loading="lazy"
        decoding="async"
        className="h-full w-full object-cover transition duration-300 group-hover:scale-[1.04]"
        draggable={false}
      />
    </button>
  );
}

export const PhotoTile = memo(PhotoTileBase);
