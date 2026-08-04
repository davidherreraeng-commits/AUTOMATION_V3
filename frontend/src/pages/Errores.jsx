import React, { useEffect, useState } from "react";
import {
  Card,
  CardContent,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Paper,
} from "@mui/material";
import axios from "../api/axiosConfig";

const Errores = () => {
  const [errores, setErrores] = useState([]);

  useEffect(() => {
    const fetchErrores = async () => {
      try {
        const response = await axios.get("/errores_contratos");
        setErrores(response.data);
      } catch (error) {
        console.error("❌ Error al cargar errores de contratos:", error);
      }
    };

    fetchErrores();
  }, []);

  return (
    <Card sx={{ padding: 2 }}>
      <CardContent>
        <Typography variant="h6" gutterBottom color="error">
          ⚠️ Errores Críticos de Contratos
        </Typography>
        <Paper sx={{ overflowX: "auto" }}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Número de Contrato</TableCell>
                <TableCell>Dependencia</TableCell>
                <TableCell>Campos Faltantes</TableCell>
                <TableCell>Fecha de Error</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {errores.map((row, idx) => (
                <TableRow key={idx}>
                  <TableCell>{row.numero_contrato}</TableCell>
                  <TableCell>{row.dependencia}</TableCell>
                  <TableCell>{row.campos_faltantes}</TableCell>
                  <TableCell>{row.fecha_error}</TableCell>
                </TableRow>
              ))}
              {errores.length === 0 && (
                <TableRow>
                  <TableCell colSpan={4} align="center">
                    No se encontraron errores críticos.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </Paper>
      </CardContent>
    </Card>
  );
};

export default Errores;