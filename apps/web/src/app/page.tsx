import { PageHeader } from "@/components/shell/PageHeader";
import { Badge } from "@/components/ui/Panel";
import { OverviewView } from "@/features/overview/OverviewView";

export default function Page() {
  return (
    <>
      <PageHeader eyebrow="Cairo University · Postgraduate Data Science graduation project" title="Executive Overview"
                  description={<>Does machine-learning forecasting improve on simple baselines for daily retail demand, and what would that
                    mean for inventory under explicitly assumed conditions? This application presents the frozen research evidence for two
                    public datasets and lets you run the verified simulation engine on your own hypothetical scenarios.</>}
                  badges={<>
                    <Badge tone="teal">Validation origins only</Badge>
                    <Badge tone="caution">Costs in hypothetical NCU</Badge>
                    <Badge>Final holdout sealed</Badge>
                  </>} />
      <OverviewView />
    </>
  );
}
