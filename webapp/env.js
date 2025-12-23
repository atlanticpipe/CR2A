(() => {
  "use strict";
  // Static env shim for GitHub Pages; edit API_BASE_URL before pushing or inject window.CR2A_API_BASE elsewhere.
  const injected = typeof window !== "undefined" && window._env ? window._env : {};
  window._env = {
    API_BASE_URL: "https://62k6wc3sqe.execute-api.us-east-1.amazonaws.com/prod",
    API_AUTH_TOKEN: "", // Set to your Lambda Authorizer token (e.g., Bearer <jwt>)
  };
})();