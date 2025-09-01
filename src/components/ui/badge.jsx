import * as React from "react"
import { cn } from "@/components/utils"
import { motion } from "framer-motion"

// Premium badge variants with emerald branding
const getBadgeClasses = (variant) => {
  const baseClasses = "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-all duration-200"
  
  const variantClasses = {
    default: "border-transparent bg-emerald-900 text-white shadow-soft",
    secondary: "border-transparent bg-gray-100 text-gray-900",
    destructive: "border-transparent bg-red-500 text-white",
    success: "border-transparent bg-emerald-600 text-white",
    warning: "border-transparent bg-yellow-500 text-white",
    outline: "text-emerald-900 border-emerald-200 bg-emerald-50"
  }

  return cn(baseClasses, variantClasses[variant] || variantClasses.default)
}

// Premium animation variants
const badgeVariants = {
  initial: { scale: 0.8, opacity: 0 },
  animate: { 
    scale: 1, 
    opacity: 1,
    transition: { type: "spring", stiffness: 500, damping: 30, duration: 0.18 }
  },
  hover: {
    scale: 1.05,
    transition: { type: "spring", stiffness: 400, damping: 25, duration: 0.18 }
  }
}

const Badge = React.forwardRef(({ className, variant = "default", children, ...props }, ref) => {
  const badgeClasses = getBadgeClasses(variant)
  
  return (
    <motion.div
      className={cn(badgeClasses, className)}
      ref={ref}
      variants={badgeVariants}
      initial="initial"
      animate="animate"
      whileHover="hover"
      {...props}
    >
      {children}
    </motion.div>
  )
})

Badge.displayName = "Badge"

export { Badge }