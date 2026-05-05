import { useEffect, useMemo, useState } from "react";
import { fetchForecast } from "./pricing.api.js";

function createEmptyRow(materialId = "") {
  return {
    id: crypto.randomUUID(),
    materialId,
    quantity: "100",
  };
}

export function useCostPlanner({ materiales, selectedMaterialId, forecastHorizon, token }) {
  const [rows, setRows] = useState(() => [createEmptyRow(selectedMaterialId || "")]);
  const [forecastsByMaterial, setForecastsByMaterial] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    setRows((current) => {
      if (current.some((row) => row.materialId)) return current;
      return [createEmptyRow(selectedMaterialId || "")];
    });
  }, [selectedMaterialId]);

  const activeMaterialIds = useMemo(
    () => [...new Set(rows.map((row) => row.materialId).filter(Boolean))],
    [rows]
  );

  useEffect(() => {
    let cancelled = false;

    async function loadForecasts() {
      if (!activeMaterialIds.length) {
        setForecastsByMaterial({});
        return;
      }

      setLoading(true);
      setError("");
      try {
        const results = await Promise.all(
          activeMaterialIds.map(async (materialId) => [
            materialId,
            await fetchForecast({ materialId, horizonteMeses: forecastHorizon, token }),
          ])
        );
        if (cancelled) return;
        setForecastsByMaterial(Object.fromEntries(results));
      } catch (loadError) {
        if (cancelled) return;
        setError(loadError.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    loadForecasts();
    return () => {
      cancelled = true;
    };
  }, [activeMaterialIds, forecastHorizon, token]);

  const plannerRows = useMemo(() => {
    return rows
      .map((row) => {
        const material = materiales.find((item) => String(item.id) === String(row.materialId));
        const forecast = row.materialId ? forecastsByMaterial[row.materialId] : null;
        const quantity = Number(row.quantity);
        const validQuantity = Number.isFinite(quantity) && quantity > 0;
        const currentUnitPrice = forecast ? Number(forecast.ultimo_precio_observado) : 0;
        const projectedPoint = forecast?.puntos?.[forecast.puntos.length - 1] || null;
        const projectedUnitPrice = projectedPoint ? Number(projectedPoint.precio_proyectado) : 0;
        const currentCost = validQuantity ? currentUnitPrice * quantity : 0;
        const projectedCost = validQuantity ? projectedUnitPrice * quantity : 0;
        const delta = projectedCost - currentCost;
        const deltaPercent = currentCost === 0 ? 0 : (delta / currentCost) * 100;

        return {
          ...row,
          material,
          forecast,
          quantity,
          validQuantity,
          projectedPoint,
          currentCost,
          projectedCost,
          delta,
          deltaPercent,
        };
      })
      .filter((row) => row.material);
  }, [forecastsByMaterial, materiales, rows]);

  const summary = useMemo(() => {
    const comparableRows = plannerRows.filter((row) => row.forecast && row.validQuantity && row.projectedPoint);
    if (!comparableRows.length) return null;

    const totalCurrent = comparableRows.reduce((total, row) => total + row.currentCost, 0);
    const totalProjected = comparableRows.reduce((total, row) => total + row.projectedCost, 0);
    const totalDelta = totalProjected - totalCurrent;
    const totalDeltaPercent = totalCurrent === 0 ? 0 : (totalDelta / totalCurrent) * 100;
    const highestImpact = comparableRows.reduce((worst, row) => (row.delta > worst.delta ? row : worst), comparableRows[0]);

    return {
      comparableRows,
      totalCurrent,
      totalProjected,
      totalDelta,
      totalDeltaPercent,
      highestImpact,
    };
  }, [plannerRows]);

  const addRow = (materialId = "") => setRows((current) => [...current, createEmptyRow(materialId)]);
  const removeRow = (id) => setRows((current) => current.filter((item) => item.id !== id));
  const updateRow = (id, field, value) => 
    setRows((current) => current.map((item) => (item.id === id ? { ...item, [field]: value } : item)));

  return {
    rows,
    plannerRows,
    summary,
    loading,
    error,
    addRow,
    removeRow,
    updateRow,
  };
}
