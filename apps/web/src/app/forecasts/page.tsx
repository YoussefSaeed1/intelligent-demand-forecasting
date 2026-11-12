import type { Metadata } from "next";
import { Suspense } from "react";
import { PageHeader } from "@/components/shell/PageHeader";
import { Badge } from "@/components/ui/Panel";
import { LoadingSkeleton } from "@/components/ui/States";
import { ForecastExplorer } from "@/features/forecasts/ForecastExplorer";

export const metadata: Metadata = { title: "Forecast Explorer" };

export default function Page() {
  return (
    <>
      <PageHeader eyebrow="Validation evidence" title="Forecast Explorer"
                  description={<>Compare the frozen selected ML model with the MA28 and Seasonal Naive baselines on any curated series. Each
                    forecast was made once at a validation origin for the next 28 days and is shown against the actual saved sales.</>}
                  badges={<><Badge tone="teal">Store Item: all 500 series</Badge><Badge tone="brand">M5: 300 curated of 30,490</Badge></>} />
      <Suspense fallback={<LoadingSkeleton label="Loading explorer" chart rows={3} />}>
        <ForecastExplorer />
      </Suspense>
    </>
  );
}
