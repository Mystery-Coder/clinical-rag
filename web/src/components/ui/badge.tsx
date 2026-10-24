import * as React from "react"
import { cn } from "@/lib/utils"

const Badge = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement> & { variant?: "default" | "outline" }
>(({ className, variant = "default", ...props }, ref) => {
  const variants = {
    default: "border-transparent bg-[var(--ink)] text-white",
    outline: "text-foreground",
  }
  return (
    <div
      ref={ref}
      className={cn(
        "inline-flex items-center rounded-md border border-[var(--line)] px-2 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
        variants[variant],
        className
      )}
      {...props}
    />
  )
})
Badge.displayName = "Badge"

export { Badge }
