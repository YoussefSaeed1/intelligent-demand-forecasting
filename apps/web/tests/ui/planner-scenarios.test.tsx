import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { niceTicks } from "@/components/charts/core";
import { InventoryPlanner } from "@/features/planner/InventoryPlanner";
import { OverviewView } from "@/features/overview/OverviewView";
import { ScenarioComparison } from "@/features/scenarios/ScenarioComparison";
import type { SimulateRequest, SimulateResponse, StudyResponse } from "@/lib/api/types";
import { scanCopy } from "../copy-gate.mjs";
import { currentUrl, fixture, mockFetch, on, readRoutes, setUrl } from "./harness";

const runButton = () => screen.getByRole("button", { name: /Run simulation|Running the Phase 5 engine/ });

it("chart domains enclose the displayed data without clipping peaks", () => {
  for (const [min, max] of [[0, 166], [-0.3, 0.83], [0.91, 0.99], [0, 0]]) {
    const ticks = niceTicks(min, max);
    expect(ticks[0]).toBeLessThanOrEqual(min);
    expect(ticks[ticks.length - 1]).toBeGreaterThanOrEqual(max);
  }
});

describe("U-05 copy gate", () => {
  it("approves only negated savings caveats and rejects positive claims", () => {
    expect(scanCopy("Hypothetical NCU; simulated differences are not realised savings. Not realised financial savings.").pass).toBe(true);
    expect(scanCopy("Hypothetical NCU. ML delivers savings of 5%.").violations).toHaveLength(1);
    expect(scanCopy("hypothetical NCU. The optimal policy").pass).toBe(false);
    expect(scanCopy("Inventory Optimisation and hypothetical NCU").pass).toBe(true);
    expect(scanCopy("Cost 12 NCU").ncuWithoutHypothetical).toBe(true);
    expect(scanCopy("hypothetical NCU. Fixed reorder point is cheapest").ropWithoutComparatorLabel).toBe(true);
  });
});

