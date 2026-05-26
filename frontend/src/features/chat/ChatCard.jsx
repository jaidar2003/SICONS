import { Alert, Box, Button, Card, CardContent, CircularProgress, TextField, Typography } from "@mui/material";
import { useState } from "react";

import { SectionHeader } from "../../shared/components/SectionHeader.jsx";
import { askChatQuestion } from "./chat.api.js";

function initialMessage(isAdmin) {
  return {
    role: "assistant",
    text: isAdmin
      ? "Podés consultarme precios y forecast, pedirme recomendaciones, comparar estrategias, simular horizontes, priorizar materiales u optimizar un presupuesto. Las operaciones administrativas requieren confirmación."
      : "Podés consultarme precios y forecast, pedirme recomendaciones, comparar estrategias, simular horizontes, priorizar materiales u optimizar un presupuesto.",
  };
}

export function ChatCard({ token, selectedMaterial, forecastHorizon, isAdmin }) {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([initialMessage(isAdmin)]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event) {
    event.preventDefault();
    const trimmed = question.trim();
    if (!trimmed || loading) return;

    setQuestion("");
    setError("");
    setMessages((current) => [...current, { role: "user", text: trimmed }]);
    setLoading(true);
    try {
      const historial = messages
        .slice(1)
        .filter((message) => !message.rejected)
        .slice(-8)
        .map((message) => ({ role: message.role, content: message.text }));
      const result = await askChatQuestion(
        {
          pregunta: trimmed,
          material_id: selectedMaterial?.id ?? null,
          horizonte_meses: forecastHorizon,
          historial,
        },
        token
      );
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          text: result.respuesta,
          rejected: !result.aceptada,
        },
      ]);
    } catch (chatError) {
      setError(chatError.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card className="mt-3 overflow-hidden border border-slate-200 shadow-md1">
      <CardContent>
        <SectionHeader
          title="Asistente BuildWise"
          description={`Opera con datos calculados de ${selectedMaterial?.nombre || "los materiales"} a ${forecastHorizon} meses. Las consultas externas se rechazan antes de llamar al proveedor de IA.`}
        />

        {error ? <Alert severity="error" className="mb-3">{error}</Alert> : null}

        <Box className="mb-4 flex min-h-[300px] flex-col gap-3 rounded-xl border border-slate-200 bg-slate-50 p-4">
          {messages.map((message, index) => (
            <Box
              key={`${message.role}-${index}`}
              className={`max-w-[85%] rounded-xl px-4 py-3 ${message.role === "user" ? "ml-auto bg-teal-700 text-white" : "bg-white text-slate-800 shadow-sm"}`}
            >
              <Typography variant="body2" sx={{ whiteSpace: "pre-wrap" }}>
                {message.text}
              </Typography>
              {message.rejected ? (
                <Typography variant="caption" color="text.secondary" display="block" mt={0.5}>
                  Consulta fuera del alcance habilitado.
                </Typography>
              ) : null}
            </Box>
          ))}
          {loading ? (
            <Box className="flex items-center gap-2 rounded-xl bg-white px-4 py-3 text-slate-600 shadow-sm">
              <CircularProgress size={16} />
              <Typography variant="body2">Consultando asistente...</Typography>
            </Box>
          ) : null}
        </Box>

        <Box component="form" onSubmit={handleSubmit} className="flex flex-col gap-3 sm:flex-row">
          <TextField
            fullWidth
            size="small"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            label="Pregunta"
            placeholder="Ej.: Compará estrategias para 500 kg de cemento en 6 meses"
            inputProps={{ maxLength: 1000 }}
            disabled={loading}
          />
          <Button type="submit" variant="contained" disabled={!question.trim() || loading}>
            Enviar
          </Button>
        </Box>
      </CardContent>
    </Card>
  );
}
