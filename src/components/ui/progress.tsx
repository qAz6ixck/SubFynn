"use client"

import * as React from "react"
import { cn } from "@/lib/utils"

export interface ProgressProps
  extends React.HTMLAttributes<HTMLDivElement> {
  value?: number | null
}

const Progress = React.forwardRef<HTMLDivElement, ProgressProps>(
  ({ className, value, ...props }, ref) => {
    const safePercent = Math.max(0, Math.min(100, value ?? 0))

    return (
      <div
        ref={ref}
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Math.round(safePercent)}
        className={cn(
          "relative h-2.5 w-full overflow-hidden rounded-full bg-surface-input border border-border-glass",
          className
        )}
        {...props}
      >
        <div
          className="h-full w-full flex-1 bg-gradient-to-r from-brand-indigo via-brand-cyan to-brand-emerald transition-transform duration-300 ease-out"
          style={{ transform: `translateX(-${100 - safePercent}%)` }}
        />
      </div>
    )
  }
)
Progress.displayName = "Progress"

export { Progress }
