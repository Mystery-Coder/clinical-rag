import * as React from "react"
import { ChevronDown } from "lucide-react"
import { cn } from "@/lib/utils"

const Collapsible = ({ children }: { children: React.ReactNode }) => {
  const [open, setOpen] = React.useState(false)
  return (
    <div>
      {React.Children.map(children, (child) => {
        if (React.isValidElement(child)) {
          return React.cloneElement(child as React.ReactElement<any>, { open, setOpen })
        }
        return child
      })}
    </div>
  )
}

const CollapsibleTrigger = ({ className, children, open, setOpen }: any) => (
  <button
    type="button"
    onClick={() => setOpen(!open)}
    className={cn("flex items-center gap-2 text-sm text-[var(--ix)]", className)}
  >
    {children}
    <ChevronDown className={cn("h-4 w-4 transition-transform", open && "rotate-180")} />
  </button>
)

const CollapsibleContent = ({ className, children, open }: any) => {
  if (!open) return null
  return <div className={cn("mt-2", className)}>{children}</div>
}

export { Collapsible, CollapsibleTrigger, CollapsibleContent }
