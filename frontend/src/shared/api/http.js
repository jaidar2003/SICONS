import { API_BASE_URL } from "../../app/config.js";

export async function apiGet(path, token) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
  });
  if (!response.ok) {
    throw new Error(`API ${response.status}: ${path}`);
  }
  return response.json();
}

export async function apiPost(path, payload, token) {
  const headers = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers,
    body: JSON.stringify(payload),
  });
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(data?.detail || `API ${response.status}: ${path}`);
  }
  return data;
}

export async function apiPatch(path, payload, token) {
  const headers = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "PATCH",
    headers,
    body: JSON.stringify(payload),
  });
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(data?.detail || `API ${response.status}: ${path}`);
  }
  return data;
}

export async function apiDelete(path, token) {
  const headers = {};
  if (token) headers.Authorization = `Bearer ${token}`;

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "DELETE",
    headers,
  });
  if (!response.ok && response.status !== 204) {
    const data = await response.json().catch(() => null);
    throw new Error(data?.detail || `API ${response.status}: ${path}`);
  }
  return null;
}
