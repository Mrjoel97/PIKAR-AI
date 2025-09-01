import React, { useState } from "react";

const TooltipProvider = ({ children }) => {
  return <>{children}</>;
};

const Tooltip = ({ children }) => {
  return <div className="relative inline-block">{children}</div>;
};

const TooltipTrigger = ({ children, asChild, ...props }) => {
  return <div {...props}>{children}</div>;
};

const TooltipContent = ({ children, className = "", side = "top", sideOffset = 4 }) => {
  const [isVisible, setIsVisible] = useState(false);
  
  const positionClasses = {
    top: "bottom-full left-1/2 transform -translate-x-1/2 mb-2",
    bottom: "top-full left-1/2 transform -translate-x-1/2 mt-2",
    left: "right-full top-1/2 transform -translate-y-1/2 mr-2",
    right: "left-full top-1/2 transform -translate-y-1/2 ml-2"
  };

  return (
    <div
      className={`absolute z-50 ${positionClasses[side]} ${
        isVisible ? "opacity-100" : "opacity-0 pointer-events-none"
      } transition-opacity duration-200 ${className}`}
    >
      <div className="bg-gray-900 text-white text-sm rounded-md px-3 py-2 shadow-lg max-w-xs">
        {children}
      </div>
    </div>
  );
};

// Simple tooltip hook for easier usage
const useTooltip = () => {
  const [isVisible, setIsVisible] = useState(false);
  
  return {
    show: () => setIsVisible(true),
    hide: () => setIsVisible(false),
    isVisible
  };
};

export { Tooltip, TooltipTrigger, TooltipContent, TooltipProvider, useTooltip };