import type { FeedbackResponse } from "@/lib/api";

function formatCategory(category: string): string {
  return category
    .split("_")
    .map((word) => word[0]?.toUpperCase() + word.slice(1))
    .join(" ");
}

export function FeedbackHistory({ items }: { items: FeedbackResponse[] }) {
  if (items.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No review feedback yet.
      </p>
    );
  }

  return (
    <ul className="space-y-3">
      {items.map((entry) => (
        <li key={entry.id} className="rounded-md border p-3 text-sm">
          <div className="flex items-center justify-between text-muted-foreground text-xs mb-1">
            <span>{entry.reviewer_name ?? "Anonymous reviewer"} (unverified)</span>
            <span>{new Date(entry.created_at).toLocaleString()}</span>
          </div>
          {entry.corrected_category || entry.corrected_priority ? (
            <p>
              {entry.corrected_category && (
                <>
                  Corrected category to{" "}
                  <strong>{formatCategory(entry.corrected_category)}</strong>.{" "}
                </>
              )}
              {entry.corrected_priority && (
                <>
                  Corrected priority to <strong>{entry.corrected_priority}</strong>.
                </>
              )}
            </p>
          ) : (
            <p>Confirmed the original prediction and priority as-is.</p>
          )}
          {entry.note && <p className="mt-1 italic">&quot;{entry.note}&quot;</p>}
        </li>
      ))}
    </ul>
  );
}
