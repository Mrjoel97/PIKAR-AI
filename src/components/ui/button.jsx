import * as React from "react"
import { cn } from "@/components/utils"
import { motion } from "framer-motion"

// Button variants with premium emerald branding
const getButtonClasses = (variant, size) => {
  const baseClasses = "inline-flex items-center justify-center whitespace-nowrap rounded-2xl font-medium transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-900 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50"
  
  const variantClasses = {
    default: "bg-emerald-900 text-white hover:bg-emerald-800 shadow-soft hover:shadow-medium",
    destructive: "bg-red-500 text-white hover:bg-red-600 shadow-soft",
    outline: "border border-emerald-900/20 bg-white hover:bg-emerald-50 hover:border-emerald-900/40 text-emerald-900",
    secondary: "bg-gray-100 text-gray-900 hover:bg-gray-200 shadow-soft",
    ghost: "hover:bg-emerald-50 hover:text-emerald-900 text-gray-900",
    link: "text-emerald-900 underline-offset-4 hover:underline"
  }

  const sizeClasses = {
    default: "h-11 px-5 py-3 text-sm",
    sm: "h-9 px-3 text-sm",
    lg: "h-12 px-6 py-3 text-base",
    icon: "h-10 w-10"
  }

  return cn(
    baseClasses,
    variantClasses[variant] || variantClasses.default,
    sizeClasses[size] || sizeClasses.default
  )
}

// Premium animation variants
const buttonVariants = {
  initial: { scale: 1 },
  hover: { 
    scale: 1.02,
    y: -2,
    transition: { type: "spring", stiffness: 400, damping: 17, duration: 0.18 }
  },
  tap: { 
    scale: 0.98,
    transition: { type: "spring", stiffness: 400, damping: 17, duration: 0.18 }
  }
}

const Button = React.forwardRef(({ 
  className, 
  variant = "default", 
  size = "default", 
  asChild = false, 
  children,
  disabled,
  ...props 
}, ref) => {
  const buttonClasses = getButtonClasses(variant, size)
  
  if (asChild) {
    return React.cloneElement(children, {
      className: cn(buttonClasses, className),
      ref,
      ...props
    })
  }

  return (
    <motion.button
      className={cn(buttonClasses, className)}
      ref={ref}
      disabled={disabled}
      variants={!disabled ? buttonVariants : undefined}
      initial="initial"
      whileHover={!disabled ? "hover" : undefined}
      whileTap={!disabled ? "tap" : undefined}
      {...props}
    >
      {children}
    </motion.button>
  )
})

Button.displayName = "Button"

export { Button }