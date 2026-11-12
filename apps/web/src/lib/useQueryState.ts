"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback } from "react";

/** URL-backed filter state: shareable links, back/forward support, no global store. */
export function useQueryState() {
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const update = useCallback((changes: Record<string, string | null | undefined>) => {
    const next = new URLSearchParams(params.toString());
    for (const [key, value] of Object.entries(changes)) {
      if (value === null || value === undefined || value === "") next.delete(key);
      else next.set(key, value);
    }
    next.sort();
    const search = next.toString();
    router.replace(search ? `${pathname}?${search}` : pathname, { scroll: false });
  }, [params, pathname, router]);

  return { params, update };
}
