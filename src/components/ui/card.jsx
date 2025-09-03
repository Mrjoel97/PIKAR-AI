import * as React from "react"
import { cn } from "@/components/utils"
import { PropTypes } from "@/services/typeSafetyService"
import { motion } from "framer-motion"

// Premium card animation variants
const cardVariants = {
  initial: { opacity: 0, y: 20 },
  animate: { 
    opacity: 1, 
    y: 0,
    transition: { type: "spring", stiffness: 300, damping: 30, duration: 0.32 }
  },
  hover: { 
    y: -6,
    rotateX: -1,
    rotateY: 1,
    scale: 1.01,
    boxShadow: "0 12px 40px rgba(6, 95, 70, 0.10)",
    transition: { type: "spring", stiffness: 400, damping: 25, duration: 0.18 }
  }
}

const Card = React.forwardRef(({ className, hover3d = true, children, ...props }, ref) => (
  <motion.div
    ref={ref}
    className={cn(
      "rounded-2xl border border-gray-200 bg-white text-gray-950 shadow-soft",
      className
    )}
    variants={hover3d ? cardVariants : undefined}
    initial={hover3d ? "initial" : undefined}
    animate={hover3d ? "animate" : undefined}
    whileHover={hover3d ? "hover" : undefined}
    style={{ transformStyle: 'preserve-3d' }}
    {...props}
  >
    {children}
  </motion.div>
))
Card.displayName = "Card"

const CardHeader = React.forwardRef(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("flex flex-col space-y-1.5 p-6", className)}
    {...props}
  />
))
CardHeader.displayName = "CardHeader"

const CardTitle = React.forwardRef(({ className, ...props }, ref) => (
  <h3
    ref={ref}
    className={cn(
      "text-2xl font-semibold leading-none tracking-tight text-gray-900",
      className
    )}
    {...props}
  />
))
CardTitle.displayName = "CardTitle"

const CardDescription = React.forwardRef(({ className, ...props }, ref) => (
  <p
    ref={ref}
    className={cn("text-sm text-gray-500", className)}
    {...props}
  />
))
CardDescription.displayName = "CardDescription"

const CardContent = React.forwardRef(({ className, ...props }, ref) => (
  <div ref={ref} className={cn("p-6 pt-0", className)} {...props} />
))
CardContent.displayName = "CardContent"

const CardFooter = React.forwardRef(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("flex items-center p-6 pt-0", className)}
    {...props}
  />
))
CardFooter.displayName = "CardFooter"

// PropTypes for type safety
Card.propTypes = {
  className: PropTypes.string,
  children: PropTypes.node
}

CardHeader.propTypes = {
  className: PropTypes.string,
  children: PropTypes.node
}

CardFooter.propTypes = {
  className: PropTypes.string,
  children: PropTypes.node
}

CardTitle.propTypes = {
  className: PropTypes.string,
  children: PropTypes.node
}

CardDescription.propTypes = {
  className: PropTypes.string,
  children: PropTypes.node
}

CardContent.propTypes = {
  className: PropTypes.string,
  children: PropTypes.node
}

export { Card, CardHeader, CardFooter, CardTitle, CardDescription, CardContent }