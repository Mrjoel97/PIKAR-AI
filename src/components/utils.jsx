// Utility functions for PIKAR AI
export function cn(...classes) {
  return classes.filter(Boolean).join(' ');
}

// Optional: Add more utility functions as needed
export function formatDate(date) {
  return new Date(date).toLocaleDateString();
}

export function truncateText(text, maxLength = 100) {
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength) + '...';
}