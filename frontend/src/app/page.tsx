"use client";

import { useState } from "react";
import Link from "next/link";

import { BackendStatusBanner } from "@/components/backend-status-banner";
import { IncidentForm } from "@/components/incident-form";
import { PredictionCard } from "@/components/prediction-card";
import type { IncidentResponse } from "@/lib/api";

export default function SubmitPage() {
  const [lastIncident, setLastIncident] = useState<IncidentResponse | null>(null);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold">Submit an incident</h1>
        <p className="text-muted-foreground mt-1">
          Get a category prediction and an advisory escalation priority.
        </p>
      </div>

      <BackendStatusBanner />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <IncidentForm onSubmitted={setLastIncident} />

        <div>
          {lastIncident ? (
            <div className="space-y-3">
              <PredictionCard incident={lastIncident} />
              <Link
                href={`/incidents/${lastIncident.id}`}
                className="text-sm text-primary underline-offset-4 hover:underline"
              >
                View full record →
              </Link>
            </div>
          ) : (
            <div className="h-full flex items-center justify-center rounded-lg border border-dashed p-8 text-center text-sm text-muted-foreground">
              Submit an incident to see its predicted category, advisory
              priority, and review status here.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
