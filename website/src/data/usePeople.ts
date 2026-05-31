import { useEffect, useState } from "react";
import { loadPeople } from "./loader";
import type { PeoplePayload } from "../types";

interface PeopleState {
  status: "loading" | "ready" | "error";
  data: PeoplePayload | null;
  error: Error | null;
}

export function usePeople(): PeopleState {
  const [state, setState] = useState<PeopleState>({
    status: "loading",
    data: null,
    error: null,
  });

  useEffect(() => {
    let cancelled = false;
    loadPeople()
      .then((data) => {
        if (cancelled) return;
        setState({ status: "ready", data, error: null });
      })
      .catch((err: Error) => {
        if (cancelled) return;
        setState({ status: "error", data: null, error: err });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return state;
}
