import AddIcon from "@mui/icons-material/Add";
import AutoGraphIcon from "@mui/icons-material/AutoGraph";
import AdminPanelSettingsOutlinedIcon from "@mui/icons-material/AdminPanelSettingsOutlined";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import Inventory2OutlinedIcon from "@mui/icons-material/Inventory2Outlined";
import SavingsOutlinedIcon from "@mui/icons-material/SavingsOutlined";
import TimelineOutlinedIcon from "@mui/icons-material/TimelineOutlined";
import {
  Alert,
  Box,
  Button,
  ButtonGroup,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Container,
  Tab,
  Tabs,
  Typography,
} from "@mui/material";
import dayjs from "dayjs";
import { useCallback, useEffect, useMemo, useState } from "react";

import { PriceForm } from "../features/admin/PriceForm.jsx";
import { fetchCurrentUser, loginRequest, registerRequest } from "../features/auth/auth.api.js";
import { LoginPage } from "../features/auth/LoginPage.jsx";
import { fetchFuentes, fetchMateriales, fetchPresentaciones } from "../features/catalog/catalog.api.js";
import { AppHeader } from "../features/layout/AppHeader.jsx";
import { AnomaliesCard } from "../features/pricing/AnomaliesCard.jsx";
import { ComparisonCard } from "../features/pricing/ComparisonCard.jsx";
import { CostPlannerCard } from "../features/pricing/CostPlannerCard.jsx";
import { CostProjectionCard } from "../features/pricing/CostProjectionCard.jsx";
import { FiltersBar } from "../features/pricing/FiltersBar.jsx";
import { ForecastCard } from "../features/pricing/ForecastCard.jsx";
import { ForecastModelDetails } from "../features/pricing/ForecastModelDetails.jsx";
import { HistoryTable } from "../features/pricing/HistoryTable.jsx";
import { InsightStrip } from "../features/pricing/InsightStrip.jsx";
import { MetricsGrid } from "../features/pricing/MetricsGrid.jsx";
import { PurchaseDecisionCard } from "../features/pricing/PurchaseDecisionCard.jsx";
import { PriceChart } from "../features/pricing/PriceChart.jsx";
import { CommercialMarginsAdmin } from "../features/admin/CommercialMarginsAdmin.jsx";
import { UsersAdmin } from "../features/admin/UsersAdmin.jsx";
import { createPrecioHistorico, fetchCommercialPrice, fetchForecast, fetchPriceRange, fetchSerie } from "../features/pricing/pricing.api.js";
import { getDisplayPrice, getMaterialPresentation } from "../features/pricing/materialPresentation.js";
import { apiGet } from "../shared/api/http.js";
import { formatCurrency, formatNumber, toApiDate } from "../shared/utils/formatters.js";
import { brand } from "./brand.js";

const TOKEN_KEY = "sicons_token";
const SHOW_PRICES_KEY = "sicons_show_prices";
const VIEW_TABS = [
  {
    value: "summary",
    label: "Resumen",
    description: "Panorama general, señales rápidas y comparación entre materiales.",
    accent: brand.sections.summary.accent,
    eyebrow: "Vista ejecutiva",
    icon: AutoGraphIcon,
  },
  {
    value: "forecast",
    label: "Forecast",
    description: "Proyección mensual, lectura técnica del modelo y comportamiento esperado.",
    accent: brand.sections.forecast.accent,
    eyebrow: "Capa predictiva",
    icon: TimelineOutlinedIcon,
  },
  {
    value: "costs",
    label: "Costos",
    description: "Escenarios de compra y apoyo para decisiones económicas de obra.",
    accent: brand.sections.costs.accent,
    eyebrow: "Impacto económico",
    icon: SavingsOutlinedIcon,
  },
  {
    value: "chatbot",
    label: "Chatbot IA",
    description: "Asistente conversacional para consultas y recomendaciones. Se incorpora en el segundo sprint.",
    accent: brand.sections.chatbot.accent,
    eyebrow: "Segundo sprint",
    icon: AdminPanelSettingsOutlinedIcon,
    disabled: true,
  },
  {
    value: "history",
    label: "Historial",
    description: "Serie completa, anomalías detectadas y tareas administrativas sobre precios.",
    accent: brand.sections.history.accent,
    eyebrow: "Auditoría de datos",
    icon: Inventory2OutlinedIcon,
  },
  {
    value: "admin",
    label: "Admin",
    description: "Configuración comercial interna para márgenes y reglas de precio de venta.",
    accent: brand.sections.admin.accent,
    eyebrow: "Administración",
    icon: AdminPanelSettingsOutlinedIcon,
  },
];

