
import * as React from "react"
import { cn } from "@/components/utils"

const Progress = React.forwardRef(({ className, value, ...props }, ref) => (
  <div
    ref={ref}
    className={cn(
      "relative h-2 w-full overflow-hidden rounded-full bg-gray-200 dark:bg-gray-800",
      className
    )}
    {...props}
  >
    <div
      className="h-full w-full flex-1 bg-emerald-600 transition-all duration-300 ease-out"
      style={{ transform: `translateX(-${100 - (value || 0)}%)` }}
    />
  </div>
))
Progress.displayName = "Progress"

export { Progress }
