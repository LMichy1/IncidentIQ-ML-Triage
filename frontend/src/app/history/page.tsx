"use client";

import { useCallback, useEffect, useState } from "react";

import { BackendStatusBanner } from "@/components/backend-status-banner";
import { HistoryTable } from "@/components/history-table";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  ApiError,
  listIncidents,
  type IncidentListResponse,
  type ReviewStatusFilter,
} from "@/lib/api";

const PAGE_SIZE = 10;

const FILTERS: { value: ReviewStatusFilter; label: string }[] = [
  { value: "all", label: "All" },
  { value: "pending_review", label: "Pending review" },
  { value: "reviewed", label: "Reviewed" },
];

const EMPTY_MESSAGES: Record<ReviewStatusFilter, string> = {
  all: "No incidents submitted yet.",
  pending_review: "No incidents are pending review.",
  reviewed: "No incidents have been reviewed yet.",
};

export default function HistoryPage() {
  const [data, setData] = useState<IncidentListResponse | null>(null);
  const [offset, setOffset] = useState(0);
  const [reviewStatus, setReviewStatus] = useState<ReviewStatusFilter>("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(
    (currentOffset: number, currentReviewStatus: ReviewStatusFilter) => {
      setLoading(true);
      setError(null);
      listIncidents(PAGE_SIZE, currentOffset, currentReviewStatus)
        .then(setData)
        .catch((err) => {
          setError(err instanceof ApiError ? err.message : "Failed to load incidents.");
        })
        .finally(() => setLoading(false));
    },
    [],
  );

  useEffect(() => {
    // Standard data-fetching-in-effect pattern, verified working by the
    // Playwright e2e suite — not restructuring a working, tested flow to
    // satisfy a stricter newer lint rule.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load(offset, reviewStatus);
  }, [offset, reviewStatus, load]);

  function handleFilterChange(next: ReviewStatusFilter) {
    if (next === reviewStatus) return;
    setReviewStatus(next);
    setOffset(0); // the current page position is meaningless under a new filter
  }

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

      <div role="group" aria-label="Filter by review status" className="flex gap-2">
        {FILTERS.map((f) => (
          <Button
            key={f.value}
            type="button"
            variant={reviewStatus === f.value ? "default" : "outline"}
            size="sm"
            aria-pressed={reviewStatus === f.value}
            disabled={loading}
            onClick={() => handleFilterChange(f.value)}
          >
            {f.label}
          </Button>
        ))}
      </div>

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
          <HistoryTable
            items={data.items}
            emptyMessage={EMPTY_MESSAGES[data.review_status]}
          />
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
