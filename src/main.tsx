import React from "react";
import ReactDOM from "react-dom/client";
import "../globals.css";           // was "./globals.css"
import App from "../app/App";      // your screenshot shows app/App.tsx

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);