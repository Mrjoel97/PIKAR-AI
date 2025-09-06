declare global {
  interface Window {
    /**
     * Navigate to the auth page with a custom redirect URL
     * @param redirectUrl - URL to redirect to after successful authentication
     */
    navigateToAuth: (redirectUrl: string) => void;
    webkitSpeechRecognition?: any;
  }
  // For TS usage without lib.dom speech types
  var webkitSpeechRecognition: any;
}

export {};