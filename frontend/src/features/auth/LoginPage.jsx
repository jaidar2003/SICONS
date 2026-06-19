import LoginIconModule from "@mui/icons-material/Login";
import PersonAddAlt1IconModule from "@mui/icons-material/PersonAddAlt1";
import VpnKeyIconModule from "@mui/icons-material/VpnKey";
import { Alert, Box, Button, ButtonGroup, Card, CardContent, CircularProgress, Stack, TextField, Typography } from "@mui/material";
import { useEffect, useMemo, useState } from "react";

import bwLogo from "../../../bwlogo.png";
import { resolveMuiIcon } from "../../shared/components/resolveMuiIcon.js";
import { requestPasswordRecoveryRequest, requestPasswordResetRequest, validatePasswordResetTokenRequest } from "./auth.api.js";

const LOGIN_MODE = "login";
const REGISTER_MODE = "register";
const RECOVERY_MODE = "recovery";
const RESET_MODE = "reset";
const MIN_PASSWORD_LENGTH = 8;
const LoginIcon = resolveMuiIcon(LoginIconModule);
const PersonAddAlt1Icon = resolveMuiIcon(PersonAddAlt1IconModule);
const VpnKeyIcon = resolveMuiIcon(VpnKeyIconModule);

function getResetRouteState() {
  const url = new URL(window.location.href);
  const pathname = url.pathname.replace(/\/+$/, "") || "/";
  const resetToken = url.searchParams.get("reset_token") || "";
  const isResetRoute = pathname === "/reset-password";
  return { resetToken, isResetRoute };
}

