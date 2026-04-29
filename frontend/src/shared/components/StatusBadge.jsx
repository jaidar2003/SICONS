import { Chip } from "@mui/material";

export function StatusBadge({ mode, label }) {
  const color = mode === "ok" ? "secondary" : mode === "error" ? "error" : "primary";
  return <Chip color={color} label={label} size="small" variant={mode === "ok" ? "filled" : "outlined"} />;
}

