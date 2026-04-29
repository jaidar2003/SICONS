import SaveIcon from "@mui/icons-material/Save";
import { Alert, Box, Button, Card, CardContent, FormControl, InputLabel, MenuItem, Select, TextField } from "@mui/material";
import { DatePicker } from "@mui/x-date-pickers";
import { useEffect, useMemo, useState } from "react";

import { SectionHeader } from "../../shared/components/SectionHeader.jsx";
import { toApiDate } from "../../shared/utils/formatters.js";

export function PriceForm({ materiales, presentaciones, fuentes, maxDate, onSave }) {
  const [payload, setPayload] = useState({
    material_id: "",
    presentacion_id: "",
    fuente_id: "",
    fecha: null,
    precio_original: "",
    numero_comprobante: "",
    observaciones: "",
  });
  const [message, setMessage] = useState(null);
  const [saving, setSaving] = useState(false);

  const filteredPresentaciones = useMemo(
    () => presentaciones.filter((presentacion) => String(presentacion.material_id) === String(payload.material_id) && presentacion.activa),
    [payload.material_id, presentaciones]
  );

  useEffect(() => {
    if (!payload.material_id && materiales.length) {
      setPayload((current) => ({ ...current, material_id: String(materiales[0].id) }));
    }
  }, [materiales, payload.material_id]);

  useEffect(() => {
    if (filteredPresentaciones.length && !filteredPresentaciones.some((presentacion) => String(presentacion.id) === String(payload.presentacion_id))) {
      setPayload((current) => ({ ...current, presentacion_id: String(filteredPresentaciones[0].id) }));
    }
  }, [filteredPresentaciones, payload.presentacion_id]);

  useEffect(() => {
    if (!payload.fuente_id && fuentes.length) {
      setPayload((current) => ({ ...current, fuente_id: String(fuentes[0].id) }));
    }
  }, [fuentes, payload.fuente_id]);

  function update(name, value) {
    setPayload((current) => ({ ...current, [name]: value }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setMessage(null);
    setSaving(true);
    try {
      const saved = await onSave({
        material_id: Number(payload.material_id),
        presentacion_id: Number(payload.presentacion_id),
        fuente_id: Number(payload.fuente_id),
        fecha: toApiDate(payload.fecha),
        precio_original: payload.precio_original,
        moneda: "ARS",
        numero_comprobante: payload.numero_comprobante.trim() || null,
        observaciones: payload.observaciones.trim() || null,
      });
      setMessage({ severity: "success", text: "Precio historico guardado. La serie fue actualizada." });
      setPayload((current) => ({
        ...current,
        material_id: String(saved.material_id),
        precio_original: "",
        numero_comprobante: "",
        observaciones: "",
      }));
    } catch (error) {
      setMessage({ severity: "error", text: error.message });
    } finally {
      setSaving(false);
    }
  }

  return (
    <Card className="mt-3">
      <CardContent>
        <SectionHeader title="Registrar precio historico" description="La normalizacion se calcula automaticamente segun la presentacion." badge="Carga manual" />
        {message ? (
          <Alert className="mb-3" severity={message.severity}>
            {message.text}
          </Alert>
        ) : null}
        <Box component="form" className="grid gap-3 lg:grid-cols-[1.1fr_1fr_1fr_.8fr_.8fr] lg:items-end" onSubmit={handleSubmit}>
          <FormControl required>
            <InputLabel id="form-material-label">Material</InputLabel>
            <Select labelId="form-material-label" label="Material" value={payload.material_id} onChange={(event) => update("material_id", event.target.value)}>
              {materiales.map((material) => (
                <MenuItem key={material.id} value={String(material.id)}>
                  {material.nombre} ({material.unidad_base})
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControl required>
            <InputLabel id="form-presentacion-label">Presentacion</InputLabel>
            <Select
              labelId="form-presentacion-label"
              label="Presentacion"
              value={payload.presentacion_id}
              onChange={(event) => update("presentacion_id", event.target.value)}
            >
              {filteredPresentaciones.map((presentacion) => (
                <MenuItem key={presentacion.id} value={String(presentacion.id)}>
                  {presentacion.nombre_presentacion}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControl required>
            <InputLabel id="form-fuente-label">Fuente</InputLabel>
            <Select labelId="form-fuente-label" label="Fuente" value={payload.fuente_id} onChange={(event) => update("fuente_id", event.target.value)}>
              {fuentes.map((fuente) => (
                <MenuItem key={fuente.id} value={String(fuente.id)}>
                  {fuente.nombre}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <DatePicker
            label="Fecha"
            value={payload.fecha}
            maxDate={maxDate}
            onChange={(value) => update("fecha", value)}
            format="DD/MM/YYYY"
            slotProps={{ textField: { required: true, size: "small" } }}
          />
          <TextField label="Precio original" type="number" required value={payload.precio_original} onChange={(event) => update("precio_original", event.target.value)} />
          <TextField label="Comprobante" value={payload.numero_comprobante} onChange={(event) => update("numero_comprobante", event.target.value)} />
          <TextField className="lg:col-span-2" label="Observaciones" value={payload.observaciones} onChange={(event) => update("observaciones", event.target.value)} />
          <Button type="submit" variant="contained" startIcon={<SaveIcon />} disabled={saving}>
            {saving ? "Guardando" : "Guardar precio"}
          </Button>
        </Box>
      </CardContent>
    </Card>
  );
}
