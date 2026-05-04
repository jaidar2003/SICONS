export const API_BASE_URL =
  import.meta.env.VITE_BUILDWISE_API_URL ||
  window.BUILDWISE_API_URL ||
  import.meta.env.VITE_SICONS_API_URL ||
  window.SICONS_API_URL ||
  "http://localhost:8000";
