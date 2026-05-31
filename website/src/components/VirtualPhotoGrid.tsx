import {
  memo,
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import type { PersonPhoto } from "../types";
import { PhotoTile } from "./PhotoTile";

interface VirtualPhotoGridProps {
  photos: PersonPhoto[];
}

interface Metrics {
  containerWidth: number;
  columns: number;
  cellWidth: number;
  cellHeight: number;
  gap: number;
}

const TARGET_CELL_WIDTH = 220;
const MIN_COLUMNS = 2;
const MAX_COLUMNS = 6;
const GAP = 12;
const OVERSCAN_ROWS = 4;

function computeMetrics(width: number): Metrics {
  const usableWidth = Math.max(width, 240);
  const rawColumns = Math.round(usableWidth / TARGET_CELL_WIDTH);
  const columns = Math.min(MAX_COLUMNS, Math.max(MIN_COLUMNS, rawColumns));
  const totalGap = GAP * (columns - 1);
  const cellWidth = Math.floor((usableWidth - totalGap) / columns);
  const cellHeight = cellWidth;
  return {
    containerWidth: usableWidth,
    columns,
    cellWidth,
    cellHeight,
    gap: GAP,
  };
}

function useElementWidth<T extends HTMLElement>() {
  const ref = useRef<T | null>(null);
  const [width, setWidth] = useState(0);

  useLayoutEffect(() => {
    const node = ref.current;
    if (!node) return;
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setWidth(entry.contentRect.width);
      }
    });
    observer.observe(node);
    setWidth(node.clientWidth);
    return () => observer.disconnect();
  }, []);

  return [ref, width] as const;
}

function VirtualPhotoGridBase({ photos }: VirtualPhotoGridProps) {
  const [hostRef, width] = useElementWidth<HTMLDivElement>();
  const [scrollY, setScrollY] = useState(0);
  const [viewportHeight, setViewportHeight] = useState(
    typeof window === "undefined" ? 800 : window.innerHeight,
  );

  useEffect(() => {
    const onScroll = () => setScrollY(window.scrollY);
    const onResize = () => setViewportHeight(window.innerHeight);
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onResize);
    };
  }, []);

  const metrics = useMemo(() => computeMetrics(width || 0), [width]);

  const rowCount = useMemo(() => {
    if (!metrics.columns) return 0;
    return Math.ceil(photos.length / metrics.columns);
  }, [metrics.columns, photos.length]);

  const rowHeight = metrics.cellHeight + metrics.gap;
  const totalHeight = rowCount * rowHeight - (rowCount > 0 ? metrics.gap : 0);

  const [hostTop, setHostTop] = useState(0);
  useLayoutEffect(() => {
    if (!hostRef.current) return;
    const update = () => {
      if (hostRef.current) {
        const rect = hostRef.current.getBoundingClientRect();
        setHostTop(rect.top + window.scrollY);
      }
    };
    update();
    window.addEventListener("resize", update);
    return () => window.removeEventListener("resize", update);
  }, [hostRef]);

  const visibleStart = Math.max(0, scrollY - hostTop);
  const visibleEnd = visibleStart + viewportHeight;
  const firstRow = Math.max(0, Math.floor(visibleStart / rowHeight) - OVERSCAN_ROWS);
  const lastRow = Math.min(
    rowCount,
    Math.ceil(visibleEnd / rowHeight) + OVERSCAN_ROWS,
  );

  const openPhoto = useCallback((photo: PersonPhoto) => {
    window.open(photo.driveUrl, "_blank", "noopener,noreferrer");
  }, []);

  const tiles: JSX.Element[] = [];
  if (metrics.columns > 0) {
    for (let row = firstRow; row < lastRow; row += 1) {
      for (let col = 0; col < metrics.columns; col += 1) {
        const index = row * metrics.columns + col;
        if (index >= photos.length) break;
        const photo = photos[index];
        const top = row * rowHeight;
        const left = col * (metrics.cellWidth + metrics.gap);
        tiles.push(
          <PhotoTile
            key={`${photo.thumbnail}_${index}`}
            photo={photo}
            style={{
              position: "absolute",
              top,
              left,
              width: metrics.cellWidth,
              height: metrics.cellHeight,
            }}
            onClick={openPhoto}
          />,
        );
      }
    }
  }

  return (
    <div ref={hostRef} className="relative w-full">
      <div
        className="relative"
        style={{ height: totalHeight, minHeight: 200 }}
        aria-label={`${photos.length} photos`}
      >
        {tiles}
      </div>
    </div>
  );
}

export const VirtualPhotoGrid = memo(VirtualPhotoGridBase);
