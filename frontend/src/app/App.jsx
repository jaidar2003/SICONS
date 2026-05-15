import AutoGraphIconModule from "@mui/icons-material/AutoGraph";
import AdminPanelSettingsOutlinedIconModule from "@mui/icons-material/AdminPanelSettingsOutlined";
import Inventory2OutlinedIconModule from "@mui/icons-material/Inventory2Outlined";
import SavingsOutlinedIconModule from "@mui/icons-material/SavingsOutlined";
import TimelineOutlinedIconModule from "@mui/icons-material/TimelineOutlined";
import {
  Alert,
  Box,
  Button,
  ButtonGroup,
  Card,
  CardContent,
  CircularProgress,
  Divider,
  Typography,
} from "@mui/material";
import dayjs from "dayjs";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { PriceForm } from "../features/admin/PriceForm.jsx";
import { LoginPage } from "../features/auth/LoginPage.jsx";
import { useAuthSession } from "../features/auth/useAuthSession.js";
import { AppHeader } from "../features/layout/AppHeader.jsx";
import { AnomaliesCard } from "../features/pricing/AnomaliesCard.jsx";
import { ComparisonCard } from "../features/pricing/ComparisonCard.jsx";
import { CostPlannerCard } from "../features/pricing/CostPlannerCard.jsx";
import { CostProjectionCard } from "../features/pricing/CostProjectionCard.jsx";
import { FinalDecisionCard } from "../features/pricing/FinalDecisionCard.jsx";
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
import { PriceVariationBetweenDatesCard } from "../features/pricing/PriceVariationBetweenDatesCard.jsx";
import { PurchaseScenarioSimulationCard } from "../features/pricing/PurchaseScenarioSimulationCard.jsx";
import { createPrecioHistorico } from "../features/pricing/pricing.api.js";
import { getDisplayPrice } from "../features/pricing/materialPresentation.js";
import { apiGet } from "../shared/api/http.js";
import { resolveMuiIcon } from "../shared/components/resolveMuiIcon.js";
import { formatCurrency, formatNumber } from "../shared/utils/formatters.js";
import { loadForecastExtras, loadInitialAppData, loadMaterialAnalysis } from "./appData.js";
import { AppViewHeader } from "./AppViewHeader.jsx";
import { brand } from "./brand.js";

const SHOW_PRICES_KEY = "sicons_show_prices";
const AutoGraphIcon = resolveMuiIcon(AutoGraphIconModule);
const AdminPanelSettingsOutlinedIcon = resolveMuiIcon(AdminPanelSettingsOutlinedIconModule);
const Inventory2OutlinedIcon = resolveMuiIcon(Inventory2OutlinedIconModule);
const SavingsOutlinedIcon = resolveMuiIcon(SavingsOutlinedIconModule);
const TimelineOutlinedIcon = resolveMuiIcon(TimelineOutlinedIconModule);
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

const COST_WORKFLOWS = [
  {
    value: "planner",
    label: "Armar presupuesto",
    helper: "Cargá varios materiales, cantidades, criticidad y presupuesto.",
  },
  {
    value: "final",
    label: "Qué comprar",
    helper: "Recomendación final: comprar ahora, compra parcial o postergar.",
  },
  {
    value: "single",
    label: "Analizar material",
    helper: "Recomendación y estrategias para un solo material.",
  },
  {
    value: "scenarios",
    label: "Comparar meses",
    helper: "Compará escenarios de 3, 6 y 12 meses.",
  },
  {
    value: "quantity",
    label: "Calcular cantidad",
    helper: "Estimá el costo futuro según una cantidad puntual.",
  },
];

const FORECAST_WORKFLOWS = [
  {
    value: "projection",
    label: "Proyección",
    helper: "Horizonte, próximos precios y lectura simple.",
  },
  {
    value: "chart",
    label: "Gráfico",
    helper: "Curva histórica y proyectada del material.",
  },
  {
    value: "model",
    label: "Modelo",
    helper: "MAPE, MAE, calibración y selección técnica.",
  },
];

