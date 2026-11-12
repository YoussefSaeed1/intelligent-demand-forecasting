"use client";

import { useCallback, useEffect, useState } from "react";
import { ApiError, apiGet } from "./client";

export interface ApiState<T> {
  data: T | undefined;
  error: ApiError | undefined;
  loading: boolean;
  reload: () => void;
}

/**
 * Fetches one API path; `null` means "nothing to load yet" (for example, no series selected). Results are tied
 * to the path that produced them, so a fast filter change can never display a stale response.
 */
export function useApi<T>(path: string | null): ApiState<T> {
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState<{ key: string | null; data?: T; error?: ApiError }>({ key: null });
  const key = path === null ? null : `${attempt}|${path}`;

  useEffect(() => {
    if (path === null) return;
    const controller = new AbortController();
    apiGet<T>(path, { signal: controller.signal }).then(
      (data) => setState({ key, data }),
      (error: unknown) => {
        if (controller.signal.aborted) return;
        setState({ key, error: error instanceof ApiError ? error
          : new ApiError(0, "unexpected", "The response could not be read") });
      },
    );
    return () => controller.abort();
  }, [path, key]);

  const reload = useCallback(() => setAttempt((n) => n + 1), []);
  const current = key !== null && state.key === key;
  return {
    data: current ? state.data : undefined,
    error: current ? state.error : undefined,
    loading: key !== null && !current,
    reload,
  };
}
