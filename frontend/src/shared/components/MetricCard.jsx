import { Card, CardContent, Typography } from "@mui/material";

export function MetricCard({ label, value, helper, control, valueFontSize, valueSx }) {
  return (
    <Card>
      <CardContent className="relative min-h-[124px] overflow-hidden">
        <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-md-primary to-md-secondary" />
        <div className="flex items-start justify-between gap-2">
          <Typography color="text.secondary" fontSize={12} fontWeight={800}>
            {label}
          </Typography>
          {control ? <div className="shrink-0">{control}</div> : null}
        </div>
        <Typography
          component="strong"
          display="block"
          fontSize={valueFontSize || { xs: 24, md: 30 }}
          fontWeight={800}
          lineHeight={1.1}
          mt={1}
          sx={{ overflowWrap: "anywhere", ...valueSx }}
        >
          {value}
        </Typography>
        <Typography color="text.secondary" fontSize={13} mt={0.75}>
          {helper}
        </Typography>
      </CardContent>
    </Card>
  );
}