export function LoginPage({ onLogin, onRegister }) {
  const initialResetState = getResetRouteState();
  const [mode, setMode] = useState(LOGIN_MODE);
  const [resetToken, setResetToken] = useState(initialResetState.resetToken);
  const [username, setUsername] = useState("");
  const [nombre, setNombre] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);
  const [validatingResetToken, setValidatingResetToken] = useState(initialResetState.isResetRoute);

  const isRegisterMode = mode === REGISTER_MODE;
  const isRecoveryMode = mode === RECOVERY_MODE;
  const isResetMode = mode === RESET_MODE;
  const submitLabel = useMemo(() => {
    if (isResetMode) return "Cambiar clave";
    if (isRecoveryMode) return "Enviar enlace";
    return isRegisterMode ? "Crear cuenta" : "Ingresar";
  }, [isResetMode, isRecoveryMode, isRegisterMode]);

  function resetForm() {
    setUsername("");
    setNombre("");
    setEmail("");
    setPassword("");
    setConfirmPassword("");
  }

  function clearResetRoute() {
    window.history.replaceState({}, "", "/");
  }

  useEffect(() => {
    if (!initialResetState.isResetRoute) {
      setValidatingResetToken(false);
      return;
    }

    if (!initialResetState.resetToken) {
      setMode(LOGIN_MODE);
      setValidatingResetToken(false);
      setError("No podés acceder a recuperacion de clave sin un enlace valido.");
      clearResetRoute();
      return;
    }

    let cancelled = false;

    async function validateResetToken() {
      setValidatingResetToken(true);
      try {
        await validatePasswordResetTokenRequest({ token: initialResetState.resetToken });
        if (cancelled) return;
        setMode(RESET_MODE);
        setResetToken(initialResetState.resetToken);
      } catch (_validationError) {
        if (cancelled) return;
        setMode(LOGIN_MODE);
        setResetToken("");
        setError("No podés acceder a recuperacion de clave sin un enlace valido.");
        clearResetRoute();
      } finally {
        if (!cancelled) {
          setValidatingResetToken(false);
        }
      }
    }

    validateResetToken();

    return () => {
      cancelled = true;
    };
  }, [initialResetState.isResetRoute, initialResetState.resetToken]);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setSuccess("");

    if (isResetMode && !resetToken) {
      setError("El enlace de recuperacion no es valido o ya no contiene el token necesario.");
      return;
    }

    if ((isRegisterMode || isResetMode) && password !== confirmPassword) {
      setError("Las claves no coinciden");
      return;
    }

    if ((isRegisterMode || isResetMode) && password.length < MIN_PASSWORD_LENGTH) {
      setError(`La clave debe tener al menos ${MIN_PASSWORD_LENGTH} caracteres`);
      return;
    }

    setLoading(true);
    try {
      if (isResetMode) {
        const result = await requestPasswordResetRequest({ token: resetToken, password });
        setSuccess(result?.message || "La clave fue actualizada. Ya podés ingresar con la nueva contraseña.");
        setMode(LOGIN_MODE);
        setResetToken("");
        setPassword("");
        setConfirmPassword("");
        clearResetRoute();
      } else if (isRecoveryMode) {
        const result = await requestPasswordRecoveryRequest({ identifier: username.trim() });
        setSuccess(result?.message || "Si el usuario existe, enviaremos un enlace para restablecer la clave.");
        setPassword("");
      } else if (isRegisterMode) {
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
      if (!isRegisterMode && !isRecoveryMode && !isResetMode) {
        resetForm();
      } else if (isRecoveryMode) {
        setUsername("");
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
              {isResetMode ? "Nueva clave" : isRecoveryMode ? "Recuperacion" : isRegisterMode ? "Registro" : "Acceso"}
            </Typography>
            <Typography variant="h2" mt={0.5}>
              {isResetMode ? "Cambiar clave" : isRecoveryMode ? "Recuperar clave" : isRegisterMode ? "Crear cuenta en BuildWise" : "Ingresar a BuildWise"}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {isResetMode
                ? "Definí una nueva contraseña para volver a ingresar a BuildWise."
                : isRecoveryMode
                ? "Ingresá tu email registrado para recibir un enlace de cambio de contraseña."
                : isRegisterMode
                ? "Creá tu usuario para acceder como cliente y usar forecast, costos y optimización."
                : "Entrá con tu usuario demo o con una cuenta registrada."}
            </Typography>
          </Box>

          {isResetMode ? null : (
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
          )}

          {error ? <Alert severity="error">{error}</Alert> : null}
          {success ? <Alert severity="success">{success}</Alert> : null}

          {validatingResetToken ? (
            <Box className="flex justify-center py-6">
              <CircularProgress size={28} />
            </Box>
          ) : null}

          {validatingResetToken ? null : <Box component="form" className="grid gap-4" onSubmit={handleSubmit}>
            <Stack spacing={2}>
              {isRegisterMode ? (
                <>
                  <TextField label="Nombre completo" value={nombre} autoComplete="name" required onChange={(event) => setNombre(event.target.value)} />
                  <TextField label="Email" type="email" value={email} autoComplete="email" required onChange={(event) => setEmail(event.target.value)} />
                </>
              ) : null}

              {isResetMode ? null : (
                <TextField
                  label={isRecoveryMode ? "Email registrado" : "Usuario"}
                  value={username}
                  autoComplete={isRecoveryMode ? "email" : "username"}
                  required
                  onChange={(event) => setUsername(event.target.value)}
                />
              )}
              {isRecoveryMode ? null : (
                <TextField
                  label={isResetMode ? "Nueva clave" : "Clave"}
                  type="password"
                  value={password}
                  autoComplete={isRegisterMode || isResetMode ? "new-password" : "current-password"}
                  required
                  helperText={isRegisterMode || isResetMode ? `Minimo ${MIN_PASSWORD_LENGTH} caracteres` : undefined}
                  onChange={(event) => setPassword(event.target.value)}
                />
              )}
              {isRegisterMode || isResetMode ? (
                <TextField
                  label={isResetMode ? "Repetir nueva clave" : "Repetir clave"}
                  type="password"
                  value={confirmPassword}
                  autoComplete="new-password"
                  required
                  onChange={(event) => setConfirmPassword(event.target.value)}
                />
              ) : null}
            </Stack>

            <Button
              type="submit"
              variant="contained"
              startIcon={isRecoveryMode || isResetMode ? <VpnKeyIcon /> : isRegisterMode ? <PersonAddAlt1Icon /> : <LoginIcon />}
              disabled={loading || validatingResetToken}
            >
              {loading ? (isResetMode ? "Actualizando" : isRecoveryMode ? "Enviando" : isRegisterMode ? "Creando" : "Ingresando") : submitLabel}
            </Button>
            {isRegisterMode ? null : (
              <Button
                type="button"
                variant="text"
                size="small"
                onClick={() => {
                  setMode(isRecoveryMode || isResetMode ? LOGIN_MODE : RECOVERY_MODE);
                  setError("");
                  setSuccess("");
                  setPassword("");
                  setConfirmPassword("");
                  setResetToken("");
                  clearResetRoute();
                }}
              >
                {isRecoveryMode || isResetMode ? "Volver al ingreso" : "Olvide mi clave"}
              </Button>
            )}
          </Box>}
        </CardContent>
      </Card>
    </Box>
  );
}
