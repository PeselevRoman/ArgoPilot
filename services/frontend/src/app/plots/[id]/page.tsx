import { Suspense } from "react";
import { ErrorNotice } from "@/components/error-notice";
import { PlanList } from "@/components/plan-list";
import { RecommendationCard } from "@/components/recommendation-card";
import { cropLabel, formatNumber } from "@/lib/format";
import { describeError } from "@/lib/messages";
import { decodePlotId } from "@/lib/plot-id";
import { getPlan } from "@/lib/planner";
import { todaysRecommendation } from "@/lib/recommendation";
import { getPlot } from "@/lib/registry";

async function PlotContent({ params }: { params: Promise<{ id: string }> }) {
  const { id: rawId } = await params;
  const id = decodePlotId(rawId);
  if (id === null) {
    return (
      <ErrorNotice
        message={describeError({ service: "planner-service", kind: "problem", status: 404, code: "NOT_FOUND" })}
        backHref="/"
      />
    );
  }
  // The plot (for its name) and the plan are asked at the same time.
  const [plotResult, planResult] = await Promise.all([getPlot(id), getPlan(id)]);
  const plot = plotResult.ok ? plotResult.data : null;

  return (
    <>
      <h1 className="font-heading text-3xl font-bold">{plot ? plot.name : "Plot"}</h1>
      {plot ? (
        <p className="mt-1 mb-5 text-muted-foreground">
          {cropLabel(plot.cropId)}, {formatNumber(plot.areaM2)} m²
        </p>
      ) : (
        <div className="mb-5" />
      )}
      {planResult.ok ? (
        <>
          <RecommendationCard recommendation={todaysRecommendation(planResult.data)} />
          <h2 className="mt-10 mb-2 font-heading text-2xl font-bold">
            {planResult.data.days.length}-day plan
          </h2>
          <PlanList days={planResult.data.days} />
        </>
      ) : (
        <ErrorNotice message={describeError(planResult.error)} backHref="/" />
      )}
    </>
  );
}

export default function PlotPage({ params }: PageProps<"/plots/[id]">) {
  return (
    <Suspense fallback={<p className="text-muted-foreground">Loading the plan</p>}>
      <PlotContent params={params} />
    </Suspense>
  );
}
