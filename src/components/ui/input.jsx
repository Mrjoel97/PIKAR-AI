import * as React from "react"
import { cn } from "@/components/utils"
import { motion } from "framer-motion"

// Premium input variants
const inputVariants = {
  rest: { 
    scale: 1,
    boxShadow: '0 2px 4px rgba(6,95,70,0.03)'
  },
  focus: { 
    scale: 1.01,
    boxShadow: '0 0 0 3px rgba(6,95,70,0.1), 0 4px 12px rgba(6,95,70,0.06)',
    transition: { duration: 0.18, ease: [0.2, 0.9, 0.2, 1] }
  }
}

const Input = React.forwardRef(({ className, type, ...props }, ref) => {
  return (
    <motion.input
      type={type}
      className={cn(
        "flex h-11 w-full rounded-2xl border border-gray-200 bg-white px-4 py-3 text-sm ring-offset-white file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-gray-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-900 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 transition-all duration-200",
        className
      )}
      ref={ref}
      variants={inputVariants}
      initial="rest"
      whileFocus="focus"
      {...props}
    />
  )
})
Input.displayName = "Input"

export { Input }