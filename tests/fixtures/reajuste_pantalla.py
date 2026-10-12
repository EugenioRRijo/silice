"""Los textos de la pantalla de reajuste para el contrato de `reajuste_s1` (UC-18)."""

CAMPOS = {
    "fecha_inicio": "2026-01-15",
    "duracion_meses": "24",
    "fecha_referencia_primer_anio": "2026-01-15",
    "periodicidad": "mensual",
    "mecanismo": "ambos",
    "estructura": "declarada",
    "fecha_base_indices": "2026-01-01",
    "r": "0.10",
    "fuente_r": "memoria",
    "fuente": "contrato ficticio",
    "responsable": "Ing.",
}
COMPONENTES = [
    {"componente": "materiales", "serie": "FIC-MAT", "peso": "0.5"},
    {"componente": "equipos", "serie": "FIC-EQU", "peso": "0.2"},
    {"componente": "mano_obra", "serie": "FIC-MO", "peso": "0.3"},
]
PERIODOS = [
    {"desde": "2027-02-01", "hasta": "2027-02-28", "version_comprobacion": "002", "excepcion": ""}
]
EJECUTADO = [{"periodo": "1", "partida": "S1-R01", "cantidad": "1000", "fuente": "AV-01"}]
