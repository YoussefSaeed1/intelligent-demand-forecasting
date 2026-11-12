import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ForecastExplorer } from "@/features/forecasts/ForecastExplorer";
import { OverviewView } from "@/features/overview/OverviewView";
import { AuditFindings, FinalHoldoutReported, Limitations, Provenance, SelectionTrials } from "@/features/research/ResearchData";
import { costRelativeByOrigin, datasetFindings, originMeanMae } from "@/lib/analytics";
import type { AggregateResponse, ResearchResponse, StudyResponse } from "@/lib/api/types";
import { currentUrl, fixture, mockFetch, on, readRoutes, router, setUrl } from "./harness";

const agg = (d: string) => fixture<AggregateResponse>(`aggregate_${d}`);
const study = (d: string) => fixture<StudyResponse>(`study_${d}`);

describe("analytics helpers reproduce saved evidence", () => {
  it("equal-origin mean MAE equals every saved Phase 4 leaderboard score that exists for these models", () => {
    const research = fixture<ResearchResponse>("research");
    const trial = (id: string) => research.modelSelectionTrials.rows.find((t) => t.trialId === id)!.validationMacroMae;
    expect(originMeanMae(agg("store_item").rows, "selected_ml")).toBeCloseTo(trial("store_item_lightgbm_00"), 10);
    expect(originMeanMae(agg("store_item").rows, "seasonal_naive")).toBeCloseTo(trial("store_item_seasonal_naive_reference"), 10);
    expect(originMeanMae(agg("m5").rows, "selected_ml")).toBeCloseTo(trial("m5_random_forest_02"), 10);
    expect(originMeanMae(agg("m5").rows, "moving_average_28")).toBeCloseTo(trial("m5_moving_average_28_reference"), 10);
    expect(originMeanMae(agg("m5").rows, "seasonal_naive")).toBeCloseTo(trial("m5_seasonal_naive_reference"), 10);
  });
  it("shows the Store Item final-origin cost reversal and the M5 cost disadvantage honestly", () => {
    const si = costRelativeByOrigin(study("store_item").perOrigin, "base", "moving_average_28");
    expect(si.slice(0, 3).every((v) => v! < 0)).toBe(true);
    expect(si[3]).toBeGreaterThan(0);
    const findings = datasetFindings("M5", agg("m5").rows, study("m5").perOrigin, study("m5").pooled).map((f) => f.text);
    expect(findings).toContain("M5 (base scenario): selected ML's mean hypothetical cost is higher than MA28 when pooled over origins, and lower at 0 of 4 origins.");
  });
});

describe("Executive Overview (U-01 data binding)", () => {
  it("renders headline KPIs, both baselines, the reversal caveat and limitations from the API", async () => {
    mockFetch(readRoutes());
    render(<OverviewView />);
    await waitFor(() => expect(screen.getByTestId("kpi-mae-store_item").textContent).toContain("6.3080"));
    expect(screen.getByTestId("kpi-mae-store_item").textContent).toMatch(/vs MA28 \(9\.5383\)/);
    expect(screen.getByTestId("kpi-mae-m5").textContent).toContain("1.0201");
    expect(screen.getByTestId("kpi-cost-store_item").textContent).toContain("6,038.44 NCU");
    expect(screen.getByTestId("kpi-cost-m5").textContent).toMatch(/\+0\.9% vs MA28/);
    expect(screen.getByTestId("kpi-series-m5").textContent).toContain("30,490");
    expect(screen.getAllByText(/Store Item cost reversal/).length).toBe(1);
    const table = screen.getByTestId("policy-table");
    expect(within(table).getByText("Low-stock comparator with lower fill rate")).toBeTruthy();
    expect(within(table).getAllByRole("row")).toHaveLength(5);
    expect(screen.getByTestId("findings").children.length).toBe(8);
    expect(screen.getByTestId("overview-limitations").textContent).toContain("not realised financial savings");
  });
  it("switches the policy table dataset", async () => {
    mockFetch(readRoutes());
    render(<OverviewView />);
    await waitFor(() => screen.getByTestId("policy-table"));
    await userEvent.click(screen.getByRole("radio", { name: "M5" }));
    await waitFor(() => expect(within(screen.getByTestId("policy-table")).getByText("223.82")).toBeTruthy());
  });
  it("shows a retryable error state when a read fails", async () => {
    mockFetch([on("/api/v1/inventory/study", () => ({ status: 503, body: { error: "not_configured", message: "x", requestId: "req-00000001" } })),
               ...readRoutes()]);
    render(<OverviewView />);
    await waitFor(() => expect(screen.getAllByRole("alert").length).toBeGreaterThan(0));
    expect(screen.getAllByRole("alert")[0].textContent).toContain("not configured");
  });
});

