import { useCallback, useEffect, useState } from "react";

export type AsyncState<T> =
  | { status: "loading" }
  | { status: "error"; error: Error }
  | { status: "success"; data: T };

export function useAsync<T>(fn: () => Promise<T>, deps: unknown[] = []) {
  const [state, setState] = useState<AsyncState<T>>({ status: "loading" });

  const run = useCallback(() => {
    let cancelled = false;
    setState({ status: "loading" });
    fn()
      .then((data) => !cancelled && setState({ status: "success", data }))
      .catch((error: Error) => !cancelled && setState({ status: "error", error }));
    return () => { cancelled = true; };
  }, deps); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => run(), [run]);
  return { ...state, reload: run };
}
