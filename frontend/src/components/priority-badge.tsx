import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

const PRIORITY_STYLES: Record<string, string> = {
  P1: "bg-red-600 text-white hover:bg-red-600",
  P2: "bg-orange-500 text-white hover:bg-orange-500",
  P3: "bg-yellow-500 text-black hover:bg-yellow-500",
  P4: "bg-slate-400 text-white hover:bg-slate-400",
};

export function PriorityBadge({ priority }: { priority: string }) {
  if (priority === "undetermined") {
    return (
      <Badge variant="outline" className="border-dashed">
        Undetermined — needs review
      </Badge>
    );
  }

  return (
    <Badge className={cn(PRIORITY_STYLES[priority] ?? "")}>{priority}</Badge>
  );
}
