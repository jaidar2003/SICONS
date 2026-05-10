import LoginIcon from "@mui/icons-material/Login";
import PersonAddAlt1Icon from "@mui/icons-material/PersonAddAlt1";
import { Alert, Box, Button, ButtonGroup, Card, CardContent, Stack, TextField, Typography } from "@mui/material";
import { useMemo, useState } from "react";

import bwLogo from "../../../bwlogo.png";

const LOGIN_MODE = "login";
const REGISTER_MODE = "register";

export function LoginPage({ onLogin, onRegister }) {
  const [mode, setMode] = useState(LOGIN_MODE);
  const [username, setUsername] = useState("");
  const [nombre, setNombre] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);

  const isRegisterMode = mode === REGISTER_MODE;
  const submitLabel = useMemo(() => (isRegisterMode ? "Crear cuenta" : "Ingresar"), [isRegisterMode]);

  function resetForm() {
    setUsername("");
    setNombre("");
    setEmail("");
    setPassword("");
    setConfirmPassword("");
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setSuccess("");

    if (isRegisterMode && password !== confirmPassword) {
      setError("Las claves no coinciden");
      return;
    }

    setLoading(true);
    try {
      if (isRegisterMode) {
        const result = await onRegister({
          username: username.trim(),
          nombre: nombre.trim(),
          email: email.trim(),
          password,
        });
        setSuccess(result?.message || "Cuenta creada. Queda pendiente de habilitacion.");
        setMode(LOGIN_MODE);
      } else {
        await onLogin({ username: username.trim(), password });
      }
      if (!isRegisterMode) {
        resetForm();
      } else {
        setPassword("");
        setConfirmPassword("");
        setNombre("");
        setEmail("");
      }
    } catch (authError) {
      setError(authError.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <Box className="mx-auto -mt-12 w-[min(460px,calc(100%-32px))] pb-12">
      <Card>
        <CardContent className="grid gap-5 p-6">
          <Box className="grid justify-items-center gap-3 text-center">
            <Box className="inline-flex h-16 w-28 items-center justify-center rounded-2xl border border-slate-200 bg-white px-3 py-2 shadow-sm">
              <img src={bwLogo} alt="BuildWise" className="h-auto w-full object-contain" />
            </Box>
            <Typography color="primary" fontSize={13} fontWeight={800}>
              {isRegisterMode ? "Registro" : "Acceso"}
            </Typography>
            <Typography variant="h2" mt={0.5}>
              {isRegisterMode ? "Crear cuenta en BuildWise" : "Ingresar a BuildWise"}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {isRegisterMode
                ? "Creá tu usuario para acceder como cliente y usar forecast, costos y optimización."
                : "Entrá con tu usuario demo o con una cuenta registrada."}
            </Typography>
          </Box>

          <Box className="flex justify-center">
            <ButtonGroup size="small" variant="outlined" aria-label="Seleccion de acceso">
              <Button variant={mode === LOGIN_MODE ? "contained" : "outlined"} onClick={() => setMode(LOGIN_MODE)}>
                Ingresar
              </Button>
              <Button variant={mode === REGISTER_MODE ? "contained" : "outlined"} onClick={() => setMode(REGISTER_MODE)}>
                Registrarse
              </Button>
            </ButtonGroup>
          </Box>

          {error ? <Alert severity="error">{error}</Alert> : null}
          {success ? <Alert severity="success">{success}</Alert> : null}

          <Box component="form" className="grid gap-4" onSubmit={handleSubmit}>
            <Stack spacing={2}>
              {isRegisterMode ? (
                <>
                  <TextField label="Nombre completo" value={nombre} autoComplete="name" required onChange={(event) => setNombre(event.target.value)} />
                  <TextField label="Email" type="email" value={email} autoComplete="email" required onChange={(event) => setEmail(event.target.value)} />
                </>
              ) : null}

              <TextField label="Usuario" value={username} autoComplete="username" required onChange={(event) => setUsername(event.target.value)} />
              <TextField
                label="Clave"
                type="password"
                value={password}
                autoComplete={isRegisterMode ? "new-password" : "current-password"}
                required
                onChange={(event) => setPassword(event.target.value)}
              />
              {isRegisterMode ? (
                <TextField
                  label="Repetir clave"
                  type="password"
                  value={confirmPassword}
                  autoComplete="new-password"
                  required
                  onChange={(event) => setConfirmPassword(event.target.value)}
                />
              ) : null}
            </Stack>

            <Button type="submit" variant="contained" startIcon={isRegisterMode ? <PersonAddAlt1Icon /> : <LoginIcon />} disabled={loading}>
              {loading ? (isRegisterMode ? "Creando" : "Ingresando") : submitLabel}
            </Button>
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
}
