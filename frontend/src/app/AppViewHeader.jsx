import { Box, Card, CardContent, Chip, Tab, Tabs, Typography } from "@mui/material";

export function AppViewHeader({ activeView, activeTabConfig, forecastHorizon, selectedMaterial, visibleTabs, onViewChange }) {
  return (
    <Card className="mt-3 overflow-hidden border border-slate-200 shadow-md1">
      <CardContent className="p-0">
        <Box
          className="px-4 pb-4 pt-5 text-white"
          sx={{
            background: `linear-gradient(135deg, ${activeTabConfig.accent} 0%, rgba(2, 6, 23, 0.92) 100%)`,
          }}
        >
          <Box className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
            <Box className="max-w-2xl">
              <Typography variant="overline" sx={{ opacity: 0.8 }}>
                {activeTabConfig.eyebrow}
              </Typography>
              <Typography mt={1} variant="h1" component="h1" lineHeight={1}>
                {activeTabConfig.label}
              </Typography>
              <Typography mt={1.25} maxWidth={760} variant="body2" sx={{ color: "rgba(255,255,255,0.82)" }}>
                {activeTabConfig.description}
              </Typography>
            </Box>
            <Box className="flex flex-wrap gap-2">
              <Chip
                label={selectedMaterial ? selectedMaterial.nombre : "Sin material"}
                sx={{ bgcolor: "rgba(255,255,255,0.14)", color: "white", fontWeight: 800 }}
              />
              <Chip label={`Horizonte ${forecastHorizon} meses`} sx={{ bgcolor: "rgba(255,255,255,0.14)", color: "white", fontWeight: 800 }} />
            </Box>
          </Box>
        </Box>
        <Box className="border-b border-slate-200 bg-white px-2 pt-2">
          <Box className="flex items-end overflow-x-auto">
            <Tabs
              value={activeView}
              onChange={(_event, value) => onViewChange(value)}
              variant="scrollable"
              scrollButtons="auto"
              allowScrollButtonsMobile
              className="w-full"
              sx={{
                minHeight: 0,
                width: "100%",
                "& .MuiTabs-indicator": {
                  height: 4,
                  borderRadius: 999,
                  backgroundColor: activeTabConfig.accent,
                },
                "& .MuiTabs-flexContainer": {
                  gap: 8,
                  flexWrap: "nowrap",
                  justifyContent: "flex-start",
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
                    minHeight: 0,
                    minWidth: "auto",
                    px: 2,
                    py: 1.5,
                    textTransform: "none",
                    fontSize: 14,
                    fontWeight: 800,
                    color: tab.accent,
                    "&.Mui-selected": {
                      color: activeTabConfig.accent,
                    },
                    "&.Mui-disabled": {
                      opacity: 0.45,
                      color: tab.accent,
                      fontStyle: "italic",
                    },
                  }}
                />
              ))}
            </Tabs>
          </Box>
        </Box>
        <Box className="bg-slate-50 px-4 py-3">
          <Typography color="text.secondary" variant="body2" fontWeight={700}>
            {activeTabConfig.description}
          </Typography>
        </Box>
      </CardContent>
    </Card>
  );
}
