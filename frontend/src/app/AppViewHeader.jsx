import { Box, Card, CardContent, Chip, Tab, Tabs, Typography } from "@mui/material";

export function AppViewHeader({ activeView, activeTabConfig, forecastHorizon, selectedMaterial, visibleTabs, onViewChange }) {
  return (
    <Card className="overflow-hidden border border-slate-200 shadow-md1" sx={{ mt: -6 }}>
      <CardContent className="p-0">
        <Box
          className="px-6 pb-3 pt-5 text-white"
          sx={{
            background: `linear-gradient(135deg, ${activeTabConfig.accent} 0%, rgba(2, 6, 23, 0.95) 100%)`,
          }}
        >
          <Box className="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
            <Box className="max-w-3xl">
              <Typography variant="overline" sx={{ opacity: 0.8, fontWeight: 700, letterSpacing: 1 }}>
                {activeTabConfig.eyebrow}
              </Typography>
              <Box className="flex flex-wrap items-baseline gap-3">
                <Typography variant="h1" component="h1" lineHeight={1.1} sx={{ fontSize: "1.75rem", fontWeight: 800 }}>
                  {activeTabConfig.label}
                </Typography>
                <Typography variant="body2" sx={{ color: "rgba(255,255,255,0.75)", fontWeight: 500 }}>
                  {activeTabConfig.description}
                </Typography>
              </Box>
            </Box>
            <Box className="flex flex-wrap gap-2 lg:mt-0">
              <Chip
                label={selectedMaterial ? selectedMaterial.nombre : "Sin material"}
                sx={{
                  bgcolor: "rgba(255,255,255,0.12)",
                  color: "white",
                  fontWeight: 800,
                  fontSize: 12,
                  backdropFilter: "blur(4px)",
                  border: "1px solid rgba(255,255,255,0.15)",
                }}
              />
              <Chip
                label={`${forecastHorizon} meses`}
                sx={{
                  bgcolor: "rgba(255,255,255,0.12)",
                  color: "white",
                  fontWeight: 800,
                  fontSize: 12,
                  backdropFilter: "blur(4px)",
                  border: "1px solid rgba(255,255,255,0.15)",
                }}
              />
            </Box>
          </Box>
        </Box>
        <Box className="border-b border-slate-200 bg-white">
          <Box className="overflow-hidden">
            <Tabs
              value={activeView}
              onChange={(_event, value) => onViewChange(value)}
              variant="fullWidth"
              className="w-full"
              sx={{
                minHeight: 0,
                width: "100%",
                "& .MuiTabs-indicator": {
                  height: 4,
                  borderRadius: "4px 4px 0 0",
                  backgroundColor: activeTabConfig.accent,
                },
                "& .MuiTabs-scroller": {
                  overflow: "hidden !important",
                },
                "& .MuiTabs-flexContainer": {
                  display: "flex",
                  width: "100%",
                  alignItems: "stretch",
                },
                "& .MuiTab-root": {
                  flex: "1 1 0",
                  flexBasis: 0,
                  maxWidth: "none",
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
                    flex: "1 1 0",
                    flexBasis: 0,
                    minHeight: 0,
                    minWidth: 0,
                    maxWidth: "none",
                    height: 48,
                    px: { xs: 0.5, sm: 1, md: 2 },
                    py: 0,
                    borderRight: "1px solid",
                    borderColor: "rgba(148, 163, 184, 0.15)",
                    boxSizing: "border-box",
                    justifyContent: "center",
                    textTransform: "none",
                    fontSize: { xs: 11, sm: 12, md: 13 },
                    fontWeight: 700,
                    whiteSpace: "nowrap",
                    overflow: "hidden",
                    color: "text.secondary",
                    "&:last-of-type": {
                      borderRight: 0,
                    },
                    "& .MuiTab-iconWrapper": {
                      mr: { xs: 0.5, sm: 0.75, md: 1 },
                      opacity: 0.7,
                    },
                    "&.Mui-selected": {
                      color: activeTabConfig.accent,
                      fontWeight: 900,
                      bgcolor: "rgba(0,0,0,0.02)",
                      "& .MuiTab-iconWrapper": {
                        opacity: 1,
                      },
                    },
                    "&.Mui-disabled": {
                      opacity: 0.4,
                      color: "text.disabled",
                    },
                  }}
                />
              ))}
            </Tabs>
          </Box>
        </Box>
      </CardContent>
    </Card>
  );
}
