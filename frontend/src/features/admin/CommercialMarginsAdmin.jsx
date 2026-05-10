import EditOutlinedIcon from "@mui/icons-material/EditOutlined";
import SwapHorizIcon from "@mui/icons-material/SwapHoriz";
import { Alert, Box, Button, Card, CardContent, Chip, FormControl, InputLabel, MenuItem, Select, TextField, Typography } from "@mui/material";
import { useCallback, useEffect, useMemo, useState } from "react";

import { SectionHeader } from "../../shared/components/SectionHeader.jsx";
import { formatNumber } from "../../shared/utils/formatters.js";
import { createCommercialMargin, fetchCommercialMargins, updateCommercialMargin } from "./admin.api.js";

const DEFAULT_FORM = {
  scope: "GLOBAL",
  materialId: "",
  presentationId: "",
  productKey: "",
  marginPct: "20.00",
  activo: true,
};

function normalizeSlug(value) {
  return String(value || "")
    .trim()
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[^\w\s-]/g, "")
    .replace(/\s+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "");
}

function deriveProductKey(materialName, presentationName) {
  const materialKey = normalizeSlug(materialName);
  const presentationKey = normalizeSlug(presentationName);
  return presentationKey ? `${materialKey}-${presentationKey}` : materialKey;
}

function getMaterialLabel(materialesById, materialId) {
  if (!materialId) return "-";
  return materialesById.get(String(materialId))?.nombre || `Material ${materialId}`;
}

function getPresentationLabel(presentacionesById, presentationId) {
  if (!presentationId) return "-";
  return presentacionesById.get(String(presentationId))?.nombre_presentacion || `Presentación ${presentationId}`;
}

