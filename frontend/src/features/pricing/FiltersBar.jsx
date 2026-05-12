import RefreshIconModule from "@mui/icons-material/Refresh";
import { Box, Button, Card, CardContent, FormControl, InputLabel, MenuItem, Select, Typography } from "@mui/material";
import { DatePicker } from "@mui/x-date-pickers";

import { resolveMuiIcon } from "../../shared/components/resolveMuiIcon.js";

const RefreshIcon = resolveMuiIcon(RefreshIconModule);

export function FiltersBar({ materiales, selectedMaterialId, desde, hasta, maxDate, warning, onMaterialChange, onDesdeChange, onHastaChange, onRefresh }) {
  return (
    <Card className="-mt-12">
      <CardContent className="grid gap-4 p-4 md:grid-cols-[180px_1fr] md:items-center">
        <Box className="border-b border-slate-200 pb-3 md:border-b-0 md:border-r md:pb-0 md:pr-4">
          <Typography color="primary" fontSize={12} fontWeight={800}>
            Vista actual
          </Typography>
          <Typography fontSize={18} fontWeight={800}>
            Serie historica
          </Typography>
        </Box>
        <Box className="grid gap-3 md:grid-cols-[minmax(220px,1fr)_180px_180px_auto] md:items-end">
          <FormControl>
            <InputLabel id="material-select-label">Material</InputLabel>
            <Select labelId="material-select-label" label="Material" value={selectedMaterialId || ""} onChange={(event) => onMaterialChange(event.target.value)}>
              {materiales.map((material) => (
                <MenuItem key={material.id} value={String(material.id)}>
                  {material.nombre} ({material.unidad_base})
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <DatePicker label="Desde" value={desde} onChange={onDesdeChange} format="DD/MM/YY" slotProps={{ textField: { size: "small" } }} />
          <DatePicker
            label="Hasta"
            value={hasta}
            maxDate={maxDate}
            onChange={onHastaChange}
            format="DD/MM/YY"
            slotProps={{ textField: { size: "small" } }}
          />
          <Button variant="contained" startIcon={<RefreshIcon />} onClick={onRefresh}>
            Actualizar
          </Button>
        </Box>
        {warning ? (
          <Box className="rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm font-medium text-rose-900 md:col-start-2">{warning}</Box>
        ) : null}
      </CardContent>
    </Card>
  );
}
