import React from "react";
import { cn } from "@/lib/utils";

const Timeline = React.forwardRef(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("relative", className)}
    {...props}
  />
));
Timeline.displayName = "Timeline";

const TimelineItem = React.forwardRef(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("relative pb-8 last:pb-0", className)}
    {...props}
  />
));
TimelineItem.displayName = "TimelineItem";

const TimelineConnector = React.forwardRef(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn(
      "absolute left-4 top-8 h-full w-0.5 bg-gray-200 dark:bg-gray-700 last:hidden",
      className
    )}
    {...props}
  />
));
TimelineConnector.displayName = "TimelineConnector";

const TimelineHeader = React.forwardRef(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("flex items-center gap-4", className)}
    {...props}
  />
));
TimelineHeader.displayName = "TimelineHeader";

const TimelineIcon = React.forwardRef(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn(
      "relative z-10 flex h-8 w-8 items-center justify-center rounded-full bg-white border-2 border-gray-200 dark:bg-gray-900 dark:border-gray-700",
      className
    )}
    {...props}
  />
));
TimelineIcon.displayName = "TimelineIcon";

const TimelineTitle = React.forwardRef(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("font-semibold", className)}
    {...props}
  />
));
TimelineTitle.displayName = "TimelineTitle";

const TimelineBody = React.forwardRef(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("ml-12", className)}
    {...props}
  />
));
TimelineBody.displayName = "TimelineBody";

export {
  Timeline,
  TimelineItem,
  TimelineConnector,
  TimelineHeader,
  TimelineTitle,
  TimelineIcon,
  TimelineBody,
};