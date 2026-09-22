"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, FlaskConical } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { getReadiness, type ReadinessResponse } from "@/lib/api";

type Status =
  | { kind: "loading" }
  | { kind: "unreachable" }
  | { kind: "not_ready"; data: ReadinessResponse }
  | { kind: "ready"; data: ReadinessResponse };

export function BackendStatusBanner() {
  const [status, setStatus] = useState<Status>({ kind: "loading" });

  useEffect(() => {
    let cancelled = false;
    getReadiness()
      .then((data) => {
        if (cancelled) return;
        setStatus(data.ready ? { kind: "ready", data } : { kind: "not_ready", data });
      })
      .catch(() => {
        if (!cancelled) setStatus({ kind: "unreachable" });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (status.kind === "loading") return null;

  if (status.kind === "unreachable") {
    return (
      <Alert variant="destructive">
        <AlertTriangle className="h-4 w-4" />
        <AlertTitle>Backend unreachable</AlertTitle>
        <AlertDescription>
          Could not reach the IncidentIQ API. Make sure the backend is
          running and NEXT_PUBLIC_API_BASE_URL points at it.
        </AlertDescription>
      </Alert>
    );
  }

  if (status.kind === "not_ready") {
    return (
      <Alert variant="destructive">
        <AlertTriangle className="h-4 w-4" />
        <AlertTitle>Model not loaded</AlertTitle>
        <AlertDescription>
          {status.data.model_error ??
            "The backend is up but the model artifact isn't loaded. Incident submission will fail."}
        </AlertDescription>
      </Alert>
    );
  }

  if (status.data.dataset_is_synthetic) {
    return (
      <Alert>
        <FlaskConical className="h-4 w-4" />
        <AlertTitle>Synthetic demonstration model</AlertTitle>
        <AlertDescription>
          {status.data.model_name} v{status.data.model_version} was trained
          on a synthetic dataset ({status.data.result_stage ?? "development"}
          -stage evaluation) — predictions demonstrate the pipeline, not
          real-world accuracy. See docs/dataset_decision.md.
        </AlertDescription>
      </Alert>
    );
  }

  return null;
}
