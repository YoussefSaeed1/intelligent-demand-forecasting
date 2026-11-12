import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";
import { clearApiCache } from "@/lib/api/client";
import { NoopLink, router, setUrl, usePathnameDouble, useSearchParamsDouble } from "./harness";

vi.mock("next/navigation", () => ({
  usePathname: () => usePathnameDouble(),
  useSearchParams: () => useSearchParamsDouble(),
  useRouter: () => router,
}));

vi.mock("next/link", () => ({ default: NoopLink }));

// jsdom lacks these; components only use them for layout measurement.
class ResizeObserverDouble {
  observe() {}
  unobserve() {}
  disconnect() {}
}
vi.stubGlobal("ResizeObserver", ResizeObserverDouble);

afterEach(() => {
  cleanup();
  clearApiCache();
  vi.unstubAllGlobals();
  vi.stubGlobal("ResizeObserver", ResizeObserverDouble);
  router.replace.mockClear();
  router.push.mockClear();
  setUrl("/");
});
