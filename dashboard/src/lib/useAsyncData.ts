"use client";

import { useEffect, useState } from "react";

type AsyncDataState<T> = {
  data: T | null;
  error: unknown;
  key: string;
  status: "pending" | "success" | "error";
};

export function useAsyncData<T>(
  key: string,
  load: () => Promise<T>,
): { data: T | null; error: unknown; loading: boolean } {
  const [state, setState] = useState<AsyncDataState<T>>({
    data: null,
    error: null,
    key,
    status: "pending",
  });

  useEffect(() => {
    let cancelled = false;

    load()
      .then((data) => {
        if (!cancelled) {
          setState({ data, error: null, key, status: "success" });
        }
      })
      .catch((error: unknown) => {
        console.error(error);
        if (!cancelled) {
          setState({ data: null, error, key, status: "error" });
        }
      });

    return () => {
      cancelled = true;
    };
  }, [key, load]);

  const isCurrent = state.key === key;

  return {
    data: isCurrent ? state.data : null,
    error: isCurrent ? state.error : null,
    loading: !isCurrent || state.status === "pending",
  };
}