describe("Inventory Planner (fixture-based component tests; real engine runs are in tests/api.test.ts and the browser QA)", () => {
  it("submits bounded inputs to the server proxy and binds summaries, deltas, breakdown and trajectories", async () => {
    const response = fixture<SimulateResponse>("simulate_store_item");
    const { calls } = mockFetch([on("/api/v1/planner/simulate", () => ({ body: response, delayMs: 50 }), "POST"), ...readRoutes()]);
    setUrl("/planner?series=store_item%7C1%3A11&origin=store_item%7C4");
    render(<InventoryPlanner />);
    expect(screen.getByText("Matches published scenario: base")).toBeTruthy();
    await userEvent.click(runButton());
    expect(screen.getByRole("button", { name: /Running the Phase 5 engine/ })).toBeTruthy();
    const table = await screen.findByTestId("planner-results");
    expect(within(table).getAllByRole("row")).toHaveLength(5);
    const ml = response.policies.find((p) => p.policyKey === "selected_ml")!;
    expect(screen.getByTestId("planner-card-selected_ml").textContent)
      .toContain(`${ml.summary.totalCost.toLocaleString("en-GB")} NCU`);
    expect(screen.getByTestId("planner-card-fixed_reorder_point").textContent).toContain("Low-stock comparator with lower fill rate");
    expect(screen.getByTestId("planner-deltas").textContent).toMatch(/Selected ML: [−+±]/);
    expect(screen.getByTestId("study-reference").textContent).toContain("Published scenario: base");
    for (const id of ["inventory-chart", "trajectory-chart", "cost-breakdown"]) expect(screen.getByTestId(id)).toBeTruthy();
    const body = calls.find((c) => c.method === "POST")!.body as SimulateRequest;
    expect(body).toMatchObject({ seriesKey: "store_item|1:11", originKey: "store_item|4", scenario: { leadDays: 7, shortageCost: 10 } });
    expect(body.policies).toHaveLength(4);
    expect(Object.keys(body)).not.toContain("demand");
    expect(scanCopy(document.body.textContent ?? "").pass).toBe(true);
  });

  it("rejects out-of-bounds input with a field message and hides results for changed inputs", async () => {
    mockFetch([on("/api/v1/planner/simulate", () => ({ body: fixture("simulate_store_item") }), "POST"), ...readRoutes()]);
    setUrl("/planner?series=store_item%7C1%3A11&origin=store_item%7C4");
    render(<InventoryPlanner />);
    await userEvent.click(runButton());
    await screen.findByTestId("planner-results");
    const lead = screen.getByLabelText("Lead time (days)");
    await userEvent.clear(lead);
    await userEvent.type(lead, "15");
    expect(screen.queryByTestId("planner-results")).toBeNull();
    expect(screen.getByText("Enter a number from 0 to 14 (whole days).")).toBeTruthy();
    expect((runButton() as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByText("Custom hypothetical scenario")).toBeTruthy();
    await userEvent.click(screen.getByRole("button", { name: /Reset to Phase 5 base/ }));
    expect((runButton() as HTMLButtonElement).disabled).toBe(false);
  });

  it("sends only the selected policies and keeps at least one", async () => {
    const { calls } = mockFetch([on("/api/v1/planner/simulate", () => ({ status: 502, body: { error: "engine_unavailable", message: "x" } }), "POST"), ...readRoutes()]);
    setUrl("/planner");
    render(<InventoryPlanner />);
    for (const name of [/Fixed ROP/, /Seasonal Naive/, /MA28/]) await userEvent.click(screen.getByRole("checkbox", { name }));
    expect((screen.getByRole("checkbox", { name: /Selected ML/ }) as HTMLInputElement).disabled).toBe(true);
    await userEvent.click(runButton());
    await screen.findByText("Simulation unavailable");
    expect((calls.find((c) => c.method === "POST")!.body as SimulateRequest).policies).toEqual(["selected_ml"]);
  });

  it("on engine unavailability shows an honest error, retry, and clearly labelled precomputed results", async () => {
    mockFetch([on("/api/v1/planner/simulate", () => ({ status: 502, body: { error: "engine_unavailable", message: "The simulation engine is unavailable" } }), "POST"),
               ...readRoutes()]);
    setUrl("/planner?series=store_item%7C1%3A11&origin=store_item%7C4");
    render(<InventoryPlanner />);
    await userEvent.click(runButton());
    expect(await screen.findByText("Simulation unavailable")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Retry" })).toBeTruthy();
    expect(screen.queryByTestId("planner-results")).toBeNull();
    expect(screen.getByRole("note", { name: "Precomputed fallback" }).textContent).toContain("Your inputs equal the published base scenario");
    const fallback = await screen.findByTestId("fallback-table");
    expect(within(fallback).getAllByRole("row")).toHaveLength(5);
  });
});

describe("Scenario Comparison (fixture-based component tests)", () => {
  it("binds pooled and per-origin saved values, sensitivity, origin grid and the Store Item reversal", async () => {
    mockFetch(readRoutes());
    setUrl("/scenarios");
    render(<ScenarioComparison />);
    const table = await screen.findByTestId("scenario-pooled");
    expect(within(table).getAllByRole("row")).toHaveLength(5);
    expect(table.textContent).toContain("6,038.44");
    expect(within(screen.getByTestId("scenario-origins")).getAllByRole("row")).toHaveLength(17);
    expect(within(screen.getByTestId("scenario-matrix")).getAllByRole("row")).toHaveLength(18);
    expect(within(screen.getByTestId("origin-grid-table")).getAllByRole("row")).toHaveLength(18);
    expect(screen.getByTestId("sensitivity-chart")).toBeTruthy();
    expect(screen.getByText(/Store Item final-origin cost reversal/)).toBeTruthy();
    expect(scanCopy(document.body.textContent ?? "").pass).toBe(true);
  });

  it("scenario and origin selections are URL state and change the displayed values", async () => {
    mockFetch(readRoutes());
    setUrl("/scenarios");
    render(<ScenarioComparison />);
    await screen.findByTestId("scenario-pooled");
    const data = fixture<StudyResponse>("study_store_item");
    const next = data.pooled.find((r) => r.scenarioKey === "lead_long" && r.policyKey === "selected_ml")!;
    await userEvent.selectOptions(screen.getByRole("combobox", { name: "Scenario" }), "lead_long");
    expect(currentUrl().searchParams.get("scenario")).toBe("lead_long");
    await waitFor(() => expect(screen.getByTestId("scenario-pooled").textContent)
      .toContain(next.meanCostNcu!.toLocaleString("en-GB", { minimumFractionDigits: 2, maximumFractionDigits: 2 })));
    await userEvent.click(screen.getByRole("radio", { name: "Origin 4" }));
    expect(currentUrl().searchParams.get("origin")).toBe("store_item|4");
    const o4 = data.perOrigin.find((r) => r.scenarioKey === "lead_long" && r.policyKey === "selected_ml" && r.fold === 4)!;
    await waitFor(() => expect(screen.getByTestId("scenario-pooled").textContent)
      .toContain(o4.meanCostNcu!.toLocaleString("en-GB", { minimumFractionDigits: 2, maximumFractionDigits: 2 })));
  });

  it("passes pattern to the API and handles empty saved populations without invented values", async () => {
    const { calls } = mockFetch([on("/api/v1/inventory/study", () => ({ body: { meta: {}, pooled: [], perOrigin: [], policies: [] } }))]);
    setUrl("/scenarios?pattern=all_zero");
    render(<ScenarioComparison />);
    expect(await screen.findByText("No saved study episodes")).toBeTruthy();
    expect(calls[0].url.searchParams.get("pattern")).toBe("all_zero");
  });
});

describe("Overview copy", () => {
  it("passes the U-05 copy gate with its mandatory negated caveats", async () => {
    mockFetch(readRoutes());
    render(<OverviewView />);
    await screen.findByTestId("policy-table");
    await waitFor(() => expect(screen.getByTestId("overview-limitations")).toBeTruthy());
    const result = scanCopy(document.body.textContent ?? "");
    expect(result.violations).toEqual([]);
    expect(result.approvedCaveats).toBeGreaterThan(0);
    expect(result.pass).toBe(true);
  });
});
