import * as React from "react"
import { cn } from "@/lib/utils"

const Button = React.forwardRef<
  HTMLButtonElement,
  React.ButtonHTMLAttributes<HTMLButtonElement> & {
    variant?: "default" | "outline" | "ghost"
  }
>(({ className, variant = "default", ...props }, ref) => {
  const variants = {
    default: "bg-[var(--ink)] text-white hover:opacity-90",
    outline: "border border-[var(--line)] bg-transparent hover:bg-white/50",
    ghost: "hover:bg-white/40",
  }
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[var(--ink)] disabled:pointer-events-none disabled:opacity-50 h-9 px-4 py-2",
        variants[variant],
        className
      )}
      ref={ref}
      {...props}
    />
  )
})
Button.displayName = "Button"

export { Button }
