import { Box, Chip, Typography } from "@mui/material";

export function SectionHeader({ title, description, badge, action }) {
  return (
    <Box className="mb-3 flex min-w-0 flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
      <Box className="min-w-0">
        <Typography variant="h2">{title}</Typography>
        {description ? (
          <Typography color="text.secondary" variant="body2" mt={0.5}>
            {description}
          </Typography>
        ) : null}
      </Box>
      <Box className="flex shrink-0 items-center gap-2">
        {badge ? <Chip color="secondary" label={badge} size="small" variant="outlined" /> : null}
        {action}
      </Box>
    </Box>
  );
}
