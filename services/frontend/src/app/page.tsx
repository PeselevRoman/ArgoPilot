import { connection } from "next/server";
import { Suspense } from "react";
import { ErrorNotice } from "@/components/error-notice";
import { FarmList } from "@/components/farm-list";
import { describeError } from "@/lib/messages";
import { listFarmsWithPlots } from "@/lib/registry";

async function Farms() {
  await connection(); // fetch at request time, never at build time
  const result = await listFarmsWithPlots();
  if (!result.ok) return <ErrorNotice message={describeError(result.error)} />;
  return <FarmList farms={result.data.farms} unassignedPlots={result.data.unassignedPlots} />;
}

export default function HomePage() {
  return (
    <>
      <h1 className="mb-6 font-heading text-3xl font-bold">Your plots</h1>
      <Suspense fallback={<p className="text-muted-foreground">Loading plots</p>}>
        <Farms />
      </Suspense>
    </>
  );
}
