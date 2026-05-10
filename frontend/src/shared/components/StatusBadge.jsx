import { Chip } from "@mui/material";

import { brand } from "../../app/brand.js";

export function StatusBadge({ mode, label }) {
  if (mode === "ok") {
    return (
      <Chip
        label={label}
        size="small"
        sx={{
          bgcolor: brand.colors.successSoft,
          color: brand.colors.success,
          border: `1px solid ${brand.colors.success}33`,
          fontWeight: 800,
        }}
      />
    );
  }

  const color = mode === "error" ? brand.colors.error : brand.colors.primary;
  const background = mode === "error" ? brand.colors.secondarySoft : brand.colors.primarySoft;

  return (
    <Chip
      label={label}
      size="small"
      variant="outlined"
      sx={{
        bgcolor: background,
        color,
        borderColor: color,
        fontWeight: 800,
      }}
    />
  );
}
