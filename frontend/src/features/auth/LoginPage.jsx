import LoginIcon from "@mui/icons-material/Login";
import { Alert, Box, Button, Card, CardContent, TextField, Typography } from "@mui/material";
import { useState } from "react";

import bwLogo from "../../../bwlogo.jpg";

export function LoginPage({ onLogin }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      await onLogin({ username: username.trim(), password });
      setPassword("");
    } catch (loginError) {
      setError(loginError.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <Box className="mx-auto -mt-12 w-[min(420px,calc(100%-32px))] pb-12">
      <Card>
        <CardContent className="grid gap-5 p-6">
          <Box className="grid justify-items-center gap-3 text-center">
            <Box className="inline-flex h-16 w-28 items-center justify-center rounded-2xl border border-slate-200 bg-white px-3 py-2 shadow-sm">
              <img src={bwLogo} alt="BuildWise" className="h-auto w-full object-contain" />
            </Box>
            <Typography color="primary" fontSize={13} fontWeight={800}>
              Acceso
            </Typography>
            <Typography variant="h2" mt={0.5}>
              Ingresar a BuildWise
            </Typography>
          </Box>
          {error ? <Alert severity="error">{error}</Alert> : null}
          <Box component="form" className="grid gap-4" onSubmit={handleSubmit}>
            <TextField label="Usuario" value={username} autoComplete="username" required onChange={(event) => setUsername(event.target.value)} />
            <TextField
              label="Clave"
              type="password"
              value={password}
              autoComplete="current-password"
              required
              onChange={(event) => setPassword(event.target.value)}
            />
            <Button type="submit" variant="contained" startIcon={<LoginIcon />} disabled={loading}>
              {loading ? "Ingresando" : "Ingresar"}
            </Button>
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
}
