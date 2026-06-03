import { Box, Button, ButtonGroup, Typography } from "@mui/material";

import { brand } from "../../app/brand.js";
import { StatusBadge } from "../../shared/components/StatusBadge.jsx";
import bwLogo from "../../../bwlogo.png";

export function AppHeader({ apiStatus, user, onLogout, showPrices, onToggleShowPrices }) {
  return (
    <Box
      component="header"
      className="pb-16 pt-6 text-white"
      sx={{
        background: brand.gradients.hero,
        boxShadow: brand.shadows.header,
      }}
    >
      <Box className="mx-auto flex w-[95%] max-w-[1600px] flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <Box className="flex flex-col gap-4 lg:flex-row lg:items-center lg:gap-8">
          <Box className="inline-flex min-h-[64px] w-[120px] items-center justify-center rounded-[12px] border border-white/30 bg-white px-3 py-2 shadow-md1">
            <img src={bwLogo} alt="BuildWise" className="h-auto w-full object-contain" />
          </Box>
          <Box>
            <Typography variant="h1" sx={{ fontSize: { xs: "1.75rem", md: "2.25rem" } }}>
              BuildWise
            </Typography>
            <Typography color="rgba(255,255,255,.82)" mt={0.5} maxWidth={600} variant="body2">
              Análisis de precios y proyecciones para decidir mejor cuándo comprar materiales de obra.
            </Typography>
          </Box>
        </Box>

        <Box className="flex flex-col gap-2 rounded-xl border border-white/20 bg-white/10 p-2 shadow-md1 sm:flex-row sm:items-center lg:mt-0">
            <Box className="flex items-center gap-3">
              <StatusBadge mode={apiStatus.mode} label={apiStatus.label} />
              {user && (
                <Box className="flex items-center gap-2">
                  <Typography fontSize={13} fontWeight={800} sx={{ opacity: 0.9, whiteSpace: "nowrap" }}>
                    {user.nombre} ({user.rol})
                  </Typography>
              </Box>
            )}
          </Box>
          {user ? (
            <Box className="flex items-center gap-2 border-t border-white/10 pt-2 sm:border-l sm:border-t-0 sm:pl-2 sm:pt-0">
              <ButtonGroup
                size="small"
                variant="outlined"
                disableElevation
                sx={{
                  borderRadius: 999,
                  bgcolor: "rgba(255,255,255,0.05)",
                  "& .MuiButton-root": {
                    borderColor: "rgba(255,255,255,0.4)",
                    bgcolor: "white",
                    color: "primary.main",
                    fontSize: 11,
                    fontWeight: 900,
                    minWidth: 80,
                    px: 1.25,
                    height: 32,
                    textTransform: "none",
                    "&:hover": {
                      borderColor: "white",
                      bgcolor: brand.colors.primarySoft,
                    },
                  },
                  "& .MuiButton-contained": {
                    bgcolor: brand.colors.primary,
                    color: "white",
                    boxShadow: "none",
                    borderColor: "transparent",
                    "&:hover": { bgcolor: brand.colors.primaryHover, boxShadow: "none" },
                  },
                }}
              >
                <Button variant={showPrices ? "contained" : "outlined"} onClick={() => onToggleShowPrices({ target: { checked: true } })}>
                  Precios
                </Button>
                <Button variant={!showPrices ? "contained" : "outlined"} onClick={() => onToggleShowPrices({ target: { checked: false } })}>
                  Var %
                </Button>
              </ButtonGroup>
              <Button
                color="inherit"
                size="small"
                variant="contained"
                sx={{
                  height: 32,
                  bgcolor: "white",
                  color: "primary.main",
                  fontSize: 11,
                  fontWeight: 900,
                  px: 1.5,
                  "&:hover": { bgcolor: brand.colors.primarySoft },
                }}
                onClick={onLogout}
              >
                Salir
              </Button>
            </Box>
          ) : null}
        </Box>
      </Box>
    </Box>
  );
}
