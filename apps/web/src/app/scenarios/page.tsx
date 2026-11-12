import type { Metadata } from "next";
import { Suspense } from "react";
import { PageHeader } from "@/components/shell/PageHeader";
import { Badge } from "@/components/ui/Panel";
import { LoadingSkeleton } from "@/components/ui/States";
import { ScenarioComparison } from "@/features/scenarios/ScenarioComparison";

export const metadata: Metadata = { title: "Scenario Comparison" };

export default function Page() {
  return (
    <>
      <PageHeader eyebrow="Exploratory scenario analysis" title="Scenario Comparison"
                  description={<>The frozen Phase 5 study: four inventory policies under 17 one-at-a-time scenarios, simulated for every
                    research series at each of the four validation origins. Use it to see how cost and service trade-offs move with the
                    assumptions and across origins.</>}
                  badges={<><Badge tone="teal">Full research populations</Badge><Badge tone="caution">Costs in hypothetical NCU</Badge><Badge>17 scenarios · 4 shared origins</Badge></>} />
      <Suspense fallback={<LoadingSkeleton label="Loading scenarios" chart rows={3} />}>
        <ScenarioComparison />
      </Suspense>
    </>
  );
}
