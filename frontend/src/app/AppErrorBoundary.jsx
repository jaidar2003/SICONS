import { Component } from "react";
import { Alert, Box, Button, Typography } from "@mui/material";

export class AppErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, componentStack: "" };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, info) {
    this.setState({ componentStack: info?.componentStack || "" });
  }

  render() {
    if (this.state.hasError) {
      return (
        <Box className="min-h-screen bg-md-surface-container p-6">
          <Box className="mx-auto max-w-3xl rounded-xl border border-slate-200 bg-white p-5 shadow-md1">
            <Typography variant="h2" mb={1}>
              BuildWise no pudo renderizar la interfaz
            </Typography>
            <Alert severity="error" sx={{ whiteSpace: "pre-wrap" }}>
              {this.state.error?.message || String(this.state.error || "Error desconocido")}
            </Alert>
            {this.state.componentStack ? (
              <Box component="pre" sx={{ mt: 2, whiteSpace: "pre-wrap", fontSize: 12, overflowX: "auto" }}>
                {this.state.componentStack}
              </Box>
            ) : null}
            <Button sx={{ mt: 2 }} variant="contained" onClick={() => window.location.reload()}>
              Recargar
            </Button>
          </Box>
        </Box>
      );
    }

    return this.props.children;
  }
}
