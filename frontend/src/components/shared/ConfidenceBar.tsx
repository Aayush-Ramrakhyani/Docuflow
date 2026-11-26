/**
 * ConfidenceBar — a small horizontal bar + percentage for an AI confidence score.
 * Color shifts from amber (high/medium) to red (low) to draw the reviewer's eye
 * to fields that most need checking.
 */

import { cn, formatConfidence, getConfidenceLevel } from "@/lib/utils";

interface ConfidenceBarProps {
  score: number;              // 0–1 confidence value
  showLabel?: boolean;        // Whether to render the "87%" text alongside the bar
  className?: string;
}

export function ConfidenceBar({
  score,
  showLabel = true,
  className,
}: ConfidenceBarProps) {
  const level = getConfidenceLevel(score);  // high | medium | low → picks the fill + text color

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
