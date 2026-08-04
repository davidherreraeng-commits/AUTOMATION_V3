import React from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Divider,
  Stack
} from "@mui/material";

function ContractModal({ open, onClose, contrato }) {
  if (!contrato) return null;

  const mostrarCampo = (label, key) => (
    <Typography variant="body2">
      <strong>{label}:</strong> {contrato[key] || "—"}
    </Typography>
  );

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>Detalles del contrato #{contrato["No. de Contrato"]}</DialogTitle>
      <DialogContent dividers>
        <Stack spacing={1.2}>
          {mostrarCampo("Tipo de Contratista", "Tipo de Contratista")}
          {mostrarCampo("Cédula o Nit", "Cédula o Nit Contratista")}
          {mostrarCampo("Código del Proyecto", "Código del Proyecto")}
          {mostrarCampo("Objeto del Contrato", "Objeto del Contrato")}
          {mostrarCampo("Supervisor", "Nombre del Supervisor") || mostrarCampo("Cédula Supervisor", "Cédula Supervisor")}
          {mostrarCampo("Fecha de Suscripción", "Fecha de Suscripción")}
          {mostrarCampo("Modalidad", "Modalidad o Proceso")}
          {mostrarCampo("Procedimiento/Causal", "Procedimiento/Causal")}
          {mostrarCampo("Tipo de Contrato", "Tipo de Contrato")}
          {mostrarCampo("Valor", "Valor")}
          {mostrarCampo("Plazo Estimado (En Días)", "Plazo Estimado (En Dias)")}
          {mostrarCampo("Fecha Publicación SECOP II", "Fecha Publicación SECOP II")}
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} variant="contained">Cerrar</Button>
      </DialogActions>
    </Dialog>
  );
}

export default ContractModal;