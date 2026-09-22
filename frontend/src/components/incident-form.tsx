"use client";

import { useState } from "react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import {
  ApiError,
  createIncident,
  type ImpactLevel,
  type IncidentResponse,
  type UrgencyLevel,
} from "@/lib/api";

const LEVELS: { value: ImpactLevel; label: string }[] = [
  { value: "low", label: "Low" },
  { value: "medium", label: "Medium" },
  { value: "high", label: "High" },
  { value: "critical", label: "Critical" },
];

const NONE_VALUE = "__none__";

interface FieldErrors {
  title?: string;
  description?: string;
}

function validate(title: string, description: string): FieldErrors {
  const errors: FieldErrors = {};
  if (title.trim().length < 3) {
    errors.title = "Title must be at least 3 characters.";
  }
  if (description.trim().length < 10) {
    errors.description = "Description must be at least 10 characters.";
  }
  return errors;
}

export function IncidentForm({
  onSubmitted,
}: {
  onSubmitted: (incident: IncidentResponse) => void;
}) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [impact, setImpact] = useState<ImpactLevel | "">("");
  const [urgency, setUrgency] = useState<UrgencyLevel | "">("");
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const errors = validate(title, description);
    setFieldErrors(errors);
    if (Object.keys(errors).length > 0) return;

    setSubmitting(true);
    setSubmitError(null);
    try {
      const incident = await createIncident({
        title: title.trim(),
        description: description.trim(),
        impact: impact || null,
        urgency: urgency || null,
      });
      setTitle("");
      setDescription("");
      setImpact("");
      setUrgency("");
      onSubmitted(incident);
    } catch (err) {
      if (err instanceof ApiError) {
        setSubmitError(err.message);
      } else {
        setSubmitError("Something went wrong submitting this incident.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5" noValidate>
      <div className="space-y-2">
        <Label htmlFor="title">Title</Label>
        <Input
          id="title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="e.g. Login fails with a 401"
          aria-invalid={Boolean(fieldErrors.title)}
        />
        {fieldErrors.title && (
          <p className="text-sm text-destructive">{fieldErrors.title}</p>
        )}
      </div>

      <div className="space-y-2">
        <Label htmlFor="description">Description</Label>
        <Textarea
          id="description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="What's happening, where, and how to reproduce it."
          rows={5}
          aria-invalid={Boolean(fieldErrors.description)}
        />
        {fieldErrors.description && (
          <p className="text-sm text-destructive">{fieldErrors.description}</p>
        )}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="impact">Impact (optional)</Label>
          <Select
            value={impact || NONE_VALUE}
            onValueChange={(v) => setImpact(v === NONE_VALUE ? "" : (v as ImpactLevel))}
          >
            <SelectTrigger id="impact">
              <SelectValue placeholder="Not specified" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={NONE_VALUE}>Not specified</SelectItem>
              {LEVELS.map((l) => (
                <SelectItem key={l.value} value={l.value}>
                  {l.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <Label htmlFor="urgency">Urgency (optional)</Label>
          <Select
            value={urgency || NONE_VALUE}
            onValueChange={(v) => setUrgency(v === NONE_VALUE ? "" : (v as UrgencyLevel))}
          >
            <SelectTrigger id="urgency">
              <SelectValue placeholder="Not specified" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={NONE_VALUE}>Not specified</SelectItem>
              {LEVELS.map((l) => (
                <SelectItem key={l.value} value={l.value}>
                  {l.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>
      <p className="text-xs text-muted-foreground -mt-3">
        Leaving impact or urgency unset produces an explicit
        &quot;undetermined&quot; priority rather than a guess.
      </p>

      {submitError && (
        <Alert variant="destructive">
          <AlertTitle>Couldn&apos;t submit incident</AlertTitle>
          <AlertDescription>{submitError}</AlertDescription>
        </Alert>
      )}

      <Button type="submit" disabled={submitting}>
        {submitting ? "Submitting…" : "Submit incident"}
      </Button>
    </form>
  );
}
