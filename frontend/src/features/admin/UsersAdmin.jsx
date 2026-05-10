import { useEffect, useState } from "react";
import { Alert, Box, Button, Card, CardContent, Chip, Table, TableBody, TableCell, TableHead, TableRow, Typography } from "@mui/material";

import { SectionHeader } from "../../shared/components/SectionHeader.jsx";
import { activateUser, deleteUser, fetchUsers } from "./admin.api.js";

function formatDate(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "-";
  return new Intl.DateTimeFormat("es-AR", { day: "2-digit", month: "2-digit", year: "2-digit" }).format(date);
}

export function UsersAdmin({ token }) {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [activatingId, setActivatingId] = useState(null);
  const [deletingId, setDeletingId] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!token) return;

    let cancelled = false;

    async function loadUsers() {
      setLoading(true);
      setError("");
      try {
        const data = await fetchUsers(token);
        if (!cancelled) {
          setUsers(data);
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError.message);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadUsers();

    return () => {
      cancelled = true;
    };
  }, [token]);

  async function handleActivate(userId) {
    if (!token) return;

    setActivatingId(userId);
    setError("");
    try {
      await activateUser(userId, token);
      const data = await fetchUsers(token);
      setUsers(data);
    } catch (activateError) {
      setError(activateError.message);
    } finally {
      setActivatingId(null);
    }
  }

  async function handleDelete(userId, username) {
    if (!token) return;
    if (!window.confirm(`Eliminar la cuenta ${username}? Esta accion no se puede deshacer.`)) return;

    setDeletingId(userId);
    setError("");
    try {
      await deleteUser(userId, token);
      const data = await fetchUsers(token);
      setUsers(data);
    } catch (deleteError) {
      setError(deleteError.message);
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <Card className="mt-3">
      <CardContent>
        <SectionHeader
          title="Usuarios registrados"
          description="Listado de accesos habilitados en el sistema. Esta vista es solo para administracion."
        />

        {error ? <Alert severity="error">{error}</Alert> : null}
        {!error && !loading && !users.length ? <Alert severity="info">No hay usuarios registrados.</Alert> : null}

        {loading ? (
          <Alert severity="info">Cargando usuarios...</Alert>
        ) : (
          <Box className="overflow-x-auto">
            <Table size="small">
              <TableHead>
                  <TableRow>
                    <TableCell>Usuario</TableCell>
                    <TableCell>Email</TableCell>
                    <TableCell>Nombre</TableCell>
                    <TableCell>Rol</TableCell>
                    <TableCell>Estado</TableCell>
                    <TableCell>Alta</TableCell>
                    <TableCell align="right">Accion</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {users.map((user) => (
                    <TableRow key={user.id} hover>
                    <TableCell>
                      <Typography fontWeight={800}>{user.username}</Typography>
                    </TableCell>
                    <TableCell>{user.email || "-"}</TableCell>
                    <TableCell>{user.nombre}</TableCell>
                    <TableCell>
                      <Chip size="small" label={user.rol} color={user.rol === "admin" ? "primary" : "default"} />
                    </TableCell>
                    <TableCell>
                      <Chip size="small" label={user.activo ? "Activo" : "Inactivo"} color={user.activo ? "success" : "default"} />
                    </TableCell>
                    <TableCell>{formatDate(user.created_at)}</TableCell>
                    <TableCell align="right">
                      <Box className="flex flex-wrap justify-end gap-2">
                        {!user.activo ? (
                          <Button size="small" variant="contained" disabled={activatingId === user.id} onClick={() => handleActivate(user.id)}>
                            {activatingId === user.id ? "Habilitando" : "Habilitar y enviar mail"}
                          </Button>
                        ) : null}
                        {user.rol !== "admin" ? (
                          <Button
                            size="small"
                            color="error"
                            variant="outlined"
                            disabled={deletingId === user.id}
                            onClick={() => handleDelete(user.id, user.username)}
                          >
                            {deletingId === user.id ? "Eliminando" : "Eliminar y avisar"}
                          </Button>
                        ) : (
                          "-"
                        )}
                      </Box>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Box>
        )}
      </CardContent>
    </Card>
  );
}
