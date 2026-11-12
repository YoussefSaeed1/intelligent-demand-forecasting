import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { MobileNavigation, Sidebar } from "@/components/shell/Navigation";
import { StatusFooter } from "@/components/shell/StatusFooter";
import { MetricCard } from "@/components/ui/MetricCard";
import { ScientificNotice } from "@/components/ui/ScientificNotice";
import { ErrorState, LoadingSkeleton } from "@/components/ui/States";
import { ApiError, apiGet, apiPath, simulate } from "@/lib/api/client";
import { DASH, date, ncu, pct, relativeChange, signed, units4 } from "@/lib/format";
import { PATTERNS } from "@/lib/labels";
import { resolveSelection } from "@/lib/selection";
import type { ResearchResponse } from "@/lib/api/types";
import { fixture, mockFetch, on, readRoutes, setUrl } from "./harness";

const params = (query: string) => new URLSearchParams(query);

describe("formatting (presentation only)", () => {
  it("formats per the UI specification and never turns undefined into zero", () => {
    expect(units4(6.49213)).toBe("6.4921");
    expect(pct(0.98383)).toBe("98.38%");
    expect(ncu(6038.4425)).toBe("6,038.44 NCU");
    expect(signed(-217, 0)).toBe("−217");
    expect(signed(12.5, 1, "%")).toBe("+12.5%");
    for (const value of [null, undefined, Number.NaN]) {
      expect(units4(value)).toBe(DASH);
      expect(pct(value)).toBe(DASH);
      expect(ncu(value)).toBe(DASH);
    }
    expect(relativeChange(5, 0)).toBeNull();
    expect(relativeChange(90, 100)).toBeCloseTo(-0.1);
    expect(date("2017-08-14")).toBe("14 Aug 2017");
  });
});

describe("selection resolution (URL state)", () => {
  it("defaults to Store Item origin 4 and a Phase 5 representative series", () => {
    expect(resolveSelection(params(""))).toMatchObject({ dataset: "store_item", series: "store_item|1:11",
                                                         origin: "store_item|4", corrected: false });
  });
  it("derives the dataset from a series key", () => {
    expect(resolveSelection(params("series=m5%7C4%3ACA_1FOODS_1_001"))).toMatchObject({ dataset: "m5", origin: "m5|4" });
  });
  it("corrects incompatible and malformed combinations instead of sending them", () => {
    const mixed = resolveSelection(params("dataset=m5&series=store_item%7C1%3A11&origin=store_item%7C2"));
    expect(mixed).toMatchObject({ dataset: "m5", series: "m5|4:CA_1FOODS_1_001", origin: "m5|4", corrected: true });
    expect(resolveSelection(params("origin=store_item%7C9")).corrected).toBe(true);
    expect(resolveSelection(params("series=';drop table")).series).toBe("store_item|1:11");
    expect(resolveSelection(params("pattern=bogus")).pattern).toBeNull();
    expect(resolveSelection(params("models=seasonal_naive,bogus")).models).toEqual(["seasonal_naive"]);
  });
});

