import { AlertTriangle, Info } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import type { IncidentResponse } from "@/lib/api";

import { PriorityBadge } from "./priority-badge";

function formatCategory(category: string): string {
  return category
    .split("_")
    .map((word) => word[0]?.toUpperCase() + word.slice(1))
    .join(" ");
}

export function PredictionCard({ incident }: { incident: IncidentResponse }) {
  const { prediction, priority } = incident;

  return (
    <Card>
      <CardHeader>
        <CardTitle>{formatCategory(prediction.category)}</CardTitle>
        <CardDescription>
          Predicted by {prediction.model_name} v{prediction.model_version}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {prediction.requires_human_review && (
          <Alert variant="destructive">
            <AlertTriangle className="h-4 w-4" />
            <AlertTitle>Flagged for human review</AlertTitle>
            <AlertDescription>{prediction.review_reason}</AlertDescription>
          </Alert>
        )}

        <div className="text-sm text-muted-foreground space-y-1">
          <div className="flex justify-between">
            <span>Raw top-class score</span>
            <span className="font-mono">{prediction.top_score.toFixed(3)}</span>
          </div>
          <div className="flex justify-between">
            <span>Margin to next class</span>
            <span className="font-mono">
              {prediction.margin_to_second.toFixed(3)}
            </span>
          </div>
        </div>

        <Alert>
          <Info className="h-4 w-4" />
          <AlertTitle>Not a calibrated confidence score</AlertTitle>
          <AlertDescription>
            This model has not been calibrated. The scores above are raw
            model output, shown for transparency — they should not be read
            as &quot;% confidence&quot;. Trained on a synthetic
            demonstration dataset; see the project&apos;s dataset
            documentation for details.
          </AlertDescription>
        </Alert>

        <Separator />

        <div>
          <div className="flex items-center justify-between mb-1">
            <span className="text-sm font-medium">Advisory priority</span>
            <PriorityBadge priority={priority.priority} />
          </div>
          <p className="text-sm text-muted-foreground">{priority.basis}</p>
        </div>
      </CardContent>
    </Card>
  );
}
