import { useCallback, useState } from "react";
import { ApiError } from "../api/client";

const UNEXPECTED_MESSAGE = "Something went wrong. Please try again.";

/**
 * Wraps an async action with loading and error state.
 * `run` resolves to the action's result, or to undefined if it failed (the error is then in `error`).
 * Pass a stable function, such as one from `api`, so `run` keeps a stable identity.
 */
export function useAction<A extends unknown[], R>(action: (...args: A) => Promise<R>) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = useCallback(
    async (...args: A): Promise<R | undefined> => {
      setLoading(true);
      setError(null);
      try {
        return await action(...args);
      } catch (cause) {
        if (!(cause instanceof ApiError)) {
          console.error("unexpected error", cause);
        }
        setError(cause instanceof ApiError ? cause.message : UNEXPECTED_MESSAGE);
        return undefined;
      } finally {
        setLoading(false);
      }
    },
    [action],
  );

  return { run, loading, error };
}