const HISTORY_WORKFLOWS = [
  {
    value: "variation",
    label: "Variación",
    helper: "Comparar precios entre dos fechas.",
  },
  {
    value: "chart",
    label: "Gráfico",
    helper: "Ver la serie histórica completa.",
  },
  {
    value: "anomalies",
    label: "Anomalías",
    helper: "Detectar saltos bruscos de precio.",
  },
  {
    value: "table",
    label: "Tabla",
    helper: "Revisar registros históricos.",
  },
  {
    value: "load",
    label: "Cargar precio",
    helper: "Alta administrativa de precios históricos.",
    adminOnly: true,
  },
];

const ADMIN_WORKFLOWS = [
  {
    value: "users",
    label: "Usuarios",
    helper: "Administrar accesos y roles.",
  },
  {
    value: "margins",
    label: "Márgenes",
    helper: "Configurar márgenes comerciales.",
  },
];

export function App() {
  const { token, user, login, register, loadCurrentUser, clearSession } = useAuthSession();
  const [showPrices, setShowPrices] = useState(() => localStorage.getItem(SHOW_PRICES_KEY) !== "false");
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
  const [forecastLoading, setForecastLoading] = useState(false);
  const [forecastHorizon, setForecastHorizon] = useState(3);
  const [forecastPriceView, setForecastPriceView] = useState("comparative");
  const [comparisonRows, setComparisonRows] = useState([]);
  const [activeView, setActiveView] = useState("summary");
  const [costWorkflow, setCostWorkflow] = useState("planner");
  const [forecastWorkflow, setForecastWorkflow] = useState("projection");
  const [historyWorkflow, setHistoryWorkflow] = useState("variation");
  const [adminWorkflow, setAdminWorkflow] = useState("users");
  const forecastRequestRef = useRef(0);
  const clientDefaultStart = useMemo(() => dayjs("2026-01-01"), []);

  const selectedMaterial = useMemo(
    () => materiales.find((material) => String(material.id) === String(selectedMaterialId)),
    [materiales, selectedMaterialId]
  );
  const isAdmin = user?.rol === "admin";
  const visibleTabs = useMemo(() => VIEW_TABS.filter((tab) => tab.value !== "admin" || isAdmin), [isAdmin]);
  const visibleHistoryWorkflows = useMemo(
    () => HISTORY_WORKFLOWS.filter((workflow) => !workflow.adminOnly || isAdmin),
    [isAdmin]
  );
  const activeTabConfig = useMemo(
    () => visibleTabs.find((tab) => tab.value === activeView) ?? visibleTabs[0],
    [activeView, visibleTabs]
  );
  const forecastChartMode = isAdmin ? forecastPriceView : "commercial";
  const summaryNextForecastPoint = forecast?.puntos?.[0] || null;
  const summaryLastForecastPoint = forecast?.puntos?.[forecast?.puntos?.length - 1] || null;
  const summaryForecastSelection = forecast?.seleccion_modelo || null;
  const summaryForecastDeltaPct =
    forecast && summaryNextForecastPoint
      ? ((Number(summaryNextForecastPoint.precio_proyectado) - Number(forecast.ultimo_precio_observado)) / Number(forecast.ultimo_precio_observado)) * 100
      : null;
  const summaryForecastConfidence = String(summaryForecastSelection?.confiabilidad || "").toLowerCase();
  const summaryForecastRecommendation =
    forecastLoading
      ? "Preparando forecast sin bloquear la navegacion."
      : summaryForecastDeltaPct === null
      ? "Sin forecast disponible."
      : summaryForecastDeltaPct > 0
        ? summaryForecastConfidence === "baja"
          ? "El precio tiende a subir, pero la confianza es baja. Conviene monitorear antes de decidir."
          : "El precio tiende a subir. Conviene anticipar compra si el presupuesto lo permite."
        : summaryForecastDeltaPct < 0
          ? "El precio tiende a bajar. Conviene esperar si la urgencia lo permite."
          : "El precio luce estable. La decisión depende más de la urgencia y del presupuesto.";
  const summaryForecastDirection =
    forecastLoading
      ? "Calculando forecast"
      : summaryForecastDeltaPct === null
      ? "Sin proyeccion"
      : summaryForecastDeltaPct > 0
        ? "Tendencia alcista"
        : summaryForecastDeltaPct < 0
          ? "Tendencia bajista"
          : "Tendencia estable";

  useEffect(() => {
    if (!visibleTabs.some((tab) => tab.value === activeView)) {
      setActiveView(visibleTabs[0]?.value ?? "summary");
    }
  }, [activeView, visibleTabs]);

  useEffect(() => {
    if (!visibleHistoryWorkflows.some((workflow) => workflow.value === historyWorkflow)) {
      setHistoryWorkflow(visibleHistoryWorkflows[0]?.value ?? "variation");
    }
  }, [historyWorkflow, visibleHistoryWorkflows]);

  const loadForecastData = useCallback(
    async ({ materialId, horizon, activeToken }) => {
      if (!materialId || !activeToken) return;

      const requestId = forecastRequestRef.current + 1;
      forecastRequestRef.current = requestId;
      setForecastLoading(true);

      try {
        const result = await loadForecastExtras({ materialId, horizon, token: activeToken });
        if (forecastRequestRef.current !== requestId) return;
        setForecast(result.forecast);
        setCommercialPrice(result.commercialPrice);
      } catch {
        if (forecastRequestRef.current !== requestId) return;
        setForecast(null);
        setCommercialPrice(null);
      } finally {
        if (forecastRequestRef.current === requestId) {
          setForecastLoading(false);
        }
      }
    },
    []
  );

  const loadSerieData = useCallback(
    async ({ materialId = selectedMaterialId, from = desde, to = hasta, horizon = forecastHorizon } = {}) => {
      const result = await loadMaterialAnalysis({
        materialId,
        from,
        to,
        horizon,
        materials: materiales,
        token,
        includeForecast: false,
        includeCommercial: false,
        includeComparison: true,
      });
      setSerie(result.serie);
      setForecast(null);
      setCommercialPrice(null);
      setComparisonRows(result.comparisonRows);
      loadForecastData({ materialId, horizon, activeToken: token }).catch(() => {});
    },
    [desde, forecastHorizon, hasta, loadForecastData, materiales, selectedMaterialId, token]
  );

  const resetWorkspaceState = useCallback(() => {
    forecastRequestRef.current += 1;
    setSerie([]);
    setForecast(null);
    setCommercialPrice(null);
    setForecastLoading(false);
    setComparisonRows([]);
  }, []);

  const bootstrapApp = useCallback(
    async (activeToken) => {
      setLoading(true);
      setError("");
      try {
        const data = await loadInitialAppData({ token: activeToken, forecastHorizon, clientDefaultStart });
        setMateriales(data.materiales);
        setPresentaciones(data.presentaciones);
        setFuentes(data.fuentes);
        setSelectedMaterialId(data.selectedMaterialId);
        setDesde(data.desde);
        setHasta(data.hasta);
        setMaxDate(data.maxDate);
        setDateWarning(data.dateWarning);
        setSerie(data.serie);
        setForecast(null);
        setCommercialPrice(null);
        setComparisonRows(data.comparisonRows);
        loadForecastData({
          materialId: data.selectedMaterialId,
          horizon: forecastHorizon,
          activeToken,
        }).catch(() => {});
      } catch (bootstrapError) {
        setError(bootstrapError.message);
      } finally {
        setLoading(false);
      }
    },
    [clientDefaultStart, forecastHorizon, loadForecastData]
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
      } catch {
        if (cancelled) return;
        setApiStatus({ mode: "error", label: "API no disponible" });
        setLoading(false);
        return;
      }

      if (!token) return;

      try {
        await loadCurrentUser(token);
        if (cancelled) return;
        await bootstrapApp(token);
      } catch {
        if (cancelled) return;
        clearSession();
        resetWorkspaceState();
        setError("La sesion vencio. Volve a iniciar sesion.");
        setLoading(false);
      }
    }
    init();
    return () => {
      cancelled = true;
    };
  }, [bootstrapApp, clearSession, loadCurrentUser, resetWorkspaceState, token]);

  function handleLogout() {
    clearSession();
    resetWorkspaceState();
  }

  async function handleSavePrice(payload) {
    const saved = await createPrecioHistorico(payload, token);
    setSelectedMaterialId(String(payload.material_id));
    await loadSerieData({ materialId: String(payload.material_id) });
    return saved;
  }

  function handleMaterialChange(value) {
    setSelectedMaterialId(value);
    loadSerieData({ materialId: value }).catch((loadError) => setError(loadError.message));
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
        <LoginPage onLogin={login} onRegister={register} />
      ) : (
        <Box className="mx-auto w-[95%] max-w-[1600px] pb-12">
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

              <AppViewHeader
                activeView={activeView}
                activeTabConfig={activeTabConfig}
                forecastHorizon={forecastHorizon}
                selectedMaterial={selectedMaterial}
                visibleTabs={visibleTabs}
                onViewChange={setActiveView}
              />

              {activeView === "summary" ? (
                <>
                  <FiltersBar
                    className="mt-3"
                    materiales={materiales}
                    selectedMaterialId={selectedMaterialId}
                    desde={desde}
                    hasta={hasta}
                    maxDate={maxDate}
                    warning={dateWarning}
                    onMaterialChange={handleMaterialChange}
                    onDesdeChange={setDesde}
                    onHastaChange={setHasta}
                    onRefresh={handleRefresh}
                  />
                  <MetricsGrid serie={serie} showPrices={showPrices} selectedMaterial={selectedMaterial} />
                  <InsightStrip serie={serie} selectedMaterial={selectedMaterial} showPrices={showPrices} />
                  {forecast ? (
                    <Card
                      className="mt-3 overflow-hidden border border-slate-200"
                      sx={{
                        boxShadow: "0 10px 24px rgba(15, 23, 42, 0.08)",
                      }}
                    >
                      <CardContent className="p-0">
                        <Box className="grid gap-0 md:grid-cols-[minmax(0,1fr)_320px]">
                          <Box className="p-4 md:p-5">
                            <Typography variant="overline" color="text.secondary">
                              Recomendación
                            </Typography>
                            <Typography mt={0.75} variant="h2" lineHeight={1.1}>
                              {summaryForecastDeltaPct === null
                                ? "Sin decisión"
                                : summaryForecastDeltaPct > 0
                                  ? "Anticipar compra"
                                  : summaryForecastDeltaPct < 0
                                    ? "Esperar si no es urgente"
                                    : "Revisar urgencia"}
                            </Typography>
                            <Typography mt={1} color="text.secondary">
                              {summaryForecastRecommendation}
                            </Typography>
                          </Box>
                          <Box className="grid gap-3 border-t border-slate-200 bg-slate-50 p-4 md:border-l md:border-t-0">
                            <Box>
                              <Typography color="text.secondary" variant="body2" fontWeight={800}>
                                Tendencia
                              </Typography>
                              <Typography mt={0.25} fontWeight={900}>
                                {summaryForecastDirection}
                              </Typography>
                              <Typography color="text.secondary" variant="body2">
                                {summaryForecastDeltaPct === null ? "Sin forecast disponible" : `${formatNumber(summaryForecastDeltaPct)}% próximo mes`}
                              </Typography>
                            </Box>
                            <Divider />
                            <Box>
                              <Typography color="text.secondary" variant="body2" fontWeight={800}>
                                Próximo precio
                              </Typography>
                              <Typography mt={0.25} fontWeight={900}>
                                {summaryNextForecastPoint ? formatCurrency(getDisplayPrice(summaryNextForecastPoint.precio_proyectado, forecast.material_nombre, forecast.unidad_base)) : "-"}
                              </Typography>
                              <Typography color="text.secondary" variant="body2">
                                {summaryNextForecastPoint ? dayjs(summaryNextForecastPoint.fecha).format("DD/MM/YY") : "Sin horizonte"}
                              </Typography>
                            </Box>
                          </Box>
                        </Box>
                      </CardContent>
                    </Card>
                  ) : null}
                  <ComparisonCard rows={comparisonRows} selectedMaterialId={selectedMaterialId} showPrices={showPrices} compact className="mt-3" />
                </>
              ) : null}

              {activeView === "forecast" ? (
                <>
                  <FiltersBar
                    className="mt-3"
                    materiales={materiales}
                    selectedMaterialId={selectedMaterialId}
                    desde={desde}
                    hasta={hasta}
                    maxDate={maxDate}
                    warning={dateWarning}
                    onMaterialChange={handleMaterialChange}
                    onDesdeChange={setDesde}
                    onHastaChange={setHasta}
                    onRefresh={handleRefresh}
                  />

                  <WorkflowSwitcher
                    eyebrow="Flujo de forecast"
                    title="Elegí qué querés revisar"
                    workflows={FORECAST_WORKFLOWS}
                    activeValue={forecastWorkflow}
                    onChange={setForecastWorkflow}
                  />

                  {forecastWorkflow === "projection" ? (
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
                    </>
                  ) : null}

                  {forecastWorkflow === "model" ? (
                    <ForecastModelDetails selection={summaryForecastSelection} title="Detalles del modelo" compact />
                  ) : null}

                  {forecastWorkflow === "chart" ? (
                    <>
                      {showPrices && isAdmin ? (
                        <Box
                          className="mt-3 flex flex-wrap items-center justify-between gap-3 rounded-md border border-slate-200 bg-white px-4 py-3"
                          sx={{
                            boxShadow: "0 8px 20px rgba(15, 23, 42, 0.06)",
                          }}
                        >
                          <Box>
                            <Typography variant="body2" fontWeight={800} color="text.secondary">
                              Cómo ver la curva
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                              Elegí el precio que querés ver en el gráfico.
                            </Typography>
                          </Box>
                          <ButtonGroup size="small" variant="outlined">
                            <Button variant={forecastPriceView === "base" ? "contained" : "outlined"} onClick={() => setForecastPriceView("base")}>
                              Solo costo
                            </Button>
                            <Button variant={forecastPriceView === "commercial" ? "contained" : "outlined"} onClick={() => setForecastPriceView("commercial")}>
                              Solo venta mayorista
                            </Button>
                            <Button variant={forecastPriceView === "comparative" ? "contained" : "outlined"} onClick={() => setForecastPriceView("comparative")}>
                              Comparar ambas
                            </Button>
                          </ButtonGroup>
                        </Box>
                      ) : null}
                      <PriceChart
                        className="mt-3"
                        serie={serie}
                        forecast={forecast}
                        selectedMaterial={selectedMaterial}
                        showPrices={showPrices}
                        chartMode={forecastChartMode}
                        commercialMarginPct={commercialPrice?.margen_ganancia_pct ?? null}
                        canShowCostDetails={isAdmin}
                      />
                    </>
                  ) : null}
                </>
              ) : null}

              {activeView === "costs" ? (
                <>
                  <WorkflowSwitcher
                    eyebrow="Flujo de costos"
                    title="Elegí una tarea para trabajar"
                    workflows={COST_WORKFLOWS}
                    activeValue={costWorkflow}
                    onChange={setCostWorkflow}
                  />

                  {costWorkflow === "planner" ? (
                    <CostPlannerCard
                      materiales={materiales}
                      selectedMaterialId={selectedMaterialId}
                      forecastHorizon={forecastHorizon}
                      token={token}
                      showPrices={showPrices}
                    />
                  ) : null}

                  {costWorkflow === "final" ? (
                    <FinalDecisionCard
                      materiales={materiales}
                      forecastHorizon={forecastHorizon}
                      token={token}
                      showPrices={showPrices}
                    />
                  ) : null}

                  {costWorkflow === "single" ? (
                    <PurchaseDecisionCard
                      materiales={materiales}
                      selectedMaterialId={selectedMaterialId}
                      forecastHorizon={forecastHorizon}
                      token={token}
                      showPrices={showPrices}
                    />
                  ) : null}

                  {costWorkflow === "scenarios" ? (
                    <PurchaseScenarioSimulationCard
                      materiales={materiales}
                      selectedMaterialId={selectedMaterialId}
                      token={token}
                      showPrices={showPrices}
                    />
                  ) : null}

                  {costWorkflow === "quantity" ? (
                    <CostProjectionCard forecast={forecast} selectedMaterial={selectedMaterial} showPrices={showPrices} />
                  ) : null}
                </>
              ) : null}

              {activeView === "history" ? (
                <>
                  <FiltersBar
                    className="mt-3"
                    materiales={materiales}
                    selectedMaterialId={selectedMaterialId}
                    desde={desde}
                    hasta={hasta}
                    maxDate={maxDate}
                    warning={dateWarning}
                    onMaterialChange={handleMaterialChange}
                    onDesdeChange={setDesde}
                    onHastaChange={setHasta}
                    onRefresh={handleRefresh}
                  />

                  <WorkflowSwitcher
                    eyebrow="Flujo de historial"
                    title="Elegí cómo revisar los datos"
                    workflows={visibleHistoryWorkflows}
                    activeValue={historyWorkflow}
                    onChange={setHistoryWorkflow}
                  />

                  {historyWorkflow === "variation" ? (
                    <PriceVariationBetweenDatesCard
                      selectedMaterial={selectedMaterial}
                      serie={serie}
                      token={token}
                      showPrices={showPrices}
                    />
                  ) : null}

                  {historyWorkflow === "chart" ? (
                    <PriceChart
                      className="mt-3"
                      serie={serie}
                      forecast={forecast}
                      selectedMaterial={selectedMaterial}
                      showPrices={showPrices}
                      chartMode={forecastChartMode}
                      commercialMarginPct={commercialPrice?.margen_ganancia_pct ?? null}
                      canShowCostDetails={isAdmin}
                    />
                  ) : null}

                  {isAdmin && historyWorkflow === "load" ? (
                    <PriceForm
                      materiales={materiales}
                      presentaciones={presentaciones}
                      fuentes={fuentes}
                      maxDate={maxDate}
                      onSave={handleSavePrice}
                    />
                  ) : null}

                  {historyWorkflow === "anomalies" ? (
                    <AnomaliesCard serie={serie} showPrices={showPrices} selectedMaterial={selectedMaterial} />
                  ) : null}

                  {historyWorkflow === "table" ? (
                    <HistoryTable serie={serie} showPrices={showPrices} selectedMaterial={selectedMaterial} />
                  ) : null}
                </>
              ) : null}

              {isAdmin && activeView === "admin" ? (
                <>
                  <WorkflowSwitcher
                    eyebrow="Flujo de administración"
                    title="Elegí qué querés configurar"
                    workflows={ADMIN_WORKFLOWS}
                    activeValue={adminWorkflow}
                    onChange={setAdminWorkflow}
                  />
                  {adminWorkflow === "users" ? <UsersAdmin token={token} /> : null}
                  {adminWorkflow === "margins" ? (
                    <CommercialMarginsAdmin token={token} materiales={materiales} presentaciones={presentaciones} />
                  ) : null}
                </>
              ) : null}

            </>
          )}
        </Box>
      )}
    </Box>
  );
}

function WorkflowSwitcher({ eyebrow, title, workflows, activeValue, onChange }) {
  const activeWorkflow = workflows.find((workflow) => workflow.value === activeValue) || workflows[0];

  return (
    <Box className="mt-3 rounded-md border border-slate-200 bg-white p-3 shadow-md1">
      <Box className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <Box>
          <Typography variant="body2" fontWeight={900} color="text.secondary">
            {eyebrow}
          </Typography>
          <Typography variant="h3" mt={0.25}>
            {title}
          </Typography>
        </Box>
        <ButtonGroup size="small" variant="outlined">
          {workflows.map((workflow) => (
            <Button
              key={workflow.value}
              variant={activeValue === workflow.value ? "contained" : "outlined"}
              onClick={() => onChange(workflow.value)}
            >
              {workflow.label}
            </Button>
          ))}
        </ButtonGroup>
      </Box>
      <Typography color="text.secondary" variant="body2" mt={1.5}>
        {activeWorkflow?.helper}
      </Typography>
    </Box>
  );
}
