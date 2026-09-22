"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";

import { PredictionCard } from "@/components/prediction-card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError, getIncident, type IncidentResponse } from "@/lib/api";

export default function IncidentDetailPage() {
  const params = useParams<{ id: string }>();
  const [incident, setIncident] = useState<IncidentResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!params.id) return;
    setLoading(true);
    setError(null);
    getIncident(params.id)
      .then(setIncident)
      .catch((err) => {
        if (err instanceof ApiError && err.status === 404) {
          setError("No incident found with this ID.");
        } else if (err instanceof ApiError) {
          setError(err.message);
        } else {
          setError("Failed to load this incident.");
        }
      })
      .finally(() => setLoading(false));
  }, [params.id]);

  if (loading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-8 w-1/2" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertTitle>Couldn&apos;t load incident</AlertTitle>
        <AlertDescription>
          {error}{" "}
          <Link href="/history" className="underline">
            Back to history
          </Link>
        </AlertDescription>
      </Alert>
    );
  }

  if (!incident) return null;

  return (
    <div className="space-y-6">
      <div>
        <Link href="/history" className="text-sm text-muted-foreground hover:underline">
          ← Back to history
        </Link>
        <h1 className="text-2xl font-semibold mt-2">{incident.title}</h1>
        <p className="text-sm text-muted-foreground">
          Submitted {new Date(incident.created_at).toLocaleString()}
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Description</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="whitespace-pre-wrap text-sm">{incident.description}</p>
          <dl className="mt-4 grid grid-cols-2 gap-2 text-sm">
            <dt className="text-muted-foreground">Impact</dt>
            <dd>{incident.impact ?? "Not specified"}</dd>
            <dt className="text-muted-foreground">Urgency</dt>
            <dd>{incident.urgency ?? "Not specified"}</dd>
          </dl>
        </CardContent>
      </Card>

      <PredictionCard incident={incident} />
    </div>
  );
}
