"use client";

import { AlertTriangle, CheckCircle2 } from "lucide-react";
import Link from "next/link";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { IncidentResponse } from "@/lib/api";

import { PriorityBadge } from "./priority-badge";

function formatCategory(category: string): string {
  return category
    .split("_")
    .map((word) => word[0]?.toUpperCase() + word.slice(1))
    .join(" ");
}

export function HistoryTable({
  items,
  emptyMessage = "No incidents submitted yet.",
}: {
  items: IncidentResponse[];
  emptyMessage?: string;
}) {
  if (items.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-8 text-center">
        {emptyMessage}
      </p>
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Title</TableHead>
          <TableHead>Category</TableHead>
          <TableHead>Priority</TableHead>
          <TableHead>Review</TableHead>
          <TableHead>Submitted</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {items.map((incident) => (
          <TableRow key={incident.id}>
            <TableCell className="max-w-[280px] truncate">
              <Link
                href={`/incidents/${incident.id}`}
                className="hover:underline"
              >
                {incident.title}
              </Link>
            </TableCell>
            <TableCell>{formatCategory(incident.prediction.category)}</TableCell>
            <TableCell>
              <PriorityBadge priority={incident.priority.priority} />
            </TableCell>
            <TableCell>
              {incident.reviewed ? (
                <span className="inline-flex items-center gap-1 text-green-700 text-sm">
                  <CheckCircle2 className="h-3.5 w-3.5" /> Reviewed
                </span>
              ) : incident.prediction.requires_human_review ? (
                <span className="inline-flex items-center gap-1 text-amber-600 text-sm">
                  <AlertTriangle className="h-3.5 w-3.5" /> Needed
                </span>
              ) : (
                <span className="text-sm text-muted-foreground">—</span>
              )}
            </TableCell>
            <TableCell className="text-sm text-muted-foreground">
              {new Date(incident.created_at).toLocaleString()}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
