import { useEffect, useState } from "react";
import { Alert, Box, Button, Card, CardContent, Chip, FormControl, InputLabel, MenuItem, Select, Stack, TextField, Typography } from "@mui/material";

import { SectionHeader } from "../../shared/components/SectionHeader.jsx";
import { fetchChatConfig, updateChatConfig } from "./admin.api.js";

const PROVIDER_OPTIONS = [
  { value: "facultad", label: "API de la facultad" },
  { value: "claude", label: "Claude" },
];

export function ChatConfigAdmin({ token }) {
  const [config, setConfig] = useState(null);
  const [form, setForm] = useState({
    proveedor_activo: "facultad",
    modelo_facultad: "",
    modelo_claude: "",
  });
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!token) return;

    let cancelled = false;

    async function loadConfig() {
      setLoading(true);
      setError("");
      try {
        const data = await fetchChatConfig(token);
        if (cancelled) return;
        setConfig(data);
        setForm({
          proveedor_activo: data.proveedor_activo || "facultad",
          modelo_facultad: data.modelo_facultad || "",
          modelo_claude: data.modelo_claude || "",
        });
      } catch (loadError) {
        if (!cancelled) setError(loadError.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    loadConfig();

    return () => {
      cancelled = true;
    };
  }, [token]);

  function updateField(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function handleSave(event) {
    event.preventDefault();
    setSaving(true);
    setError("");
    setMessage("");
    try {
      const result = await updateChatConfig(
        {
          proveedor_activo: form.proveedor_activo,
          modelo_facultad: form.modelo_facultad.trim() || null,
          modelo_claude: form.modelo_claude.trim() || null,
        },
        token
      );
      setConfig(result);
      setForm({
        proveedor_activo: result.proveedor_activo || "facultad",
        modelo_facultad: result.modelo_facultad || "",
        modelo_claude: result.modelo_claude || "",
      });
      window.dispatchEvent(new CustomEvent("buildwise:chat-config-updated", { detail: result }));
      setMessage("Configuracion de IA actualizada correctamente.");
    } catch (saveError) {
      setError(saveError.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <Card className="mt-5">
      <CardContent className="space-y-6 p-5 md:p-6">
        <SectionHeader
          title="Configuracion de IA"
          description="Selecciona el proveedor primario y revisa los modelos configurados para chat. El fallback a Claude queda automatico cuando la API de la facultad falla."
          badge="Admin"
        />

        <Alert severity="info">
          La seleccion impacta solo en la capa conversacional. El core de BuildWise sigue usando datos propios, forecast, anomalías y reglas deterministicas.
        </Alert>

        {error ? <Alert severity="error">{error}</Alert> : null}
        {message ? <Alert severity="success">{message}</Alert> : null}

        <Box className="grid gap-3 md:grid-cols-3">
          <MiniStatus label="Proveedor activo" value={config ? (PROVIDER_OPTIONS.find((opt) => opt.value === config.proveedor_activo)?.label || config.proveedor_activo) : "-"} />
          <MiniStatus label="Modelo facultad" value={config?.modelo_facultad || "Sin configurar"} />
          <MiniStatus label="Modelo Claude" value={config?.modelo_claude || "Sin configurar"} />
        </Box>

        <Box component="form" onSubmit={handleSave} className="rounded-2xl border border-slate-200 bg-slate-50 p-4 md:p-5">
          <Stack spacing={2.25}>
            <FormControl size="small">
              <InputLabel id="chat-provider-label">Proveedor primario</InputLabel>
              <Select
                labelId="chat-provider-label"
                label="Proveedor primario"
                value={form.proveedor_activo}
                onChange={(event) => updateField("proveedor_activo", event.target.value)}
              >
                {PROVIDER_OPTIONS.map((option) => (
                  <MenuItem key={option.value} value={option.value}>
                    {option.label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <TextField
              size="small"
              label="Modelo de la facultad"
              value={form.modelo_facultad}
              onChange={(event) => updateField("modelo_facultad", event.target.value)}
              helperText="Identificador real del modelo enviado a la API compatible de la facultad. Ej.: gemma4-26b."
            />

            <TextField
              size="small"
              label="Modelo Claude"
              value={form.modelo_claude}
              onChange={(event) => updateField("modelo_claude", event.target.value)}
              helperText="Identificador real del modelo de Anthropic. Se usa cuando Claude queda como primario o fallback."
            />

            <Box className="flex flex-wrap gap-2">
              <Button type="submit" variant="contained" disabled={saving || loading}>
                {saving ? "Guardando" : "Guardar configuración"}
              </Button>
            </Box>
          </Stack>
        </Box>
      </CardContent>
    </Card>
  );
}

function MiniStatus({ label, value }) {
  return (
    <Box className="rounded-xl border border-slate-200 bg-white p-3">
      <Typography color="text.secondary" variant="body2" fontWeight={800}>
        {label}
      </Typography>
      <Typography component="strong" display="block" mt={0.75} variant="h3" lineHeight={1.1}>
        {value}
      </Typography>
      <Chip label="Configuracion global" size="small" variant="outlined" sx={{ mt: 1, fontWeight: 800 }} />
    </Box>
  );
}