describe("typed API client", () => {
  it("builds deterministic paths", () => {
    expect(apiPath("/series", { q: undefined, dataset: "m5", limit: 25, cursor: "" }))
      .toBe("/api/v1/series?dataset=m5&limit=25");
    expect(apiPath("/forecasts", { series: "store_item|1:11", origin: "store_item|4" }))
      .toBe("/api/v1/forecasts?origin=store_item%7C4&series=store_item%7C1%3A11");
  });
  it("memoises successful reads and surfaces server errors without internals", async () => {
    const { fn } = mockFetch([
      on("/api/v1/datasets", () => ({ body: fixture("datasets") })),
      on("/api/v1/series", () => ({ status: 429, body: { error: "rate_limited", message: "Too many requests; please retry later", requestId: "req-12345678" } })),
    ]);
    await apiGet(apiPath("/datasets"));
    await apiGet(apiPath("/datasets"));
    expect(fn).toHaveBeenCalledTimes(1);
    const error = await apiGet(apiPath("/series", { dataset: "m5" })).catch((e: unknown) => e) as ApiError;
    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ status: 429, code: "rate_limited", requestId: "req-12345678", retryable: true });
  });
  it("maps a network failure on simulate to a retryable error", async () => {
    mockFetch([() => { throw new TypeError("fetch failed"); }]);
    const error = await simulate({ seriesKey: "store_item|1:11", originKey: "store_item|4", policies: ["selected_ml"],
                                   scenario: { leadDays: 7, reviewDays: 1, bufferDays: 3, initialCoverDays: 7, holdingCost: 1,
                                               shortageCost: 10, fixedOrderCost: 1, variableOrderCost: 0, terminalCost: 0,
                                               variabilityMultiplier: 1 } }).catch((e: unknown) => e) as ApiError;
    expect(error.code).toBe("network_error");
    expect(error.retryable).toBe(true);
  });
  it("uses the same demand-pattern keys as the curated database", () => {
    const research = fixture<ResearchResponse>("research");
    expect(PATTERNS.map((p) => [p.key, p.label]))
      .toEqual(research.demandPatterns.map((p) => [p.patternKey, p.demandPattern]));
  });
});

describe("application shell", () => {
  it("renders the five destinations and marks the current page", () => {
    setUrl("/planner");
    render(<Sidebar />);
    const nav = screen.getByRole("navigation", { name: "Primary" });
    const links = within(nav).getAllByRole("link");
    expect(links.map((l) => l.textContent)).toEqual([
      expect.stringContaining("Executive Overview"), expect.stringContaining("Forecast Explorer"),
      expect.stringContaining("Inventory Planner"), expect.stringContaining("Scenario Comparison"),
      expect.stringContaining("Research & Methodology"),
    ]);
    expect(within(nav).getByRole("link", { current: "page" })).toHaveProperty("textContent", expect.stringContaining("Inventory Planner"));
    expect(screen.getByText(/hypothetical NCU/)).toBeTruthy();
  });
  it("opens and closes the mobile drawer from the keyboard", async () => {
    const user = userEvent.setup();
    render(<MobileNavigation />);
    const toggle = screen.getByRole("button", { name: "Open navigation" });
    await user.click(toggle);
    expect(toggle.getAttribute("aria-expanded")).toBe("true");
    expect(screen.getAllByRole("link").length).toBeGreaterThanOrEqual(5);
    await user.keyboard("{Escape}");
    expect(screen.getByRole("button", { name: "Open navigation" }).getAttribute("aria-expanded")).toBe("false");
  });
  it("shows export version and engine reachability from /health", async () => {
    mockFetch(readRoutes());
    render(<StatusFooter />);
    await waitFor(() => expect(screen.getByTestId("engine-status").textContent).toBe("reachable"));
    expect(screen.getByText("2026-11-12.1")).toBeTruthy();
  });
});

describe("shared components", () => {
  it("labels notices with text, not colour alone", () => {
    render(<ScientificNotice kind="hypothetical">Costs are NCU.</ScientificNotice>);
    expect(screen.getByRole("note", { name: "Hypothetical simulation" }).textContent).toContain("Costs are NCU.");
  });
  it("renders metric, loading and error states", async () => {
    const retried: string[] = [];
    render(<>
      <MetricCard label="Fill rate" value="98.38%" context="Validation origins" />
      <LoadingSkeleton label="Loading chart" />
      <ErrorState error={new ApiError(502, "engine_unavailable", "Engine down", [], "req-abcdef12")} onRetry={() => retried.push("x")} />
    </>);
    expect(screen.getByText("98.38%")).toBeTruthy();
    expect(screen.getByRole("status").textContent).toContain("Loading chart");
    expect(screen.getByRole("alert").textContent).toContain("req-abcdef12");
    await userEvent.click(screen.getByRole("button", { name: /retry/i }));
    expect(retried).toHaveLength(1);
  });
});
