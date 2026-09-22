"use client";

import { useState } from "react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import {
  ApiError,
  CATEGORIES,
  PRIORITY_VALUES,
  submitFeedback,
  type FeedbackResponse,
  type IncidentResponse,
} from "@/lib/api";

const CONFIRM_ORIGINAL = "__confirm_original__";

function formatCategory(category: string): string {
  return category
    .split("_")
    .map((word) => word[0]?.toUpperCase() + word.slice(1))
    .join(" ");
}

export function FeedbackForm({
  incident,
  onSubmitted,
}: {
  incident: IncidentResponse;
  onSubmitted: (feedback: FeedbackResponse) => void;
}) {
  const [reviewerName, setReviewerName] = useState("");
  const [category, setCategory] = useState(CONFIRM_ORIGINAL);
  const [priority, setPriority] = useState(CONFIRM_ORIGINAL);
  const [note, setNote] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successCount, setSuccessCount] = useState(0);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const feedback = await submitFeedback(incident.id, {
        reviewer_name: reviewerName.trim() || null,
        corrected_category: category === CONFIRM_ORIGINAL ? null : category,
        corrected_priority: priority === CONFIRM_ORIGINAL ? null : priority,
        note: note.trim() || null,
      });
      setReviewerName("");
      setCategory(CONFIRM_ORIGINAL);
      setPriority(CONFIRM_ORIGINAL);
      setNote("");
      setSuccessCount((n) => n + 1);
      onSubmitted(feedback);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to submit feedback.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="fb-category">Category</Label>
          <Select value={category} onValueChange={setCategory}>
            <SelectTrigger id="fb-category">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={CONFIRM_ORIGINAL}>
                Confirm original ({formatCategory(incident.prediction.category)})
              </SelectItem>
              {CATEGORIES.map((c) => (
                <SelectItem key={c} value={c}>
                  {formatCategory(c)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <Label htmlFor="fb-priority">Priority</Label>
          <Select value={priority} onValueChange={setPriority}>
            <SelectTrigger id="fb-priority">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={CONFIRM_ORIGINAL}>
                Confirm original ({incident.priority.priority})
              </SelectItem>
              {PRIORITY_VALUES.map((p) => (
                <SelectItem key={p} value={p}>
                  {p}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="fb-reviewer">Your name (optional, not verified)</Label>
        <Input
          id="fb-reviewer"
          value={reviewerName}
          onChange={(e) => setReviewerName(e.target.value)}
          placeholder="e.g. Alex"
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="fb-note">Note (optional)</Label>
        <Textarea
          id="fb-note"
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="Why are you confirming or correcting this?"
          rows={3}
        />
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertTitle>Couldn&apos;t submit feedback</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {successCount > 0 && !submitting && !error && (
        <Alert>
          <AlertTitle>Feedback saved</AlertTitle>
          <AlertDescription>
            Recorded without changing the original prediction — see the
            review history below.
          </AlertDescription>
        </Alert>
      )}

      <Button type="submit" disabled={submitting}>
        {submitting ? "Submitting…" : "Submit feedback"}
      </Button>
    </form>
  );
}
