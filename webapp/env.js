(() => {
  "use strict";
  // Amplify overwrites this file at build to expose environment variables safely in the browser.
  const injected = typeof window !== "undefined" && window._env ? window._env : {};
  window._env = {
    API_BASE_URL: injected.API_BASE_URL || "",
  };
})();
