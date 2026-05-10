import { createTheme } from "@mui/material/styles";

import { brand } from "./brand.js";

export const theme = createTheme({
  palette: {
    mode: "light",
    primary: {
      main: brand.colors.primary,
      light: brand.colors.primarySoft,
      dark: brand.colors.primaryHover,
      contrastText: brand.colors.inverse,
    },
    secondary: {
      main: brand.colors.secondary,
      light: brand.colors.secondarySoft,
      dark: brand.colors.secondaryHover,
      contrastText: brand.colors.inverse,
    },
    error: {
      main: brand.colors.error,
    },
    background: {
      default: brand.colors.surfaceContainer,
      paper: brand.colors.surface,
    },
    text: {
      primary: brand.colors.text,
      secondary: brand.colors.textMuted,
    },
    divider: brand.colors.border,
  },
  shape: {
    borderRadius: brand.radii.card,
  },
  typography: {
    fontFamily: brand.fonts.body,
    h1: {
      fontSize: "clamp(2rem, 5vw, 3.5rem)",
      fontWeight: 800,
      letterSpacing: 0,
    },
    h2: {
      fontSize: "1.375rem",
      fontWeight: 800,
      letterSpacing: 0,
    },
    h3: {
      fontSize: "1.125rem",
      fontWeight: 800,
      letterSpacing: 0,
    },
    subtitle1: {
      fontSize: "0.95rem",
      fontWeight: 600,
      lineHeight: 1.5,
    },
    body2: {
      fontSize: "0.875rem",
      lineHeight: 1.5,
    },
    button: {
      fontWeight: 700,
      letterSpacing: 0,
      textTransform: "none",
    },
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          minHeight: 40,
          boxShadow: "none",
          borderRadius: brand.radii.pill,
          paddingInline: 18,
          fontWeight: 800,
          lineHeight: 1,
        },
        contained: {
          boxShadow: "none",
        },
        containedPrimary: {
          "&:hover": {
            boxShadow: "none",
            backgroundColor: brand.colors.primaryHover,
          },
        },
        containedSecondary: {
          "&:hover": {
            boxShadow: "none",
            backgroundColor: brand.colors.secondaryHover,
          },
        },
        outlined: {
          borderWidth: 1.5,
          backgroundColor: brand.colors.surface,
        },
        outlinedPrimary: {
          borderColor: brand.colors.primary,
          color: brand.colors.primary,
          "&:hover": {
            borderWidth: 1.5,
            borderColor: brand.colors.primaryHover,
            backgroundColor: brand.colors.primarySoft,
          },
        },
        outlinedSecondary: {
          borderColor: brand.colors.secondary,
          color: brand.colors.secondary,
          "&:hover": {
            borderWidth: 1.5,
            borderColor: brand.colors.secondaryHover,
            backgroundColor: brand.colors.secondarySoft,
          },
        },
      },
    },
    MuiButtonGroup: {
      styleOverrides: {
        grouped: {
          minWidth: 52,
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: brand.radii.card,
          border: `1px solid ${brand.colors.border}`,
          boxShadow: brand.shadows.card,
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: brand.radii.pill,
          fontWeight: 800,
        },
      },
    },
    MuiTextField: {
      defaultProps: {
        size: "small",
      },
    },
    MuiFormControl: {
      defaultProps: {
        size: "small",
      },
    },
  },
});
