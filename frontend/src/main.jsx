import React from "react";
import ReactDOM from "react-dom/client";
import { CssBaseline, ThemeProvider } from "@mui/material";
import { LocalizationProvider } from "@mui/x-date-pickers";
import { AdapterDayjs } from "@mui/x-date-pickers/AdapterDayjs";
import "dayjs/locale/es";

import { App } from "./app/App.jsx";
import { AppErrorBoundary } from "./app/AppErrorBoundary.jsx";
import { theme } from "./app/theme.js";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <ThemeProvider theme={theme}>
      <LocalizationProvider dateAdapter={AdapterDayjs} adapterLocale="es">
        <CssBaseline />
        <AppErrorBoundary>
          <App />
        </AppErrorBoundary>
      </LocalizationProvider>
    </ThemeProvider>
  </React.StrictMode>
);
