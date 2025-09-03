import * as React from "react"
import { cn } from "@/components/utils"
import { PropTypes } from "@/services/typeSafetyService"
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

// PropTypes for type safety
Input.propTypes = {
  className: PropTypes.string,
  type: PropTypes.oneOf(['text', 'email', 'password', 'number', 'tel', 'url', 'search', 'date', 'time', 'datetime-local', 'file']),
  placeholder: PropTypes.string,
  value: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  defaultValue: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  onChange: PropTypes.func,
  onBlur: PropTypes.func,
  onFocus: PropTypes.func,
  disabled: PropTypes.bool,
  required: PropTypes.bool,
  id: PropTypes.string,
  name: PropTypes.string,
  autoComplete: PropTypes.string,
  autoFocus: PropTypes.bool,
  readOnly: PropTypes.bool,
  min: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  max: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  step: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  pattern: PropTypes.string,
  maxLength: PropTypes.number,
  minLength: PropTypes.number
}

export { Input }