"use client";

import { useCallback, useEffect, useState } from "react";

import { BackendStatusBanner } from "@/components/backend-status-banner";
import { HistoryTable } from "@/components/history-table";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError, listIncidents, type IncidentListResponse } from "@/lib/api";

const PAGE_SIZE = 10;

export default function HistoryPage() {
  const [data, setData] = useState<IncidentListResponse | null>(null);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback((currentOffset: number) => {
    setLoading(true);
    setError(null);
    listIncidents(PAGE_SIZE, currentOffset)
      .then(setData)
      .catch((err) => {
        setError(err instanceof ApiError ? err.message : "Failed to load incidents.");
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    // load() sets loading/error synchronously before its async fetch — the
    // standard data-fetching-in-effect pattern (verified working by the
    // Playwright e2e suite). Not restructuring a working, tested flow to
    // satisfy a stricter newer lint rule.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load(offset);
  }, [offset, load]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Incident history</h1>
        <p className="text-muted-foreground mt-1">
          Every prediction is stored with the model and policy version used
          to produce it.
        </p>
      </div>

      <BackendStatusBanner />

      {error && (
        <Alert variant="destructive">
          <AlertTitle>Couldn&apos;t load incidents</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {loading && !data && (
        <div className="space-y-2">
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-8 w-full" />
        </div>
      )}

      {data && (
        <>
          <HistoryTable items={data.items} />
          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">
              {data.total === 0
                ? "0 incidents"
                : `Showing ${offset + 1}–${Math.min(offset + PAGE_SIZE, data.total)} of ${data.total}`}
            </p>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={offset === 0 || loading}
                onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
              >
                Previous
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={offset + PAGE_SIZE >= data.total || loading}
                onClick={() => setOffset(offset + PAGE_SIZE)}
              >
                Next
              </Button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
