import React, { useEffect, useState } from "react";
import axios from "../api/axiosConfig";
import {
  Box, Typography, Table, TableBody, TableCell, TableContainer,
  TableHead, TableRow, Paper, Stack, Button, MenuItem, Select,
  FormControl, InputLabel, IconButton, Dialog, DialogTitle, DialogContent
} from "@mui/material";
import { jsPDF } from "jspdf";
import autoTable from "jspdf-autotable";
import * as XLSX from "xlsx";
import VisibilityIcon from "@mui/icons-material/Visibility";
import { DatePicker, LocalizationProvider } from "@mui/x-date-pickers";
import { AdapterDayjs } from "@mui/x-date-pickers/AdapterDayjs";
import dayjs from "dayjs";

function Historial() {
  const [historial, setHistorial] = useState([]);
  const [filtroDep, setFiltroDep] = useState("");
  const [fechaInicio, setFechaInicio] = useState(null);
  const [fechaFin, setFechaFin] = useState(null);

  const [detalleContrato, setDetalleContrato] = useState([]);
  const [openModal, setOpenModal] = useState(false);
  const [modalTitulo, setModalTitulo] = useState("");

  useEffect(() => {
    axios.get("http://localhost:8000/historial")
      .then((res) => setHistorial(res.data))
      .catch((err) => console.error("❌ Error al cargar historial", err));
  }, []);

  const historialFiltrado = historial.filter(item => {
    const cumpleDep = !filtroDep || item.dependencia === filtroDep;
    const fecha = dayjs(item.fecha, "YYYY-MM-DD HH:mm:ss");
    const cumpleInicio = !fechaInicio || fecha.isAfter(fechaInicio.subtract(1, "day"));
    const cumpleFin = !fechaFin || fecha.isBefore(fechaFin.add(1, "day"));
    return cumpleDep && cumpleInicio && cumpleFin;
  });

  const exportarPDF = () => {
    const doc = new jsPDF();
    const fecha = new Date().toLocaleString();
    const img = new Image();
    img.src = "/logo-poli.png";
    img.onload = () => {
      doc.addImage(img, "PNG", 10, 10, 30, 30);
      doc.setFontSize(14);
      doc.text("Politécnico Jaime Isaza Cadavid", 50, 18);
      doc.setFontSize(11);
      doc.text("Módulo de Automatización de Contratos", 50, 25);
      doc.text(`Exportado: ${fecha}`, 50, 32);
      doc.line(10, 38, 200, 38);

      const columnas = ["Fecha", "Dependencia", "Archivo", "# Contratos", "Estado"];
      const filas = historialFiltrado.map(h => [
        h.fecha, h.dependencia, h.archivo, h.cantidad_contratos, h.estado
      ]);

      autoTable(doc, {
        startY: 42,
        head: [columnas],
        body: filas,
        styles: { fontSize: 9 },
        margin: { left: 14, right: 14 }
      });

      doc.save("Historial_Automatizaciones.pdf");
    };
  };

  const exportarExcel = () => {
    const ws = XLSX.utils.json_to_sheet(historialFiltrado);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "Historial");
    XLSX.writeFile(wb, "Historial_Automatizaciones.xlsx");
  };

  const verDetalleArchivo = async (dependencia, archivo) => {
  try {
    const res = await axios.get(`http://localhost:8000/ver_archivo_excel?dependencia=${dependencia}&archivo=${archivo}`);
    setDetalleContrato(res.data);
    setModalTitulo(`Contratos procesados en ${archivo}`);
    setOpenModal(true);
  } catch (err) {
    console.error("❌ Error al cargar el archivo:", err);

    if (err.response?.status === 404) {
      alert("⚠️ El archivo ya no se encuentra en el servidor. Es posible que haya sido eliminado.");
    } else {
      alert("❌ Error inesperado al consultar el detalle del archivo.");
    }
  }
};

  const exportarDetallePDF = () => {
    const doc = new jsPDF();
    const fecha = new Date().toLocaleString();
    doc.setFontSize(12);
    doc.text(modalTitulo, 14, 20);
    doc.setFontSize(10);
    doc.text(`Exportado: ${fecha}`, 14, 26);

    if (detalleContrato.length > 0) {
      const columnas = Object.keys(detalleContrato[0]);
      const filas = detalleContrato.map(row => columnas.map(c => row[c]));

      autoTable(doc, {
        startY: 32,
        head: [columnas],
        body: filas,
        styles: { fontSize: 8 },
        margin: { left: 14, right: 14 }
      });
    }

    doc.save(modalTitulo.replace(/\s/g, "_") + ".pdf");
  };

  const exportarDetalleExcel = () => {
    const ws = XLSX.utils.json_to_sheet(detalleContrato);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "Contratos");
    XLSX.writeFile(wb, modalTitulo.replace(/\s/g, "_") + ".xlsx");
  };

  return (
    <Box p={3}>
      <Typography variant="h5" color="#005026" fontWeight="bold" mb={2}>Historial de Automatizaciones</Typography>

      <Stack direction="row" spacing={2} alignItems="center" mb={2}>
        <FormControl sx={{ minWidth: 150 }}>
          <InputLabel>Dependencia</InputLabel>
          <Select value={filtroDep} label="Dependencia" onChange={(e) => setFiltroDep(e.target.value)}>
            <MenuItem value="">Todas</MenuItem>
            <MenuItem value="Adquisiciones">Adquisiciones</MenuItem>
            <MenuItem value="Proyectos">Proyectos</MenuItem>
          </Select>
        </FormControl>

        <LocalizationProvider dateAdapter={AdapterDayjs}>
          <DatePicker label="Desde" value={fechaInicio} onChange={(v) => setFechaInicio(v)} />
          <DatePicker label="Hasta" value={fechaFin} onChange={(v) => setFechaFin(v)} />
        </LocalizationProvider>

        <Button variant="contained" sx={{ backgroundColor: '#005026', color: 'white', '&:hover': { backgroundColor: '#00441f' } }} onClick={exportarPDF}>Exportar PDF</Button>
        <Button variant="contained" sx={{ backgroundColor: '#FFC600', color: 'black', '&:hover': { backgroundColor: '#e6b800' } }} onClick={exportarExcel}>Exportar Excel</Button>
      </Stack>

      <TableContainer component={Paper}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell><b>Fecha</b></TableCell>
              <TableCell><b>Dependencia</b></TableCell>
              <TableCell><b>Archivo</b></TableCell>
              <TableCell><b># Contratos</b></TableCell>
              <TableCell><b>Estado</b></TableCell>
              <TableCell><b>Acciones</b></TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {historialFiltrado.map((row, i) => (
              <TableRow key={i}>
                <TableCell>{row.fecha}</TableCell>
                <TableCell>{row.dependencia}</TableCell>
                <TableCell>{row.archivo}</TableCell>
                <TableCell>{row.cantidad_contratos}</TableCell>
                <TableCell>{row.estado}</TableCell>
                <TableCell>
                  <Stack direction="row" spacing={1}>
                    <IconButton color="primary" onClick={() => verDetalleArchivo(row.dependencia, row.archivo)}>
                      <VisibilityIcon />
                    </IconButton>
                    {row.archivo_pdf && (
                      <a
                        href={`http://localhost:8000/descargar_informe?dependencia=${row.dependencia}&archivo_pdf=${row.archivo_pdf}`}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        <Button variant="outlined" size="small">Informe PDF</Button>
                      </a>
                    )}
                  </Stack>
                </TableCell>
              </TableRow>
            ))}
            {historialFiltrado.length === 0 && (
              <td colSpan={6} style={{ textAlign: "center", padding: "20px", color: "#666" }}>
                No hay informes disponibles. Ejecuta una automatización para generar uno nuevo.
              </td>
            )}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={openModal} onClose={() => setOpenModal(false)} maxWidth="lg" fullWidth>
        <DialogTitle>{modalTitulo}</DialogTitle>
        <DialogContent dividers>
          <Stack direction="row" spacing={2} mb={2}>
            <Button variant="outlined" onClick={exportarDetallePDF}>Exportar PDF</Button>
            <Button variant="outlined" onClick={exportarDetalleExcel}>Exportar Excel</Button>
          </Stack>
          <TableContainer component={Paper}>
            <Table size="small">
              <TableHead>
                {detalleContrato.length > 0 && (
                  <TableRow>
                    {Object.keys(detalleContrato[0]).map((key, i) => (
                      <TableCell key={i}><b>{key}</b></TableCell>
                    ))}
                  </TableRow>
                )}
              </TableHead>
              <TableBody>
                {detalleContrato.map((row, i) => (
                  <TableRow key={i}>
                    {Object.values(row).map((val, j) => (
                      <TableCell key={j}>{val}</TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </DialogContent>
      </Dialog>
    </Box>
  );
}

export default Historial;