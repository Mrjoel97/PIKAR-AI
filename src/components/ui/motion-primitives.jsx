
// Motion-enabled UI Primitives for PIKAR Premium Design
import React, { forwardRef } from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/components/utils';

// Respect reduced motion preference
const shouldReduceMotion = () => {
  return typeof window !== 'undefined' && 
         window.matchMedia('(prefers-reduced-motion: reduce)').matches;
};

// Base transitions
const springTransition = {
  type: 'spring',
  stiffness: 120,
  damping: 18,
};

const microTransition = {
  duration: 0.18,
  ease: [0.2, 0.9, 0.2, 1],
};

// Section reveal variants
export const sectionVariants = {
  hidden: { 
    opacity: 0, 
    y: shouldReduceMotion() ? 0 : 24 
  },
  show: { 
    opacity: 1, 
    y: 0,
    transition: shouldReduceMotion() ? { duration: 0 } : springTransition
  }
};

// Staggered children reveal
export const staggerContainer = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: shouldReduceMotion() ? 
      { duration: 0 } : 
      {
        staggerChildren: 0.06,
        delayChildren: 0.02
      }
  }
};

// List item variants for staggered animations
export const listItemVariants = {
  hidden: { 
    opacity: 0, 
    x: shouldReduceMotion() ? 0 : -20 
  },
  show: { 
    opacity: 1, 
    x: 0,
    transition: shouldReduceMotion() ? { duration: 0 } : microTransition
  }
};

// Hero section 3D parallax (subtle)
export const heroParallaxVariants = {
  rest: { 
    rotateX: 0,
    translateZ: 0,
    scale: 1
  },
  scroll: { 
    rotateX: shouldReduceMotion() ? 0 : -0.5,
    translateZ: shouldReduceMotion() ? 0 : 8,
    scale: shouldReduceMotion() ? 1 : 1.01,
    transition: {
      type: 'spring',
      stiffness: 100,
      damping: 30
    }
  }
};

// Motion Section (for page sections with reveal animations)
export const MotionSection = forwardRef((props, ref) => {
  const { className, delay = 0, children, ...otherProps } = props;
  
  return (
    <motion.section
      ref={ref}
      className={className}
      variants={sectionVariants}
      initial="hidden"
      whileInView="show"
      viewport={{ once: true, amount: 0.2 }}
      transition={{ delay }}
      {...otherProps}
    >
      {children}
    </motion.section>
  );
});

// Motion Card (simplified version that works with our Card component)
export const MotionCard = forwardRef((props, ref) => {
  const { className, hover3d = true, children, ...otherProps } = props;
  
  // Return regular Card since we've already added motion to the Card component
  return (
    <div
      ref={ref}
      className={cn(
        'rounded-2xl bg-white shadow-soft border border-gray-100',
        className
      )}
      {...otherProps}
    >
      {children}
    </div>
  );
});
