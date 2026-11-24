import { cn, formatConfidence, getConfidenceLevel } from "@/lib/utils";

interface ConfidenceBarProps {
  score: number;
  showLabel?: boolean;
  className?: string;
}

export function ConfidenceBar({
  score,
  showLabel = true,
  className,
}: ConfidenceBarProps) {
  const level = getConfidenceLevel(score);
  const fillClass = {
    high: "confidence-bar-fill-high",
    medium: "confidence-bar-fill-medium",
    low: "confidence-bar-fill-low",
  }[level];

  const textClass = {
    high: "text-amber-600",
    medium: "text-amber-500",
    low: "text-red-500",
  }[level];

  return (
    <div className={cn("flex items-center gap-2", className)}>
      <div className="confidence-bar w-24">
        <div
          className={fillClass}
          style={{ width: `${Math.round(score * 100)}%` }}
        />
      </div>
      {showLabel && (
        <span className={cn("text-2xs font-mono", textClass)}>
          {formatConfidence(score)}
        </span>
      )}
    </div>
  );
}