export function CommercialMarginsAdmin({ token, materiales, presentaciones }) {
  const [margins, setMargins] = useState([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [editingId, setEditingId] = useState(null);
  const [form, setForm] = useState(DEFAULT_FORM);

  const materialesById = useMemo(() => new Map(materiales.map((material) => [String(material.id), material])), [materiales]);
  const presentacionesById = useMemo(
    () => new Map(presentaciones.map((presentacion) => [String(presentacion.id), presentacion])),
    [presentaciones]
  );

  const filteredPresentaciones = useMemo(
    () => presentaciones.filter((presentacion) => String(presentacion.material_id) === String(form.materialId) && presentacion.activa),
    [form.materialId, presentaciones]
  );

  const scopeLabel = {
    GLOBAL: "General",
    MATERIAL: "Material",
    PRODUCT: "Producto",
  };

  const loadMargins = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await fetchCommercialMargins(token);
      setMargins(data);
    } catch (loadError) {
      setError(loadError.message);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    if (token) {
      loadMargins();
    }
  }, [loadMargins, token]);

  useEffect(() => {
    if (form.scope !== "GLOBAL" && !form.materialId && materiales.length) {
      setForm((current) => ({ ...current, materialId: String(materiales[0].id) }));
    }
  }, [form.scope, form.materialId, materiales]);

  useEffect(() => {
    if (form.scope === "PRODUCT" && filteredPresentaciones.length) {
      const currentPresentationIsValid = filteredPresentaciones.some((presentacion) => String(presentacion.id) === String(form.presentationId));
      if (!currentPresentationIsValid) {
        setForm((current) => ({ ...current, presentationId: String(filteredPresentaciones[0].id) }));
      }
    }
  }, [filteredPresentaciones, form.presentationId, form.scope]);

  function updateField(name, value) {
    setForm((current) => ({ ...current, [name]: value }));
  }

  function handleScopeChange(nextScope) {
    setForm((current) => {
      if (nextScope === "GLOBAL") {
        return {
          ...current,
          scope: nextScope,
          materialId: "",
          presentationId: "",
          productKey: "",
        };
      }

      if (nextScope === "MATERIAL") {
        return {
          ...current,
          scope: nextScope,
          presentationId: "",
          productKey: "",
          materialId: current.materialId || (materiales[0] ? String(materiales[0].id) : ""),
        };
      }

      return {
        ...current,
        scope: nextScope,
        materialId: current.materialId || (materiales[0] ? String(materiales[0].id) : ""),
        presentationId: current.presentationId,
      };
    });
  }

  function handleMaterialChange(nextMaterialId) {
    setForm((current) => {
      const nextMaterial = materialesById.get(String(nextMaterialId));
      const nextPresentaciones = presentaciones.filter(
        (presentacion) => String(presentacion.material_id) === String(nextMaterialId) && presentacion.activa
      );
      const nextPresentationId =
        current.scope === "PRODUCT" && nextPresentaciones.some((presentacion) => String(presentacion.id) === String(current.presentationId))
          ? current.presentationId
          : current.scope === "PRODUCT"
            ? nextPresentaciones[0]
              ? String(nextPresentaciones[0].id)
              : ""
            : current.presentationId;

      return {
        ...current,
        materialId: String(nextMaterialId),
        presentationId: current.scope === "GLOBAL" ? "" : nextPresentationId,
        productKey:
          current.scope === "PRODUCT" && current.productKey && nextMaterial
            ? deriveProductKey(nextMaterial.nombre, nextPresentaciones.find((presentacion) => String(presentacion.id) === String(nextPresentationId))?.nombre_presentacion)
            : current.productKey,
      };
    });
  }

  function handlePresentationChange(nextPresentationId) {
    setForm((current) => {
      if (current.scope !== "PRODUCT") {
        return { ...current, presentationId: String(nextPresentationId) };
      }

      const nextPresentation = presentacionesById.get(String(nextPresentationId));
      const nextMaterial = materialesById.get(String(current.materialId));
      return {
        ...current,
        presentationId: String(nextPresentationId),
        productKey: nextPresentation && nextMaterial ? deriveProductKey(nextMaterial.nombre, nextPresentation.nombre_presentacion) : current.productKey,
      };
    });
  }

  function resetForm() {
    setEditingId(null);
    setForm(DEFAULT_FORM);
  }

  function startEdit(margin) {
    setEditingId(margin.id);
    setForm({
      scope: margin.scope,
      materialId: margin.material_id ? String(margin.material_id) : "",
      presentationId: margin.presentation_id ? String(margin.presentation_id) : "",
      productKey: margin.product_key || "",
      marginPct: String(margin.margen_ganancia_pct),
      activo: margin.activo,
    });
    setMessage("");
    setError("");
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setMessage("");

    const scope = form.scope;
    const materialId = scope === "GLOBAL" ? null : Number(form.materialId);
    const presentationId = scope === "PRODUCT" && form.presentationId ? Number(form.presentationId) : null;
    const material = materialId ? materialesById.get(String(materialId)) : null;
    const presentation = presentationId ? presentacionesById.get(String(presentationId)) : null;
    const marginPct = Number(form.marginPct);

    if (scope !== "GLOBAL" && !materialId) {
      setError("Seleccioná un material para el margen.");
      return;
    }
    if (!Number.isFinite(marginPct) || marginPct < 0) {
      setError("El margen debe ser un número mayor o igual a cero.");
      return;
    }

    let productKey = form.productKey.trim() || null;
    if (scope === "PRODUCT" && !productKey && presentation) {
      productKey = deriveProductKey(material?.nombre, presentation?.nombre_presentacion);
    }
    if (scope === "PRODUCT" && !presentationId && !productKey) {
      setError("Para un margen PRODUCT necesitás una presentacion o una clave de producto.");
      return;
    }

    const payload = {
      scope,
      material_id: materialId,
      presentation_id: presentationId,
      product_key: productKey,
      margen_ganancia_pct: marginPct.toFixed(2),
      activo: Boolean(form.activo),
    };

    setSaving(true);
    try {
      if (editingId) {
        await updateCommercialMargin(editingId, payload, token);
        setMessage("Margen actualizado correctamente.");
      } else {
        await createCommercialMargin(payload, token);
        setMessage("Margen creado correctamente.");
      }
      resetForm();
      await loadMargins();
    } catch (saveError) {
      setError(saveError.message);
    } finally {
      setSaving(false);
    }
  }

  async function handleToggleActivo(margin) {
    setError("");
    setMessage("");
    try {
      await updateCommercialMargin(margin.id, { activo: !margin.activo }, token);
      setMessage(margin.activo ? "Margen desactivado." : "Margen activado.");
      await loadMargins();
    } catch (toggleError) {
      setError(toggleError.message);
    }
  }

  return (
    <Card className="mt-5">
      <CardContent className="space-y-6 p-5 md:p-6">
        <SectionHeader
          title="Administración de márgenes comerciales"
          description="Define el margen de venta por alcance y deja que la regla comercial se aplique por encima del precio de costo."
          badge="Admin"
        />

        <Alert severity="info">
          El precio de costo sigue viniendo del forecast. Acá solo configurás la capa comercial que transforma costo en precio de venta.
        </Alert>

        {error ? (
          <Alert severity="error">
            {error}
          </Alert>
        ) : null}
        {message ? (
          <Alert severity="success">
            {message}
          </Alert>
        ) : null}

        <Box
          component="form"
          className="rounded-2xl border border-slate-200 bg-slate-50 p-4 md:p-5"
          onSubmit={handleSubmit}
        >
          <Box className="grid gap-4 lg:grid-cols-2 xl:grid-cols-[.8fr_1fr_1fr_1fr_.7fr_.7fr] xl:items-end">
          <FormControl size="small">
            <InputLabel id="commercial-scope-label">Alcance</InputLabel>
            <Select labelId="commercial-scope-label" label="Alcance" value={form.scope} onChange={(event) => handleScopeChange(event.target.value)}>
              <MenuItem value="GLOBAL">General</MenuItem>
              <MenuItem value="MATERIAL">Material</MenuItem>
              <MenuItem
                value="PRODUCT"
                disabled
                sx={{
                  opacity: 0.45,
                  fontStyle: "italic",
                }}
              >
                Producto (no disponible en el MVP)
              </MenuItem>
            </Select>
          </FormControl>

          <FormControl size="small" disabled={form.scope === "GLOBAL"}>
            <InputLabel id="commercial-material-label">Material</InputLabel>
            <Select labelId="commercial-material-label" label="Material" value={form.materialId} onChange={(event) => handleMaterialChange(event.target.value)}>
              {materiales.map((material) => (
                <MenuItem key={material.id} value={String(material.id)}>
                  {material.nombre}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <FormControl size="small" disabled={form.scope !== "PRODUCT"}>
            <InputLabel id="commercial-presentation-label">Presentación</InputLabel>
            <Select
              labelId="commercial-presentation-label"
              label="Presentación"
              value={form.presentationId}
              onChange={(event) => handlePresentationChange(event.target.value)}
            >
              <MenuItem value="">
                <em>Sin presentación</em>
              </MenuItem>
              {filteredPresentaciones.map((presentacion) => (
                <MenuItem key={presentacion.id} value={String(presentacion.id)}>
                  {presentacion.nombre_presentacion}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <TextField
            size="small"
            label="Clave de producto"
            value={form.productKey}
            onChange={(event) => updateField("productKey", event.target.value)}
            disabled={form.scope !== "PRODUCT"}
          />

          <TextField
            size="small"
            label="Margen %"
            type="number"
            value={form.marginPct}
            onChange={(event) => updateField("marginPct", event.target.value)}
            inputProps={{ min: 0, step: "0.01" }}
          />

          <FormControl size="small">
            <InputLabel id="commercial-activo-label">Estado</InputLabel>
            <Select labelId="commercial-activo-label" label="Estado" value={String(form.activo)} onChange={(event) => updateField("activo", event.target.value === "true")}>
              <MenuItem value="true">Activo</MenuItem>
              <MenuItem value="false">Inactivo</MenuItem>
            </Select>
          </FormControl>

          <Box className="flex flex-wrap gap-2 lg:col-span-2 xl:col-span-6">
            <Button type="submit" variant="contained" startIcon={<SwapHorizIcon />} disabled={saving || loading}>
              {saving ? (editingId ? "Actualizando" : "Guardando") : editingId ? "Actualizar margen" : "Crear margen"}
            </Button>
            <Button type="button" variant="outlined" onClick={resetForm} disabled={saving || loading}>
              Limpiar
            </Button>
          </Box>

          {form.scope === "PRODUCT" ? (
            <Typography className="pt-1 lg:col-span-2 xl:col-span-6" variant="body2" color="text.secondary">
              La clave de producto es opcional si elegís una presentación. Solo se usa en márgenes de producto.
            </Typography>
          ) : null}
          </Box>
        </Box>

        <Box className="grid gap-4">
          <Typography variant="h3">Márgenes cargados</Typography>
          {loading ? (
            <Alert severity="info">Cargando márgenes...</Alert>
          ) : margins.length === 0 ? (
            <Alert severity="warning">No hay márgenes configurados.</Alert>
          ) : (
            margins.map((margin) => {
              const materialLabel = getMaterialLabel(materialesById, margin.material_id);
              const presentationLabel = getPresentationLabel(presentacionesById, margin.presentation_id);
              return (
                <Box key={margin.id} className="rounded-xl border border-slate-200 bg-white p-4 md:p-5">
                  <Box className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                    <Box>
                      <Box className="mb-2 flex flex-wrap gap-2">
                        <Chip label={scopeLabel[margin.scope] || margin.scope} color={margin.activo ? "primary" : "default"} size="small" />
                        <Chip label={margin.activo ? "Activo" : "Inactivo"} color={margin.activo ? "success" : "default"} size="small" />
                        <Chip label={`${formatNumber(margin.margen_ganancia_pct)}%`} variant="outlined" size="small" />
                      </Box>
                      <Typography variant="h3">
                        {margin.scope === "GLOBAL"
                          ? "Margen global"
                          : margin.scope === "MATERIAL"
                            ? materialLabel
                            : `${materialLabel}${presentationLabel !== "-" ? ` · ${presentationLabel}` : ""}`}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        {margin.scope === "GLOBAL"
                          ? "Aplica como respaldo general."
                          : margin.scope === "MATERIAL"
                            ? `Aplica a todo el material ${materialLabel}.`
                            : `Aplica al producto ${margin.product_key || `${materialLabel} · ${presentationLabel}`}.`}
                      </Typography>
                    </Box>

                    <Box className="flex flex-wrap gap-2">
                      <Button variant="outlined" startIcon={<EditOutlinedIcon />} onClick={() => startEdit(margin)}>
                        Editar
                      </Button>
                      <Button variant="outlined" color={margin.activo ? "warning" : "success"} onClick={() => handleToggleActivo(margin)}>
                        {margin.activo ? "Desactivar" : "Activar"}
                      </Button>
                    </Box>
                  </Box>

                  <Box className="mt-4 grid gap-3 md:grid-cols-4">
                    <MiniMeta label="Margen" value={`${formatNumber(margin.margen_ganancia_pct)}%`} helper={`ID ${margin.id}`} />
                    <MiniMeta label="Material" value={materialLabel} helper={margin.material_id ? `ID ${margin.material_id}` : "Sin material"} />
                    <MiniMeta label="Presentación" value={presentationLabel} helper={margin.presentation_id ? `ID ${margin.presentation_id}` : "Sin presentación"} />
                    <MiniMeta label="Clave de producto" value={margin.product_key || "-"} helper="Solo para producto" />
                  </Box>
                </Box>
              );
            })
          )}
        </Box>
      </CardContent>
    </Card>
  );
}

function MiniMeta({ label, value, helper }) {
  return (
    <Box className="rounded-xl border border-slate-200 bg-slate-50 p-4">
      <Typography color="text.secondary" variant="body2" fontWeight={800}>
        {label}
      </Typography>
      <Typography component="strong" display="block" mt={0.75} variant="h3" lineHeight={1.1}>
        {value}
      </Typography>
      <Typography color="text.secondary" variant="body2" mt={0.5}>
        {helper}
      </Typography>
    </Box>
  );
}
