import { Box, Chip, Typography } from "@mui/material";

export function SectionHeader({ title, description, badge, action }) {
  return (
    <Box className="mb-3 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
      <Box>
        <Typography variant="h2">{title}</Typography>
        {description ? (
          <Typography color="text.secondary" mt={0.5}>
            {description}
          </Typography>
        ) : null}
      </Box>
      <Box className="flex items-center gap-2">
        {badge ? <Chip color="secondary" label={badge} size="small" variant="outlined" /> : null}
        {action}
      </Box>
    </Box>
  );
}
