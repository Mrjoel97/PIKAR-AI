// Mock hook for persona management
// In a real app, this would come from global state or database
export const usePersona = () => {
  // Hardcoded for now, or could check local storage
  // 'solopreneur', 'startup', 'sme', 'enterprise'
  return { persona: 'solopreneur' }; 
};
