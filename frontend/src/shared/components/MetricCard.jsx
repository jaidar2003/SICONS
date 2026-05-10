import { Card, CardContent, Typography } from "@mui/material";

export function MetricCard({ label, value, helper }) {
  return (
    <Card>
      <CardContent className="relative min-h-[124px] overflow-hidden">
        <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-md-primary to-md-secondary" />
        <Typography color="text.secondary" fontSize={12} fontWeight={800}>
          {label}
        </Typography>
        <Typography component="strong" display="block" fontSize={{ xs: 24, md: 30 }} fontWeight={800} lineHeight={1.1} mt={1} sx={{ overflowWrap: "anywhere" }}>
          {value}
        </Typography>
        <Typography color="text.secondary" fontSize={13} mt={0.75}>
          {helper}
        </Typography>
      </CardContent>
    </Card>
  );
}
