import LoginIcon from "@mui/icons-material/Login";
import { Alert, Box, Button, Card, CardContent, TextField, Typography } from "@mui/material";
import { useState } from "react";

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
        <CardContent className="grid gap-4 p-6">
          <Box>
            <Typography color="primary" fontSize={13} fontWeight={800}>
              Acceso
            </Typography>
            <Typography variant="h2" mt={0.5}>
              Ingresar a SICONS
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

