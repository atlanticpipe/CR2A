(() => {
  "use strict";
  // Production configuration for deployed CR2A API
  const injected = typeof window !== "undefined" && window._env ? window._env : {};
  window._env = {
    API_BASE_URL: injected.API_BASE_URL || "https://p6zla1yuxb.execute-api.us-east-1.amazonaws.com/prod",
    API_AUTH_TOKEN: injected.API_AUTH_TOKEN || "Bearer mvp-token",
  };
})();