describe("Forecast Explorer (U-02, U-03)", () => {
  it("renders the default representative series with three models and population context", async () => {
    mockFetch([...readRoutes(), on("/api/v1/series/store_item%7C1%3A11", () => ({ body: { meta: {}, series: {
      seriesKey: "store_item|1:11", datasetKey: "store_item", seriesId: "1:11", storeId: "1", itemId: "1", patternKey: "smooth",
      demandPattern: "Smooth", patternDescription: "Regular demand", trainingPrefixMeanUnits: 19.8, retrospectiveSparseGroup: "Not applicable" }, origins: [] } }))]);
    setUrl("/forecasts");
    render(<ForecastExplorer />);
    await waitFor(() => expect(screen.getByTestId("metrics-table")).toBeTruthy());
    const rows = within(screen.getByTestId("metrics-table")).getAllByRole("row");
    expect(rows).toHaveLength(4);
    expect(rows[1].textContent).toContain("Selected ML");
    expect(screen.getByTestId("forecast-chart")).toBeTruthy();
    expect(screen.getByRole("link", { name: /Open in Inventory Planner/ }).getAttribute("href"))
      .toBe("/planner?series=store_item%7C1%3A11&origin=store_item%7C4");
    await waitFor(() => expect(screen.getByTestId("population-table")).toBeTruthy());
    expect(screen.queryByText(/Exploratory demo subset/)).toBeNull();
  });
  it("switching dataset resets series and origin in the URL and shows the M5 subset caveat", async () => {
    mockFetch([...readRoutes(), () => ({ status: 404, body: { error: "not_found", message: "Unknown series" } })]);
    setUrl("/forecasts?origin=store_item%7C2");
    render(<ForecastExplorer />);
    await userEvent.click(screen.getByRole("radio", { name: "M5" }));
    expect(router.replace).toHaveBeenCalled();
    expect(currentUrl().searchParams.get("dataset")).toBe("m5");
    expect(currentUrl().searchParams.get("series")).toBe("m5|4:CA_1FOODS_1_001");
    expect(currentUrl().searchParams.get("origin")).toBe("m5|4");
    expect(await screen.findByText(/Exploratory demo subset/)).toBeTruthy();
  });
  it("model toggles update the URL and keep at least one model", async () => {
    mockFetch([...readRoutes(), () => ({ status: 404, body: { error: "not_found", message: "Unknown series" } })]);
    setUrl("/forecasts");
    render(<ForecastExplorer />);
    await userEvent.click(screen.getByRole("checkbox", { name: /MA28/ }));
    expect(currentUrl().searchParams.get("models")).toBe("selected_ml,seasonal_naive");
    await userEvent.click(screen.getByRole("checkbox", { name: /Seasonal Naive/ }));
    const ml = screen.getByRole("checkbox", { name: /Selected ML/ }) as HTMLInputElement;
    expect(ml.disabled).toBe(true);
  });
  it("flags and corrects an incompatible link instead of querying it", async () => {
    const { calls } = mockFetch([...readRoutes(), () => ({ status: 404, body: { error: "not_found", message: "Unknown series" } })]);
    setUrl("/forecasts?dataset=m5&series=store_item%7C1%3A11&origin=store_item%7C1");
    render(<ForecastExplorer />);
    expect(screen.getByText(/Link adjusted/)).toBeTruthy();
    await waitFor(() => expect(calls.some((c) => c.url.pathname === "/api/v1/forecasts")).toBe(true));
    const forecastCall = calls.find((c) => c.url.pathname === "/api/v1/forecasts")!;
    expect(forecastCall.url.searchParams.get("origin")).toBe("m5|4");
    expect(forecastCall.url.searchParams.get("series")).toBe("m5|4:CA_1FOODS_1_001");
  });
  it("exports only the displayed, bounded rows as CSV", async () => {
    mockFetch([...readRoutes(), () => ({ status: 404, body: { error: "not_found", message: "Unknown series" } })]);
    const created: Blob[] = [];
    vi.stubGlobal("URL", Object.assign(URL, { createObjectURL: (b: Blob) => { created.push(b); return "blob:x"; }, revokeObjectURL: () => {} }));
    setUrl("/forecasts");
    render(<ForecastExplorer />);
    const button = await screen.findByRole("button", { name: /CSV/ });
    await waitFor(() => expect((button as HTMLButtonElement).disabled).toBe(false));
    await userEvent.click(button);
    const text = await new Promise<string>((resolve) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result));
      reader.readAsText(created[0]);
    });
    const lines = text.trim().split("\n");
    expect(lines[0]).toMatch(/not the final holdout/);
    expect(lines).toHaveLength(2 + 84 + 28);
    expect(lines[1]).toBe("series_id,origin,date,window,units,selected_ml_forecast,moving_average_28_forecast,seasonal_naive_forecast");
  });
});

describe("Research & Methodology", () => {
  it("renders trials, reported holdout, audit findings, limitations and provenance from the API", async () => {
    mockFetch(readRoutes());
    render(<><SelectionTrials /><FinalHoldoutReported /><AuditFindings /><Limitations /><Provenance /></>);
    await waitFor(() => expect(screen.getByTestId("limitations").children).toHaveLength(8));
    expect(within(screen.getByTestId("audit-findings")).getAllByRole("row")).toHaveLength(13);
    expect(within(screen.getByTestId("trials-store_item")).getAllByRole("row")).toHaveLength(15);
    expect(within(screen.getByTestId("trials-m5")).getAllByRole("row")).toHaveLength(14);
    expect(screen.getByText(/reported as recorded; not a new evaluation/)).toBeTruthy();
    expect(within(screen.getByTestId("final-holdout")).getAllByRole("row")).toHaveLength(9);
    expect(screen.getByTestId("provenance").textContent).toContain("a71ab187aaad10eb3df4ec550ef2bd99b9542064619b35c7629da14eedcb3fdb");
  });
});
