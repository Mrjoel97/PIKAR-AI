import React, { useState, createContext, useContext } from "react";

// Simple collapsible context
const CollapsibleContext = createContext();

const Collapsible = ({ children, defaultOpen = false }) => {
  const [isOpen, setIsOpen] = useState(defaultOpen);
  
  return (
    <CollapsibleContext.Provider value={{ isOpen, setIsOpen }}>
      <div data-state={isOpen ? "open" : "closed"} className="group/collapsible">
        {children}
      </div>
    </CollapsibleContext.Provider>
  );
};

const CollapsibleTrigger = ({ children, className = "", ...props }) => {
  const { isOpen, setIsOpen } = useContext(CollapsibleContext);
  
  return (
    <button
      onClick={() => setIsOpen(!isOpen)}
      className={className}
      {...props}
    >
      {children}
    </button>
  );
};

const CollapsibleContent = ({ children, className = "" }) => {
  const { isOpen } = useContext(CollapsibleContext);
  
  return (
    <div
      className={`transition-all duration-200 overflow-hidden ${
        isOpen ? "max-h-96 opacity-100" : "max-h-0 opacity-0"
      } ${className}`}
    >
      <div className="py-1">
        {children}
      </div>
    </div>
  );
};

export { Collapsible, CollapsibleTrigger, CollapsibleContent };