import LogoutIcon from "@mui/icons-material/Logout";
import { Box, Button, Container, FormControlLabel, Switch, Typography } from "@mui/material";

import { StatusBadge } from "../../shared/components/StatusBadge.jsx";

export function AppHeader({ apiStatus, user, onLogout, showPrices, onToggleShowPrices }) {
  return (
    <Box component="header" className="pb-20 pt-8 text-white" sx={{ backgroundColor: "#002395" }}>
      <Container maxWidth="lg" className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
        <Box>
          <Box className="mb-4 inline-flex min-h-[86px] w-[150px] items-center justify-center rounded-md border border-white/30 bg-white px-3 py-2 shadow-md1">
            <img src="/bwlogo.png" alt="BuildWise" className="h-auto w-full object-contain" />
          </Box>
          <Typography variant="h1">Analisis de precios de materiales</Typography>
          <Typography color="rgba(255,255,255,.82)" mt={1.25} maxWidth={680}>
            Serie historica normalizada para comparar precios reales y preparar proyecciones.
          </Typography>
        </Box>

        <Box className="flex w-full flex-col gap-2 rounded-md border border-white/20 bg-white/10 p-2 shadow-md1 sm:w-auto sm:min-w-[360px] sm:flex-row sm:items-center sm:justify-between lg:mt-2">
          <Box className="flex justify-start sm:justify-end">
            <StatusBadge mode={apiStatus.mode} label={apiStatus.label} />
          </Box>
          {user ? (
            <Box className="flex flex-wrap items-center justify-between gap-2">
              <FormControlLabel
                control={<Switch checked={showPrices} onChange={onToggleShowPrices} color="default" />}
                label={showPrices ? "Mostrar precios" : "Solo porcentajes"}
                sx={{ mr: 0, "& .MuiFormControlLabel-label": { fontSize: 13, fontWeight: 700, color: "white" } }}
              />
              <Typography fontSize={14} fontWeight={700} noWrap>
                {user.nombre} ({user.rol})
              </Typography>
              <Button color="inherit" size="small" variant="contained" startIcon={<LogoutIcon />} sx={{ bgcolor: "white", color: "primary.main", "&:hover": { bgcolor: "#EEF2FF" } }} onClick={onLogout}>
                Salir
              </Button>
            </Box>
          ) : null}
        </Box>
      </Container>
    </Box>
  );
}
