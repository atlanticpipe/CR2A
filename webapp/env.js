(() => {
  "use strict";
  // Local development configuration
  const injected = typeof window !== "undefined" && window._env ? window._env : {};
  window._env = {
    API_BASE_URL: injected.API_BASE_URL || "http://localhost:8000",
    API_AUTH_TOKEN: injected.API_AUTH_TOKEN || "Bearer local-dev-token",
  };
})();