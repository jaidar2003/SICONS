import { Badge, Box, Divider, IconButton, List, ListItem, ListItemText, Menu, Typography } from "@mui/material";
import NotificationsIcon from "@mui/icons-material/Notifications";
import { useCallback, useEffect, useState } from "react";
import dayjs from "dayjs";

import { listAlerts, markAlertsAsRead } from "./alerts.api.js";

export function AlertsMenu({ token }) {
  const [anchorEl, setAnchorEl] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);

  const fetchAlerts = useCallback(async () => {
    try {
      const data = await listAlerts({ solo_no_leidas: true }, token);
      setAlerts(data);
      setUnreadCount(data.length);
    } catch (error) {
      console.error("Error fetching alerts:", error);
    }
  }, [token]);

  useEffect(() => {
    if (token) {
      fetchAlerts();
      const interval = setInterval(fetchAlerts, 60000); // Polling cada 1 min
      return () => clearInterval(interval);
    }
  }, [fetchAlerts, token]);

  const handleOpen = (event) => setAnchorEl(event.currentTarget);
  const handleClose = () => setAnchorEl(null);

  const handleMarkAsRead = async () => {
    if (alerts.length === 0) return;
    try {
      const ids = alerts.map(a => a.id);
      await markAlertsAsRead(ids, token);
      setAlerts([]);
      setUnreadCount(0);
    } catch (error) {
      console.error("Error marking alerts as read:", error);
    }
  };

  return (
    <>
      <IconButton color="inherit" onClick={handleOpen}>
        <Badge badgeContent={unreadCount} color="error">
          <NotificationsIcon />
        </Badge>
      </IconButton>
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleClose}
        PaperProps={{
          sx: { width: 360, maxHeight: 400, mt: 1.5, borderRadius: 2 }
        }}
      >
        <Box px={2} py={1} display="flex" justifyContent="space-between" alignItems="center">
          <Typography variant="subtitle1" fontWeight={700}>Alertas Proactivas</Typography>
          {unreadCount > 0 && (
            <Typography 
              variant="caption" 
              color="primary" 
              sx={{ cursor: 'pointer', fontWeight: 600 }}
              onClick={handleMarkAsRead}
            >
              Marcar todas como leídas
            </Typography>
          )}
        </Box>
        <Divider />
        <List sx={{ p: 0 }}>
          {alerts.length === 0 ? (
            <ListItem>
              <ListItemText 
                secondary="No hay alertas nuevas en este momento." 
                secondaryTypographyProps={{ align: 'center', py: 2 }}
              />
            </ListItem>
          ) : (
            alerts.map((alerta) => (
              <ListItem key={alerta.id} divider>
                <ListItemText
                  primary={
                    <Typography variant="body2" fontWeight={700} color={alerta.prioridad === 'ALTA' ? 'error' : 'textPrimary'}>
                      {alerta.titulo}
                    </Typography>
                  }
                  secondary={
                    <>
                      <Typography variant="caption" display="block" color="textSecondary">
                        {alerta.mensaje}
                      </Typography>
                      <Typography variant="caption" color="textSecondary" sx={{ fontSize: '0.7rem' }}>
                        {dayjs(alerta.created_at).format("DD/MM/YY HH:mm")}
                      </Typography>
                    </>
                  }
                />
              </ListItem>
            ))
          )}
        </List>
      </Menu>
    </>
  );
}
