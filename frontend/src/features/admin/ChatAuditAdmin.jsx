import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";

import { SectionHeader } from "../../shared/components/SectionHeader.jsx";
import { fetchChatAudit, fetchChatAuditMetrics, fetchChatDeterminism, fetchChatDeterminismCanonica } from "./admin.api.js";

const INTENT_OPTIONS = ["HISTORICO", "FORECAST", "RECOMENDACION", "PRESUPUESTO", "CATALOGO", "ADMIN", "FUERA_ALCANCE"];

function formatDateTime(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "-";
  return new Intl.DateTimeFormat("es-AR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function truncate(value, maxLength = 110) {
  if (!value) return "-";
  return value.length > maxLength ? `${value.slice(0, maxLength)}...` : value;
}

export function ChatAuditAdmin({ token }) {
  const [rows, setRows] = useState([]);
  const [determinism, setDeterminism] = useState(null);
  const [canonical, setCanonical] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [filters, setFilters] = useState({ limit: 50, tipo_intencion: "", fallback_usado: "" });

  const queryParams = useMemo(
    () => ({
      limit: filters.limit,
      tipo_intencion: filters.tipo_intencion,
      fallback_usado: filters.fallback_usado,
    }),
    [filters]
  );

  async function loadAudit() {
    if (!token) return;
    setLoading(true);
    setError("");
    try {
      const data = await fetchChatAudit(queryParams, token);
      const metricas = await fetchChatAuditMetrics({ limit: 500 }, token);
      const report = await fetchChatDeterminism({ limit: 200, limit_groups: 8 }, token);
      const canonicalReport = await fetchChatDeterminismCanonica({ limit: 500 }, token);
      setRows(data);
      setMetrics(metricas);
      setDeterminism(report);
      setCanonical(canonicalReport);
    } catch (loadError) {
      setError(loadError.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    let cancelled = false;

    async function run() {
      if (!token) return;
      setLoading(true);
      setError("");
      try {
        const data = await fetchChatAudit(queryParams, token);
        const metricas = await fetchChatAuditMetrics({ limit: 500 }, token);
        const report = await fetchChatDeterminism({ limit: 200, limit_groups: 8 }, token);
        const canonicalReport = await fetchChatDeterminismCanonica({ limit: 500 }, token);
        if (!cancelled) {
          setRows(data);
          setMetrics(metricas);
          setDeterminism(report);
          setCanonical(canonicalReport);
        }
      } catch (loadError) {
        if (!cancelled) setError(loadError.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    run();

    return () => {
      cancelled = true;
    };
  }, [token, queryParams]);

  return (
    <Card className="mt-3">
      <CardContent>
        <SectionHeader
          title="Auditoría del asistente IA"
          description="Consultas RAG registradas con usuario, intención, fuentes, fallback, duración y respuesta."
          badge="DSS trazable"
        />

        <Box className="mb-3 grid gap-3 md:grid-cols-4">
          <FormControl size="small">
            <InputLabel>Intención</InputLabel>
            <Select
              label="Intención"
              value={filters.tipo_intencion}
              onChange={(event) => setFilters((current) => ({ ...current, tipo_intencion: event.target.value }))}
            >
              <MenuItem value="">Todas</MenuItem>
              {INTENT_OPTIONS.map((intent) => (
                <MenuItem key={intent} value={intent}>
                  {intent}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControl size="small">
            <InputLabel>Fallback</InputLabel>
            <Select
              label="Fallback"
              value={filters.fallback_usado}
              onChange={(event) => setFilters((current) => ({ ...current, fallback_usado: event.target.value }))}
            >
              <MenuItem value="">Todos</MenuItem>
              <MenuItem value="true">Con fallback</MenuItem>
              <MenuItem value="false">Sin fallback</MenuItem>
            </Select>
          </FormControl>
          <TextField
            size="small"
            type="number"
            label="Límite"
            value={filters.limit}
            inputProps={{ min: 1, max: 200 }}
            onChange={(event) => setFilters((current) => ({ ...current, limit: event.target.value }))}
          />
          <Button variant="outlined" onClick={loadAudit} disabled={loading}>
            {loading ? "Actualizando" : "Actualizar"}
          </Button>
        </Box>

        {error ? <Alert severity="error">{error}</Alert> : null}
        {!error && loading ? <Alert severity="info">Cargando auditoría...</Alert> : null}
        {!error && !loading && !rows.length ? <Alert severity="info">No hay consultas auditadas con esos filtros.</Alert> : null}

        {determinism ? (
          <Box className="mb-3 grid gap-3 md:grid-cols-4">
            <Card variant="outlined">
              <CardContent>
                <Typography variant="caption" color="text.secondary" fontWeight={800}>
                  Score determinismo RAG
                </Typography>
                <Typography variant="h5" fontWeight={900}>
                  {determinism.score_promedio != null ? `${Math.round(determinism.score_promedio * 100)}%` : "-"}
                </Typography>
              </CardContent>
            </Card>
            <Card variant="outlined">
              <CardContent>
                <Typography variant="caption" color="text.secondary" fontWeight={800}>
                  Grupos repetidos
                </Typography>
                <Typography variant="h5" fontWeight={900}>
                  {determinism.grupos_repetidos}
                </Typography>
              </CardContent>
            </Card>
            <Card variant="outlined">
              <CardContent>
                <Typography variant="caption" color="text.secondary" fontWeight={800}>
                  Consultas evaluadas
                </Typography>
                <Typography variant="h5" fontWeight={900}>
                  {determinism.consultas_evaluadas}
                </Typography>
              </CardContent>
            </Card>
            <Card variant="outlined">
              <CardContent>
                <Typography variant="caption" color="text.secondary" fontWeight={800}>
                  Campos comparados
                </Typography>
                <Typography variant="h5" fontWeight={900}>
                  {determinism.campos_evaluados?.length || 0}
                </Typography>
              </CardContent>
            </Card>
          </Box>
        ) : null}

        {determinism?.grupos?.length ? (
          <Box className="mb-3 overflow-x-auto">
            <Typography variant="subtitle2" fontWeight={900} className="mb-2">
              Preguntas repetidas con menor estabilidad
            </Typography>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Pregunta</TableCell>
                  <TableCell>Muestra</TableCell>
                  <TableCell>Score</TableCell>
                  <TableCell>Variables</TableCell>
                  <TableCell>Material</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {determinism.grupos.map((group) => (
                  <TableRow key={group.pregunta_normalizada} hover>
                    <TableCell>{truncate(group.pregunta_ejemplo || group.pregunta_normalizada, 90)}</TableCell>
                    <TableCell>{group.muestra}</TableCell>
                    <TableCell>
                      <Chip
                        size="small"
                        label={`${Math.round(group.score * 100)}%`}
                        color={group.score >= 1 ? "success" : group.score >= 0.8 ? "warning" : "error"}
                      />
                    </TableCell>
                    <TableCell>
                      <Box className="flex flex-wrap gap-1">
                        {(group.campos_variables || []).length ? (
                          group.campos_variables.map((field) => <Chip key={field} size="small" label={field} variant="outlined" />)
                        ) : (
                          <Chip size="small" label="Sin variación" color="success" variant="outlined" />
                        )}
                      </Box>
                    </TableCell>
                    <TableCell>{group.material_resuelto || "-"}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Box>
        ) : null}

        {metrics ? (
          <Box className="mb-3 grid gap-3 md:grid-cols-5">
            <Card variant="outlined">
              <CardContent>
                <Typography variant="caption" color="text.secondary" fontWeight={800}>
                  Total consultas
                </Typography>
                <Typography variant="h5" fontWeight={900}>
                  {metrics.total_consultas}
                </Typography>
              </CardContent>
            </Card>
            <Card variant="outlined">
              <CardContent>
                <Typography variant="caption" color="text.secondary" fontWeight={800}>
                  Fuera de alcance
                </Typography>
                <Typography variant="h5" fontWeight={900}>
                  {metrics.consultas_fuera_de_alcance}
                </Typography>
              </CardContent>
            </Card>
            <Card variant="outlined">
              <CardContent>
                <Typography variant="caption" color="text.secondary" fontWeight={800}>
                  Tasa fallback
                </Typography>
                <Typography variant="h5" fontWeight={900}>
                  {metrics.tasa_fallback != null ? `${Math.round(metrics.tasa_fallback * 100)}%` : "-"}
                </Typography>
              </CardContent>
            </Card>
            <Card variant="outlined">
              <CardContent>
                <Typography variant="caption" color="text.secondary" fontWeight={800}>
                  Latencia p95
                </Typography>
                <Typography variant="h5" fontWeight={900}>
                  {metrics.latencia_p95_ms != null ? `${Math.round(metrics.latencia_p95_ms)} ms` : "-"}
                </Typography>
              </CardContent>
            </Card>
            <Card variant="outlined">
              <CardContent>
                <Typography variant="caption" color="text.secondary" fontWeight={800}>
                  Usuarios únicos
                </Typography>
                <Typography variant="h5" fontWeight={900}>
                  {metrics.usuarios_unicos}
                </Typography>
              </CardContent>
            </Card>
          </Box>
        ) : null}

        {canonical ? (
          <Box className="mb-3 grid gap-3">
            <Typography variant="subtitle2" fontWeight={900}>
              Batería canónica
            </Typography>
            <Box className="grid gap-3 md:grid-cols-5">
              <Card variant="outlined">
                <CardContent>
                  <Typography variant="caption" color="text.secondary" fontWeight={800}>
                    Casos
                  </Typography>
                  <Typography variant="h5" fontWeight={900}>
                    {canonical.total_casos}
                  </Typography>
                </CardContent>
              </Card>
              <Card variant="outlined">
                <CardContent>
                  <Typography variant="caption" color="text.secondary" fontWeight={800}>
                    Con evidencia
                  </Typography>
                  <Typography variant="h5" fontWeight={900}>
                    {canonical.casos_con_evidencia}
                  </Typography>
                </CardContent>
              </Card>
              <Card variant="outlined">
                <CardContent>
                  <Typography variant="caption" color="text.secondary" fontWeight={800}>
                    Cobertura
                  </Typography>
                  <Typography variant="h5" fontWeight={900}>
                    {canonical.cobertura != null ? `${Math.round(canonical.cobertura * 100)}%` : "-"}
                  </Typography>
                </CardContent>
              </Card>
              <Card variant="outlined">
                <CardContent>
                  <Typography variant="caption" color="text.secondary" fontWeight={800}>
                    Score promedio
                  </Typography>
                  <Typography variant="h5" fontWeight={900}>
                    {canonical.score_promedio != null ? `${Math.round(canonical.score_promedio * 100)}%` : "-"}
                  </Typography>
                </CardContent>
              </Card>
              <Card variant="outlined">
                <CardContent>
                  <Typography variant="caption" color="text.secondary" fontWeight={800}>
                    Cumplen expectativa
                  </Typography>
                  <Typography variant="h5" fontWeight={900}>
                    {canonical.casos.filter((item) => item.cumple_expectativa).length}
                  </Typography>
                </CardContent>
              </Card>
            </Box>
            <Box className="overflow-x-auto">
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Pregunta</TableCell>
                    <TableCell>Muestra</TableCell>
                    <TableCell>Score</TableCell>
                    <TableCell>Expectativa</TableCell>
                    <TableCell>Observado</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {canonical.casos.map((item) => (
                    <TableRow key={item.pregunta} hover>
                      <TableCell>{truncate(item.pregunta, 90)}</TableCell>
                      <TableCell>{item.muestra}</TableCell>
                      <TableCell>
                        <Chip
                          size="small"
                          label={`${Math.round(item.score * 100)}%`}
                          color={item.score >= 1 ? "success" : item.score >= 0.75 ? "warning" : "error"}
                        />
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2">
                          {item.tipo_intencion_esperada}
                          {item.material_esperado ? ` / ${item.material_esperado}` : ""}
                          {item.horizonte_esperado != null ? ` / ${item.horizonte_esperado}m` : ""}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2">
                          {item.tipo_intencion_observada || "-"}
                          {item.material_observado ? ` / ${item.material_observado}` : ""}
                          {item.horizonte_observado != null ? ` / ${item.horizonte_observado}m` : ""}
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Box>
          </Box>
        ) : null}

        {rows.length ? (
          <Box className="overflow-x-auto">
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Fecha</TableCell>
                  <TableCell>Usuario</TableCell>
                  <TableCell>Intención</TableCell>
                  <TableCell>Pregunta</TableCell>
                  <TableCell>Material</TableCell>
                  <TableCell>Fuentes</TableCell>
                  <TableCell>IA</TableCell>
                  <TableCell align="right">Duración</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {rows.map((row) => (
                  <TableRow key={row.id} hover>
                    <TableCell>{formatDateTime(row.created_at)}</TableCell>
                    <TableCell>
                      <Typography fontWeight={800}>{row.username || `ID ${row.usuario_id || "-"}`}</Typography>
                    </TableCell>
                    <TableCell>
                      <Chip size="small" label={row.tipo_intencion || "-"} color={row.tipo_intencion === "FUERA_ALCANCE" ? "warning" : "primary"} />
                    </TableCell>
                    <TableCell>
                      <Tooltip title={row.pregunta || ""}>
                        <Typography variant="body2">{truncate(row.pregunta)}</Typography>
                      </Tooltip>
                    </TableCell>
                    <TableCell>{row.material_resuelto || "-"}</TableCell>
                    <TableCell>
                      <Box className="flex flex-wrap gap-1">
                        {(row.fuentes_recuperadas || []).slice(0, 3).map((source) => (
                          <Chip key={source} size="small" label={source} variant="outlined" />
                        ))}
                        {(row.fuentes_recuperadas || []).length > 3 ? <Chip size="small" label={`+${row.fuentes_recuperadas.length - 3}`} /> : null}
                      </Box>
                    </TableCell>
                    <TableCell>
                      <Box className="flex flex-wrap gap-1">
                        {row.proveedor_ia ? <Chip size="small" label={row.proveedor_ia} variant="outlined" /> : null}
                        {row.fallback_usado ? <Chip size="small" label="Fallback" color="warning" /> : null}
                      </Box>
                    </TableCell>
                    <TableCell align="right">{row.duration_ms != null ? `${row.duration_ms} ms` : "-"}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Box>
        ) : null}
      </CardContent>
    </Card>
  );
}
