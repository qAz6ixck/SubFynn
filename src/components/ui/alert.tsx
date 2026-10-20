import * as React from "react"
import { cn } from "@/lib/utils"

export interface AlertProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "success" | "destructive" | "info"
}

const Alert = React.forwardRef<HTMLDivElement, AlertProps>(
  ({ className, variant = "default", ...props }, ref) => {
    const variantStyles = {
      default: "bg-surface-card border-border-card text-content-white [&>svg]:text-brand-cyan",
      success: "bg-surface-card border-brand-emerald/40 text-content-white [&>svg]:text-brand-emerald shadow-[0_0_20px_-5px_rgba(16,185,129,0.2)]",
      destructive: "bg-surface-card border-brand-rose/40 text-content-white [&>svg]:text-brand-rose shadow-[0_0_20px_-5px_rgba(244,63,94,0.2)]",
      info: "bg-surface-card border-brand-indigo/40 text-content-white [&>svg]:text-brand-indigo shadow-[0_0_20px_-5px_rgba(99,102,241,0.2)]",
    }

    return (
      <div
        ref={ref}
        role="alert"
        className={cn(
          "relative w-full rounded-2xl border p-4 text-sm glass-card-specular backdrop-blur-glass transition-all duration-300",
          "grid grid-cols-[auto_1fr] gap-x-3.5 gap-y-1 items-start",
          "[&>svg]:w-5 [&>svg]:h-5 [&>svg]:mt-0.5 [&>svg]:shrink-0",
          variantStyles[variant] || variantStyles.default,
          className
        )}
        {...props}
      />
    )
  }
)
Alert.displayName = "Alert"

const AlertTitle = React.forwardRef<
  HTMLHeadingElement,
  React.HTMLAttributes<HTMLHeadingElement>
>(({ className, ...props }, ref) => (
  <h5
    ref={ref}
    className={cn(
      "col-start-2 font-semibold text-content-white tracking-tight leading-snug font-sans text-sm",
      className
    )}
    {...props}
  />
))
AlertTitle.displayName = "AlertTitle"

const AlertDescription = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLParagraphElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn(
      "col-start-2 text-xs text-content-muted leading-relaxed font-sans",
      className
    )}
    {...props}
  />
))
AlertDescription.displayName = "AlertDescription"

export { Alert, AlertTitle, AlertDescription }
