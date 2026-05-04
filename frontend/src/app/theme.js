import { createTheme } from "@mui/material/styles";

export const theme = createTheme({
  palette: {
    mode: "light",
    primary: {
      main: "#002395",
      contrastText: "#FFFFFF",
    },
    secondary: {
      main: "#D35F00",
      contrastText: "#FFFFFF",
    },
    error: {
      main: "#BA1A1A",
    },
    background: {
      default: "#F0F2FA",
      paper: "#FEFBFF",
    },
    text: {
      primary: "#1A1B20",
      secondary: "#44474F",
    },
    divider: "#C5C6D0",
  },
  shape: {
    borderRadius: 8,
  },
  typography: {
    fontFamily: "Roboto, Inter, system-ui, sans-serif",
    h1: {
      fontSize: "clamp(2rem, 5vw, 3.5rem)",
      fontWeight: 800,
      letterSpacing: 0,
    },
    h2: {
      fontSize: "1.5rem",
      fontWeight: 700,
      letterSpacing: 0,
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
          borderRadius: 999,
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
            backgroundColor: "#001B75",
          },
        },
        containedSecondary: {
          "&:hover": {
            boxShadow: "none",
            backgroundColor: "#B04E00",
          },
        },
        outlined: {
          borderWidth: 1.5,
          backgroundColor: "#FEFBFF",
        },
        outlinedPrimary: {
          borderColor: "#002395",
          color: "#002395",
          "&:hover": {
            borderWidth: 1.5,
            borderColor: "#001B75",
            backgroundColor: "#EEF2FF",
          },
        },
        outlinedSecondary: {
          borderColor: "#D35F00",
          color: "#D35F00",
          "&:hover": {
            borderWidth: 1.5,
            borderColor: "#B04E00",
            backgroundColor: "#FFF1E7",
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
          borderRadius: 8,
          border: "1px solid #C5C6D0",
          boxShadow: "0 1px 2px rgba(0,0,0,.14), 0 4px 10px rgba(0,0,0,.08)",
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
