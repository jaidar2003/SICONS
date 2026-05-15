import { useEffect, useMemo, useState } from "react";
import { fetchForecast } from "./pricing.api.js";

const COST_PLANNER_STORAGE_PREFIX = "sicons_cost_planner";

function createEmptyRow(materialId = "") {
  return {
    id: crypto.randomUUID(),
    materialId,
    quantity: "100",
    criticidad: "media",
    minimumImmediatePct: "",
  };
}

export function useCostPlanner({ materiales, selectedMaterialId, forecastHorizon, token }) {
  const storageKey = useMemo(() => `${COST_PLANNER_STORAGE_PREFIX}:${forecastHorizon}`, [forecastHorizon]);
  const [rows, setRows] = useState(() => {
    if (typeof window === "undefined") {
      return [createEmptyRow(selectedMaterialId || "")];
    }

    const stored = window.localStorage.getItem(storageKey);
    if (!stored) {
      return [createEmptyRow(selectedMaterialId || "")];
    }

    try {
      const parsed = JSON.parse(stored);
      if (!Array.isArray(parsed.rows) || !parsed.rows.length) {
        return [createEmptyRow(selectedMaterialId || "")];
      }

      return parsed.rows.map((row) => ({
        id: row.id || crypto.randomUUID(),
        materialId: row.materialId || "",
        quantity: row.quantity || "100",
        criticidad: row.criticidad || "media",
        minimumImmediatePct: row.minimumImmediatePct || "",
      }));
    } catch {
      return [createEmptyRow(selectedMaterialId || "")];
    }
  });
  const [storedBudgetInput, setStoredBudgetInput] = useState(() => {
    if (typeof window === "undefined") return "";
    const stored = window.localStorage.getItem(storageKey);
    if (!stored) return "";

    try {
      const parsed = JSON.parse(stored);
      return typeof parsed.budgetInput === "string" ? parsed.budgetInput : "";
    } catch {
      return "";
    }
  });
  const [forecastsByMaterial, setForecastsByMaterial] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    setRows((current) => {
      if (current.some((row) => row.materialId)) return current;
      return [createEmptyRow(selectedMaterialId || "")];
    });
  }, [selectedMaterialId]);

  useEffect(() => {
    if (typeof window === "undefined") return;

    window.localStorage.setItem(
      storageKey,
      JSON.stringify({
        rows,
      })
    );
  }, [rows, storageKey]);

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
        const criticidad = row.criticidad || "media";
        const minimumImmediatePct = row.minimumImmediatePct || "";
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
          criticidad,
          minimumImmediatePct,
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

  const setBudgetPersisted = (value) => {
    setStoredBudgetInput(value);
    if (typeof window === "undefined") return;

    const raw = window.localStorage.getItem(storageKey);
    let current = {};
    try {
      current = raw ? JSON.parse(raw) : {};
    } catch {
      current = {};
    }

    window.localStorage.setItem(
      storageKey,
      JSON.stringify({
        ...current,
        budgetInput: value,
      })
    );
  };

  return {
    rows,
    plannerRows,
    summary,
    loading,
    error,
    addRow,
    removeRow,
    updateRow,
    storedBudgetInput,
    setBudgetPersisted,
  };
}
