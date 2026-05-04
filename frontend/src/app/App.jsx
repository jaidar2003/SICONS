import AddIcon from "@mui/icons-material/Add";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import { Alert, Box, Button, CircularProgress, Container } from "@mui/material";
import dayjs from "dayjs";
import { useCallback, useEffect, useMemo, useState } from "react";

import { PriceForm } from "../features/admin/PriceForm.jsx";
import { fetchCurrentUser, loginRequest } from "../features/auth/auth.api.js";
import { LoginPage } from "../features/auth/LoginPage.jsx";
import { fetchFuentes, fetchMateriales, fetchPresentaciones } from "../features/catalog/catalog.api.js";
import { AppHeader } from "../features/layout/AppHeader.jsx";
import { AnomaliesCard } from "../features/pricing/AnomaliesCard.jsx";
import { ComparisonCard } from "../features/pricing/ComparisonCard.jsx";
import { CostPlannerCard } from "../features/pricing/CostPlannerCard.jsx";
import { CostProjectionCard } from "../features/pricing/CostProjectionCard.jsx";
import { FiltersBar } from "../features/pricing/FiltersBar.jsx";
import { ForecastCard } from "../features/pricing/ForecastCard.jsx";
import { HistoryTable } from "../features/pricing/HistoryTable.jsx";
import { InsightStrip } from "../features/pricing/InsightStrip.jsx";
import { MetricsGrid } from "../features/pricing/MetricsGrid.jsx";
import { PriceChart } from "../features/pricing/PriceChart.jsx";
import { createPrecioHistorico, fetchForecast, fetchPriceRange, fetchSerie } from "../features/pricing/pricing.api.js";
import { apiGet } from "../shared/api/http.js";
import { toApiDate } from "../shared/utils/formatters.js";

const TOKEN_KEY = "sicons_token";
const SHOW_PRICES_KEY = "sicons_show_prices";

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
  const [forecastHorizon, setForecastHorizon] = useState(3);
  const [comparisonRows, setComparisonRows] = useState([]);
  const [showPriceForm, setShowPriceForm] = useState(false);

  const selectedMaterial = useMemo(
    () => materiales.find((material) => String(material.id) === String(selectedMaterialId)),
    [materiales, selectedMaterialId]
  );
  const isAdmin = user?.rol === "admin";

  const loadSerieData = useCallback(
    async ({ materialId = selectedMaterialId, from = desde, to = hasta, horizon = forecastHorizon } = {}) => {
      if (!materialId) return;
      const desdeApi = toApiDate(from);
      const hastaApi = toApiDate(to);
      const [serieActual, forecastActual, comparisonResults] = await Promise.all([
        fetchSerie({ materialId, desde: desdeApi, hasta: hastaApi, token }),
        fetchForecast({ materialId, horizonteMeses: horizon, token }).catch(() => null),
        Promise.all(
          materiales.map(async (material) => ({
            material,
            serie: await fetchSerie({ materialId: material.id, desde: desdeApi, hasta: hastaApi, token }),
          }))
        ),
      ]);
      setSerie(serieActual);
      setForecast(forecastActual);
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
        const defaultDesde = range.desde ? dayjs(range.desde) : null;
        const defaultHasta = dayjs(range.hasta || range.hoy);
        const max = range.hoy ? dayjs(range.hoy) : null;

        setSelectedMaterialId(defaultMaterialId);
        setDesde(defaultDesde);
        setHasta(defaultHasta);
        setMaxDate(max);
        setDateWarning(range.tiene_fechas_futuras ? `Hay registros posteriores a hoy (${range.hasta_real}). El analisis se limita hasta ${defaultHasta.format("YYYY-MM-DD")}.` : "");

        if (defaultMaterialId) {
          const desdeApi = toApiDate(defaultDesde);
          const hastaApi = toApiDate(defaultHasta);
          const [serieActual, forecastActual, comparisonResults] = await Promise.all([
            fetchSerie({ materialId: defaultMaterialId, desde: desdeApi, hasta: hastaApi, token: activeToken }),
            fetchForecast({ materialId: defaultMaterialId, horizonteMeses: forecastHorizon, token: activeToken }).catch(() => null),
            Promise.all(
              materials.map(async (material) => ({
                material,
                serie: await fetchSerie({ materialId: material.id, desde: desdeApi, hasta: hastaApi, token: activeToken }),
              }))
            ),
          ]);
          setSerie(serieActual);
          setForecast(forecastActual);
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
    await bootstrapApp(data.access_token);
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
        <LoginPage onLogin={handleLogin} />
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

              <MetricsGrid serie={serie} showPrices={showPrices} />
              <InsightStrip serie={serie} selectedMaterial={selectedMaterial} showPrices={showPrices} />
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
              <CostProjectionCard forecast={forecast} selectedMaterial={selectedMaterial} showPrices={showPrices} />
              <CostPlannerCard
                materiales={materiales}
                selectedMaterialId={selectedMaterialId}
                forecastHorizon={forecastHorizon}
                token={token}
                showPrices={showPrices}
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

              <PriceChart
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

              <Box className="mt-3 grid gap-3 lg:grid-cols-[.6fr_1.4fr]">
                <AnomaliesCard serie={serie} showPrices={showPrices} />
                <ComparisonCard rows={comparisonRows} selectedMaterialId={selectedMaterialId} showPrices={showPrices} />
              </Box>

              <HistoryTable serie={serie} showPrices={showPrices} />
            </>
          )}
        </Container>
      )}
    </Box>
  );
}
