import type { Metadata } from "next";
import { Suspense } from "react";
import { PageHeader } from "@/components/shell/PageHeader";
import { Badge } from "@/components/ui/Panel";
import { LoadingSkeleton } from "@/components/ui/States";
import { InventoryPlanner } from "@/features/planner/InventoryPlanner";

export const metadata: Metadata = { title: "Inventory Planner" };

export default function Page() {
  return (
    <>
      <PageHeader eyebrow="Hypothetical simulation" title="Inventory Planner"
                  description={<>Pick a curated series and validation origin, set your own replenishment and cost assumptions, and run the
                    unchanged Phase 5 inventory engine. Every run uses the saved sales of that 28-day validation window and the saved
                    fixed-origin forecasts; it is a what-if analysis, not a forecast of real outcomes.</>}
                  badges={<><Badge tone="caution">Costs in hypothetical NCU</Badge><Badge tone="teal">Verified Python engine</Badge><Badge>Bounded, rate-limited runs</Badge></>} />
      <Suspense fallback={<LoadingSkeleton label="Loading planner" rows={4} />}>
        <InventoryPlanner />
      </Suspense>
    </>
  );
}
