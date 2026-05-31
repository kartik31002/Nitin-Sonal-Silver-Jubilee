import { Suspense, lazy } from "react";
import { Route, Routes } from "react-router-dom";
import HomePage from "./pages/HomePage";
import { usePeople } from "./data/usePeople";

const PersonPage = lazy(() => import("./pages/PersonPage"));

function LoadingShell() {
  return (
    <div className="container-page flex min-h-[60vh] items-center justify-center py-24 text-ink-300">
      <div className="flex flex-col items-center gap-3">
        <div className="h-10 w-10 animate-spin rounded-full border-2 border-ink-700 border-t-brand-500" />
        <p className="text-sm">Loading photos...</p>
      </div>
    </div>
  );
}

function ErrorShell({ message }: { message: string }) {
  return (
    <div className="container-page py-24 text-center">
      <h2 className="text-2xl font-semibold">Could not load the gallery</h2>
      <p className="mt-3 text-sm text-ink-300">{message}</p>
      <p className="mt-2 text-xs text-ink-400">
        Make sure <code>public/data/people.json</code> exists. Run{" "}
        <code>uv run photo-finder deploy</code> from the processor folder.
      </p>
    </div>
  );
}

export default function App() {
  const state = usePeople();

  if (state.status === "loading") {
    return <LoadingShell />;
  }

  if (state.status === "error" || state.data === null) {
    return <ErrorShell message={state.error?.message ?? "Unknown error"} />;
  }

  const data = state.data;

  return (
    <Suspense fallback={<LoadingShell />}>
      <Routes>
        <Route path="/" element={<HomePage data={data} />} />
        <Route path="/p/:personId" element={<PersonPage data={data} />} />
        <Route path="*" element={<HomePage data={data} />} />
      </Routes>
    </Suspense>
  );
}