function buildComparisonRows(results) {
  return results
    .filter((result) => result.serie.length > 0)
    .map((result) => {
      const first = result.serie[0];
      const last = result.serie[result.serie.length - 1];
      const firstValue = Number(first.precio_promedio_normalizado);
      const lastValue = Number(last.precio_promedio_normalizado);
      const variation = firstValue === 0 ? 0 : ((lastValue - firstValue) / firstValue) * 100;
      const sampleSize = result.serie.reduce((total, point) => total + Number(point.cantidad_registros || 0), 0);
      return { material: result.material, first, last, firstValue, lastValue, variation, sampleSize };
    })
    .sort((left, right) => left.variation - right.variation);
}

export function App() {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY));
  const [showPrices, setShowPrices] = useState(() => localStorage.getItem(SHOW_PRICES_KEY) !== "false");
  const [user, setUser] = useState(null);
  const [apiStatus, setApiStatus] = useState({ mode: "", label: "Conectando API" });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [materiales, setMateriales] = useState([]);
  const [presentaciones, setPresentaciones] = useState([]);
  const [fuentes, setFuentes] = useState([]);
  const [selectedMaterialId, setSelectedMaterialId] = useState("");
  const [desde, setDesde] = useState(null);
  const [hasta, setHasta] = useState(null);
  const [maxDate, setMaxDate] = useState(null);
  const [dateWarning, setDateWarning] = useState("");
  const [serie, setSerie] = useState([]);
  const [forecast, setForecast] = useState(null);
  const [commercialPrice, setCommercialPrice] = useState(null);
  const [forecastHorizon, setForecastHorizon] = useState(3);
  const [forecastPriceView, setForecastPriceView] = useState("comparative");
  const [comparisonRows, setComparisonRows] = useState([]);
  const [showPriceForm, setShowPriceForm] = useState(false);
  const [activeView, setActiveView] = useState("summary");
  const clientDefaultStart = useMemo(() => dayjs("2026-01-01"), []);

  const selectedMaterial = useMemo(
    () => materiales.find((material) => String(material.id) === String(selectedMaterialId)),
    [materiales, selectedMaterialId]
  );
  const selectedPresentation = useMemo(
    () => getMaterialPresentation(selectedMaterial?.nombre, selectedMaterial?.unidad_base),
    [selectedMaterial?.nombre, selectedMaterial?.unidad_base]
  );
  const isAdmin = user?.rol === "admin";
  const visibleTabs = useMemo(() => VIEW_TABS.filter((tab) => tab.value !== "admin" || isAdmin), [isAdmin]);
  const activeTabConfig = useMemo(
    () => visibleTabs.find((tab) => tab.value === activeView) ?? visibleTabs[0],
    [activeView, visibleTabs]
  );
  const summaryNextForecastPoint = forecast?.puntos?.[0] || null;
  const summaryLastForecastPoint = forecast?.puntos?.[forecast?.puntos?.length - 1] || null;
  const summaryForecastSelection = forecast?.seleccion_modelo || null;
  const summaryForecastDeltaPct =
    forecast && summaryNextForecastPoint
      ? ((Number(summaryNextForecastPoint.precio_proyectado) - Number(forecast.ultimo_precio_observado)) / Number(forecast.ultimo_precio_observado)) * 100
      : null;
  const summaryForecastConfidence = String(summaryForecastSelection?.confiabilidad || "").toLowerCase();
  const summaryForecastRecommendation =
    summaryForecastDeltaPct === null
      ? "Sin forecast disponible."
      : summaryForecastDeltaPct > 0
        ? summaryForecastConfidence === "baja"
          ? "El precio tiende a subir, pero la confianza es baja. Conviene monitorear antes de decidir."
          : "El precio tiende a subir. Conviene anticipar compra si el presupuesto lo permite."
        : summaryForecastDeltaPct < 0
          ? "El precio tiende a bajar. Conviene esperar si la urgencia lo permite."
          : "El precio luce estable. La decisión depende más de la urgencia y del presupuesto.";
  const summaryForecastDirection =
    summaryForecastDeltaPct === null
      ? "Sin proyeccion"
      : summaryForecastDeltaPct > 0
        ? "Tendencia alcista"
        : summaryForecastDeltaPct < 0
          ? "Tendencia bajista"
          : "Tendencia estable";
  const summaryShowBagEquivalents =
    selectedPresentation.type === "cement" &&
    summaryNextForecastPoint?.precio_equivalente_25kg !== null &&
    summaryNextForecastPoint?.precio_equivalente_25kg !== undefined;

  const loadSerieData = useCallback(
    async ({ materialId = selectedMaterialId, from = desde, to = hasta, horizon = forecastHorizon } = {}) => {
      if (!materialId) return;
      const desdeApi = toApiDate(from);
      const hastaApi = toApiDate(to);
      const [serieActual, forecastActual, commercialPriceActual, comparisonResults] = await Promise.all([
        fetchSerie({ materialId, desde: desdeApi, hasta: hastaApi, token }),
        fetchForecast({ materialId, horizonteMeses: horizon, token }).catch(() => null),
        fetchCommercialPrice({ materialId, horizonteMeses: horizon, token }).catch(() => null),
        Promise.all(
          materiales.map(async (material) => ({
            material,
            serie: await fetchSerie({ materialId: material.id, desde: desdeApi, hasta: hastaApi, token }),
          }))
        ),
      ]);
      setSerie(serieActual);
      setForecast(forecastActual);
      setCommercialPrice(commercialPriceActual);
      setComparisonRows(buildComparisonRows(comparisonResults));
    },
    [desde, forecastHorizon, hasta, materiales, selectedMaterialId, token]
  );

  const bootstrapApp = useCallback(
    async (activeToken) => {
      setLoading(true);
      setError("");
      try {
        const [materials, presentations, sources, range] = await Promise.all([
          fetchMateriales(activeToken),
          fetchPresentaciones(activeToken),
          fetchFuentes(activeToken),
          fetchPriceRange(activeToken),
        ]);
        setMateriales(materials);
        setPresentaciones(presentations);
        setFuentes(sources);

        const defaultMaterial = materials.find((material) => material.nombre.toLowerCase().includes("cemento")) || materials[0];
        const defaultMaterialId = defaultMaterial ? String(defaultMaterial.id) : "";
        const rangeDesde = range.desde ? dayjs(range.desde) : null;
        const defaultDesde = rangeDesde ? (rangeDesde.isAfter(clientDefaultStart) ? rangeDesde : clientDefaultStart) : clientDefaultStart;
        const defaultHasta = dayjs(range.hasta || range.hoy);
        const max = range.hoy ? dayjs(range.hoy) : null;

        setSelectedMaterialId(defaultMaterialId);
        setDesde(defaultDesde);
        setHasta(defaultHasta);
        setMaxDate(max);
        setDateWarning(
          range.tiene_fechas_futuras
            ? `Hay registros posteriores a hoy (${dayjs(range.hasta_real).format("DD/MM/YY")}). El analisis se limita hasta ${defaultHasta.format("DD/MM/YY")}.`
            : ""
        );

        if (defaultMaterialId) {
          const desdeApi = toApiDate(defaultDesde);
          const hastaApi = toApiDate(defaultHasta);
          const [serieActual, forecastActual, commercialPriceActual, comparisonResults] = await Promise.all([
            fetchSerie({ materialId: defaultMaterialId, desde: desdeApi, hasta: hastaApi, token: activeToken }),
            fetchForecast({ materialId: defaultMaterialId, horizonteMeses: forecastHorizon, token: activeToken }).catch(() => null),
            fetchCommercialPrice({ materialId: defaultMaterialId, horizonteMeses: forecastHorizon, token: activeToken }).catch(() => null),
            Promise.all(
              materials.map(async (material) => ({
                material,
                serie: await fetchSerie({ materialId: material.id, desde: desdeApi, hasta: hastaApi, token: activeToken }),
              }))
            ),
          ]);
          setSerie(serieActual);
          setForecast(forecastActual);
          setCommercialPrice(commercialPriceActual);
          setComparisonRows(buildComparisonRows(comparisonResults));
        }
      } catch (bootstrapError) {
        setError(bootstrapError.message);
      } finally {
        setLoading(false);
      }
    },
    [forecastHorizon]
  );

  useEffect(() => {
    let cancelled = false;
    async function init() {
      try {
        await apiGet("/health");
        if (cancelled) return;
        setApiStatus({ mode: "ok", label: "API conectada" });

        if (!token) {
          setLoading(false);
          return;
        }
      } catch (initError) {
        if (cancelled) return;
        setApiStatus({ mode: "error", label: "API no disponible" });
        setLoading(false);
        return;
      }

      if (!token) return;

      try {
        const currentUser = await fetchCurrentUser(token);
        if (cancelled) return;
        setUser(currentUser);
        await bootstrapApp(token);
      } catch (initError) {
        if (cancelled) return;
        localStorage.removeItem(TOKEN_KEY);
        setToken(null);
        setUser(null);
        setSerie([]);
        setForecast(null);
        setComparisonRows([]);
        setShowPriceForm(false);
        setError("La sesion vencio. Volve a iniciar sesion.");
        setLoading(false);
      }
    }
    init();
    return () => {
      cancelled = true;
    };
  }, [bootstrapApp, token]);

  async function handleLogin(credentials) {
    const data = await loginRequest(credentials);
    localStorage.setItem(TOKEN_KEY, data.access_token);
    setToken(data.access_token);
    setUser(data.usuario);
  }

  async function handleRegister(payload) {
    return registerRequest(payload);
  }

  function handleLogout() {
    localStorage.removeItem(TOKEN_KEY);
    setToken(null);
    setUser(null);
    setSerie([]);
    setForecast(null);
    setComparisonRows([]);
    setShowPriceForm(false);
  }

  async function handleSavePrice(payload) {
    const saved = await createPrecioHistorico(payload, token);
    setSelectedMaterialId(String(payload.material_id));
    await loadSerieData({ materialId: String(payload.material_id) });
    return saved;
  }

  async function handleRefresh() {
    setError("");
    try {
      await loadSerieData();
    } catch (refreshError) {
      setError(refreshError.message);
    }
  }

  return (
    <Box className="min-h-screen bg-md-surface-container">
      <AppHeader
        apiStatus={apiStatus}
        user={user}
        onLogout={handleLogout}
        showPrices={showPrices}
        onToggleShowPrices={(event) => {
          const nextValue = event.target.checked;
          localStorage.setItem(SHOW_PRICES_KEY, String(nextValue));
          setShowPrices(nextValue);
        }}
      />

      {!user ? (
        <LoginPage onLogin={handleLogin} onRegister={handleRegister} />
      ) : (
        <Container maxWidth="lg" className="pb-12">
          {loading ? (
            <Box className="-mt-8 flex justify-center rounded-md bg-white p-8 shadow-md1">
              <CircularProgress />
            </Box>
          ) : (
            <>
              {error ? (
                <Alert className="mb-3 -mt-8" severity="error">
                  {error}
                </Alert>
              ) : null}

              <FiltersBar
                materiales={materiales}
                selectedMaterialId={selectedMaterialId}
                desde={desde}
                hasta={hasta}
                maxDate={maxDate}
                warning={dateWarning}
                onMaterialChange={(value) => {
                  setSelectedMaterialId(value);
                  loadSerieData({ materialId: value }).catch((loadError) => setError(loadError.message));
                }}
                onDesdeChange={setDesde}
                onHastaChange={setHasta}
                onRefresh={handleRefresh}
              />

              <Card className="mt-3 overflow-hidden border border-slate-200 shadow-md1">
                <CardContent className="p-0">
                  <Box
                    className="px-4 pb-4 pt-5 text-white"
                    sx={{
                      background: `linear-gradient(135deg, ${activeTabConfig.accent} 0%, rgba(2, 6, 23, 0.92) 100%)`,
                    }}
                  >
                    <Box className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
                      <Box className="max-w-2xl">
                        <Typography variant="overline" sx={{ opacity: 0.8 }}>
                          {activeTabConfig.eyebrow}
                        </Typography>
                        <Typography mt={1} variant="h1" component="h1" lineHeight={1}>
                          {activeTabConfig.label}
                        </Typography>
                        <Typography mt={1.25} maxWidth={760} variant="body2" sx={{ color: "rgba(255,255,255,0.82)" }}>
                          {activeTabConfig.description}
                        </Typography>
                      </Box>
                      <Box className="flex flex-wrap gap-2">
                        <Chip
                          label={selectedMaterial ? selectedMaterial.nombre : "Sin material"}
                          sx={{ bgcolor: "rgba(255,255,255,0.14)", color: "white", fontWeight: 800 }}
                        />
                        <Chip
                          label={`Horizonte ${forecastHorizon} meses`}
                          sx={{ bgcolor: "rgba(255,255,255,0.14)", color: "white", fontWeight: 800 }}
                        />
                      </Box>
                    </Box>
                  </Box>
                  <Box className="border-b border-slate-200 bg-white px-2 pt-2">
                    <Box className="flex items-end overflow-x-auto">
                      <Tabs
                        value={activeView}
                        onChange={(_event, value) => setActiveView(value)}
                        variant="scrollable"
                        scrollButtons="auto"
                        allowScrollButtonsMobile
                        className="w-full"
                        sx={{
                          minHeight: 0,
                          width: "100%",
                          "& .MuiTabs-indicator": {
                            height: 4,
                            borderRadius: 999,
                            backgroundColor: activeTabConfig.accent,
                          },
                          "& .MuiTabs-flexContainer": {
                            gap: 8,
                            flexWrap: "nowrap",
                            justifyContent: "flex-start",
                          },
                        }}
                      >
                        {visibleTabs.map((tab) => (
                          <Tab
                            key={tab.value}
                            value={tab.value}
                            icon={<tab.icon fontSize="small" />}
                            iconPosition="start"
                            label={tab.label}
                            disabled={tab.disabled}
                            sx={{
                              minHeight: 0,
                              minWidth: "auto",
                              px: 2,
                              py: 1.5,
                              textTransform: "none",
                              fontSize: 14,
                              fontWeight: 800,
                              color: tab.accent,
                              "&.Mui-selected": {
                                color: activeTabConfig.accent,
                              },
                              "&.Mui-disabled": {
                                opacity: 0.45,
                                color: tab.accent,
                                fontStyle: "italic",
                              },
                            }}
                          />
                        ))}
                      </Tabs>
                    </Box>
                  </Box>
                  <Box className="bg-slate-50 px-4 py-3">
                    <Typography color="text.secondary" variant="body2" fontWeight={700}>
                      {activeTabConfig.description}
                    </Typography>
                  </Box>
                </CardContent>
              </Card>

              {activeView === "summary" ? (
                <>
                  <MetricsGrid serie={serie} showPrices={showPrices} selectedMaterial={selectedMaterial} />
                  <InsightStrip serie={serie} selectedMaterial={selectedMaterial} showPrices={showPrices} />
                  {forecast ? (
                    <Card
                      className="mt-3 overflow-hidden border border-slate-200"
                      sx={{
                        boxShadow: "0 18px 40px rgba(177, 18, 38, 0.22), 0 4px 14px rgba(15, 23, 42, 0.08)",
                      }}
                    >
                      <CardContent className="p-0">
                        <Box className="border-b border-slate-200 bg-slate-50 px-4 py-3">
                          <Typography variant="overline" color="text.secondary">
                            Lectura rápida
                          </Typography>
                          <Typography mt={0.5} variant="h3">
                            ¿Qué está mostrando el material?
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            Una síntesis simple para decidir sin leer todo el panel.
                          </Typography>
                        </Box>
                        <Box className="grid gap-3 p-4 md:grid-cols-3">
                    <Box className="rounded-xl border border-slate-200 bg-white p-3">
                      <Typography color="text.secondary" variant="body2" fontWeight={800}>
                        Tendencia esperada
                      </Typography>
                            <Typography component="strong" display="block" mt={0.75} variant="h2" lineHeight={1.1}>
                              {summaryForecastDirection}
                            </Typography>
                            <Typography color="text.secondary" variant="body2" mt={0.5}>
                        {summaryForecastDeltaPct === null ? "Sin forecast disponible" : `Variación próxima: ${formatNumber(summaryForecastDeltaPct)}%`}
                      </Typography>
                    </Box>
                    <Box className="rounded-xl border border-slate-200 bg-white p-3">
                      <Typography color="text.secondary" variant="body2" fontWeight={800}>
                        Recomendación operativa
                      </Typography>
                      <Typography component="strong" display="block" mt={0.75} variant="h3" lineHeight={1.15}>
                        {summaryForecastDeltaPct === null
                          ? "Sin decisión"
                          : summaryForecastDeltaPct > 0
                            ? "Anticipar compra"
                            : summaryForecastDeltaPct < 0
                              ? "Pedir esperar"
                              : "Revisar urgencia"}
                      </Typography>
                      <Typography color="text.secondary" variant="body2" mt={0.5}>
                        {summaryForecastRecommendation}
                      </Typography>
                    </Box>
                    <Box className="rounded-xl border border-slate-200 bg-white p-3">
                      <Typography color="text.secondary" variant="body2" fontWeight={800}>
                        Próximo precio proyectado
                            </Typography>
                            <Typography component="strong" display="block" mt={0.75} variant="h2" lineHeight={1.1}>
                              {summaryNextForecastPoint ? formatCurrency(getDisplayPrice(summaryNextForecastPoint.precio_proyectado, forecast.material_nombre, forecast.unidad_base)) : "-"}
                            </Typography>
                            <Typography color="text.secondary" variant="body2" mt={0.5}>
                              {summaryNextForecastPoint
                                ? `Primer mes proyectado: ${dayjs(summaryNextForecastPoint.fecha).format("DD/MM/YY")}`
                                : "No hay horizonte calculado"}
                            </Typography>
                          </Box>
                          <Box className="rounded-xl border border-slate-200 bg-white p-3">
                            <Typography color="text.secondary" variant="body2" fontWeight={800}>
                              Horizonte completo
                            </Typography>
                            <Typography component="strong" display="block" mt={0.75} variant="h2" lineHeight={1.1}>
                              {summaryLastForecastPoint ? formatCurrency(getDisplayPrice(summaryLastForecastPoint.precio_proyectado, forecast.material_nombre, forecast.unidad_base)) : "-"}
                            </Typography>
                            <Typography color="text.secondary" variant="body2" mt={0.5}>
                              {summaryLastForecastPoint
                                ? `Último mes proyectado: ${dayjs(summaryLastForecastPoint.fecha).format("DD/MM/YY")}`
                                : "No hay horizonte calculado"}
                            </Typography>
                          </Box>
                        </Box>
                      </CardContent>
                    </Card>
                  ) : null}
                  <ForecastModelDetails selection={summaryForecastSelection} title="Detalles del modelo" compact />
                  {showPrices && forecast && summaryNextForecastPoint && summaryShowBagEquivalents ? (
                    <Card className="mt-3 overflow-hidden border border-slate-200 shadow-md1">
                      <CardContent className="p-0">
                        <Box className="border-b border-slate-200 bg-slate-50 px-4 py-3">
                          <Typography variant="overline" color="text.secondary">
                            Resumen de cemento
                          </Typography>
                          <Typography mt={0.5} variant="h3">
                            Bolsa 25 kg / 50 kg
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            Equivalente comercial para el primer mes proyectado.
                          </Typography>
                        </Box>
                        <Box className="p-4">
                          <Typography variant="body2" fontWeight={700} color="text.secondary">
                            {dayjs(summaryNextForecastPoint.fecha).format("DD/MM/YY")}
                          </Typography>
                          <Typography mt={0.75} variant="h2" lineHeight={1.1}>
                            {`${formatCurrency(summaryNextForecastPoint.precio_equivalente_25kg)} / ${formatCurrency(summaryNextForecastPoint.precio_equivalente_50kg)}`}
                          </Typography>
                          <Typography mt={0.5} variant="body2" color="text.secondary">
                            Primer punto proyectado: {formatCurrency(getDisplayPrice(summaryNextForecastPoint.precio_proyectado, forecast.material_nombre, forecast.unidad_base))}
                          </Typography>
                        </Box>
                      </CardContent>
                    </Card>
                  ) : null}
                  <Box className="mt-3 grid gap-3 lg:grid-cols-[minmax(0,1.35fr)_minmax(320px,0.65fr)] lg:items-stretch">
                    <Box className="min-w-0 lg:flex">
                      <PriceChart
                        serie={serie}
                        forecast={forecast}
                        selectedMaterial={selectedMaterial}
                        showPrices={showPrices}
                      />
                    </Box>
                    <Box className="min-w-0 lg:flex">
                      <ComparisonCard rows={comparisonRows} selectedMaterialId={selectedMaterialId} showPrices={showPrices} compact />
                    </Box>
                  </Box>
                </>
              ) : null}

              {activeView === "forecast" ? (
                <>
                  <ForecastCard
                    forecast={forecast}
                    serie={serie}
                    horizonteMeses={forecastHorizon}
                    showPrices={showPrices}
                    onChangeHorizon={(value) => {
                      setForecastHorizon(value);
                      loadSerieData({ materialId: selectedMaterialId, horizon: value }).catch((loadError) => setError(loadError.message));
                    }}
                  />
                  {showPrices ? (
                    <Box
                      className="mt-3 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-white px-4 py-3"
                      sx={{
                        boxShadow: "0 14px 34px rgba(177, 18, 38, 0.12), 0 4px 14px rgba(15, 23, 42, 0.06)",
                      }}
                    >
                      <Box>
                        <Typography variant="body2" fontWeight={800} color="text.secondary">
                          Cómo ver la curva
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          Elegí si querés ver el costo, la venta minorista o ambas curvas superpuestas.
                        </Typography>
                      </Box>
                      <ButtonGroup size="small" variant="outlined">
                        <Button variant={forecastPriceView === "base" ? "contained" : "outlined"} onClick={() => setForecastPriceView("base")}>
                          Solo costo
                        </Button>
                        <Button variant={forecastPriceView === "commercial" ? "contained" : "outlined"} onClick={() => setForecastPriceView("commercial")}>
                          Solo venta minorista
                        </Button>
                        <Button variant={forecastPriceView === "comparative" ? "contained" : "outlined"} onClick={() => setForecastPriceView("comparative")}>
                          Comparar ambas
                        </Button>
                      </ButtonGroup>
                    </Box>
                  ) : null}
                  {forecast ? (
                    <Card className="mt-3 overflow-hidden border border-slate-200 shadow-md1">
                      <CardContent className="p-0">
                        <Box className="border-b border-slate-200 bg-slate-50 px-4 py-3">
                          <Typography variant="overline" color="text.secondary">
                            Síntesis del forecast
                          </Typography>
                          <Typography mt={0.5} variant="h3">
                            ¿Qué me dice la proyección?
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            La lectura más simple del modelo para usarla sin interpretar toda la tabla.
                          </Typography>
                        </Box>
                        <Box className="grid gap-3 p-4 md:grid-cols-3">
                          <Box className="rounded-xl border border-slate-200 bg-white p-3">
                            <Typography color="text.secondary" variant="body2" fontWeight={800}>
                              Dirección
                            </Typography>
                            <Typography component="strong" display="block" mt={0.75} variant="h2" lineHeight={1.1}>
                              {summaryForecastDirection}
                            </Typography>
                            <Typography color="text.secondary" variant="body2" mt={0.5}>
                              {summaryForecastDeltaPct === null ? "Sin forecast disponible" : `Cambio estimado: ${formatNumber(summaryForecastDeltaPct)}%`}
                            </Typography>
                          </Box>
                          <Box className="rounded-xl border border-slate-200 bg-white p-3">
                            <Typography color="text.secondary" variant="body2" fontWeight={800}>
                              Próximo mes
                            </Typography>
                            <Typography component="strong" display="block" mt={0.75} variant="h2" lineHeight={1.1}>
                              {summaryNextForecastPoint ? formatCurrency(getDisplayPrice(summaryNextForecastPoint.precio_proyectado, forecast.material_nombre, forecast.unidad_base)) : "-"}
                            </Typography>
                            <Typography color="text.secondary" variant="body2" mt={0.5}>
                              {summaryNextForecastPoint
                                ? dayjs(summaryNextForecastPoint.fecha).format("DD/MM/YY")
                                : "No hay horizonte calculado"}
                            </Typography>
                          </Box>
                          <Box className="rounded-xl border border-slate-200 bg-white p-3">
                            <Typography color="text.secondary" variant="body2" fontWeight={800}>
                              Horizonte completo
                            </Typography>
                            <Typography component="strong" display="block" mt={0.75} variant="h2" lineHeight={1.1}>
                              {summaryLastForecastPoint ? formatCurrency(getDisplayPrice(summaryLastForecastPoint.precio_proyectado, forecast.material_nombre, forecast.unidad_base)) : "-"}
                            </Typography>
                            <Typography color="text.secondary" variant="body2" mt={0.5}>
                              {summaryLastForecastPoint ? dayjs(summaryLastForecastPoint.fecha).format("DD/MM/YY") : "No hay horizonte calculado"}
                            </Typography>
                          </Box>
                        </Box>
                      </CardContent>
                    </Card>
                  ) : null}
                  <ForecastModelDetails selection={summaryForecastSelection} title="Detalles del modelo" compact />
                  <PriceChart
                    className="mt-3"
                    serie={serie}
                    forecast={forecast}
                    selectedMaterial={selectedMaterial}
                    showPrices={showPrices}
                    chartMode={forecastPriceView}
                    commercialMarginPct={commercialPrice?.margen_ganancia_pct ?? null}
                  />
                </>
              ) : null}

              {activeView === "costs" ? (
                <>
                  <PurchaseDecisionCard
                    materiales={materiales}
                    selectedMaterialId={selectedMaterialId}
                    forecastHorizon={forecastHorizon}
                    token={token}
                    showPrices={showPrices}
                  />
                  <CostProjectionCard forecast={forecast} selectedMaterial={selectedMaterial} showPrices={showPrices} />
                  <CostPlannerCard
                    materiales={materiales}
                    selectedMaterialId={selectedMaterialId}
                    forecastHorizon={forecastHorizon}
                    token={token}
                    showPrices={showPrices}
                  />
                </>
              ) : null}

              {activeView === "history" ? (
                <>
                  <PriceChart
                    className="mt-3"
                    serie={serie}
                    forecast={forecast}
                    selectedMaterial={selectedMaterial}
                    showPrices={showPrices}
                    action={
                      isAdmin ? (
                        <Button
                          variant="outlined"
                          color="secondary"
                          startIcon={showPriceForm ? <ExpandLessIcon /> : <AddIcon />}
                          onClick={() => setShowPriceForm((current) => !current)}
                        >
                          {showPriceForm ? "Ocultar carga" : "Registrar precio"}
                        </Button>
                      ) : null
                    }
                  />

                  {isAdmin && showPriceForm ? (
                    <PriceForm
                      materiales={materiales}
                      presentaciones={presentaciones}
                      fuentes={fuentes}
                      maxDate={maxDate}
                      onSave={handleSavePrice}
                    />
                  ) : null}

                  <Box className="mt-3 grid gap-3 lg:grid-cols-2 lg:items-stretch">
                    <AnomaliesCard serie={serie} showPrices={showPrices} selectedMaterial={selectedMaterial} />
                    <HistoryTable serie={serie} showPrices={showPrices} selectedMaterial={selectedMaterial} />
                  </Box>
                </>
              ) : null}

              {isAdmin && activeView === "admin" ? (
                <>
                  <UsersAdmin token={token} />
                  <CommercialMarginsAdmin token={token} materiales={materiales} presentaciones={presentaciones} />
                </>
              ) : null}

            </>
          )}
        </Container>
      )}
    </Box>
  );
}
