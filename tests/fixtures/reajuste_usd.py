"""Un contrato FICTICIO en USD para el reajuste con índices expresados en USD (RF-214).

Versión 001 en USD: una partida (PU 100 USD, 1.000 unidades). Los índices y las tasas NO se siembran
aquí: la prueba de punta a punta los importa por la API con `CSV_INDICES` y `CSV_TASAS`.

Cuentas a mano (bitácora `2026-11-13-ola2-pdf-e-indices.md` §2):
- FIC-INPC (índice en Bs): enero de 2026 = 200; febrero de 2027 = 276.
- Tasa de venta del BCV: 40 Bs/USD todos los días de enero de 2026 (la del 29/12/2025 cubre del 1
  al 4 de enero, S1-R1) y 46 todos los de febrero de 2027 (la del 29/01/2027 cubre del 1 al 4).
- En USD: 200 ÷ 40 = 5 y 276 ÷ 46 = 6; Km = 6 ÷ 5 = 1,2; escalatoria = 1.000 × 100 × 0,2 ×
  (1 − 0,10) = 18.000,00 USD (828.000,00 Bs a 46). Con el índice en Bs: Km = 1,38 y
  34.200,00 USD, que cuenta dos veces la devaluación.
"""

from datetime import date
from decimal import Decimal as D  # noqa: N817

from core import models
from core.budget import crear_proyecto, elaborar, guardar_presupuesto
from core.catalog import Catalogo
from core.contracts import ComposicionAPU, Dominio, ItemComputo, LineaMaterial, ParametrosCosto
from core.contracts.item_computo import OrigenTipo

CERO = ParametrosCosto(D(0), D(0), D(0), D(0))
NOMBRE = "Contrato ficticio en USD (reajuste)"
PARTIDA = "USD-R01"
FUENTE = "https://www.bcv.org.ve/ (valores FICTICIOS de prueba)"

_TASAS = [
    ("2025-12-29", "40"),
    ("2026-01-05", "40"),
    ("2026-01-12", "40"),
    ("2026-01-19", "40"),
    ("2026-01-26", "40"),
    ("2027-01-29", "46"),
    ("2027-02-05", "46"),
    ("2027-02-12", "46"),
    ("2027-02-19", "46"),
    ("2027-02-26", "46"),
]
CSV_INDICES = (
    "serie,fecha,valor,provisional,fuente\n"
    f"FIC-INPC,2026-01-01,200,no,{FUENTE}\n"
    f"FIC-INPC,2027-02-01,276,no,{FUENTE}\n"
).encode()
CSV_TASAS = (
    "serie,fecha,valor,provisional,fuente\n"
    + "".join(f"BCV-USD-VENTA,{f},{v},no,{FUENTE}\n" for f, v in _TASAS)
).encode()
DEFINICION_INDICE = {
    "serie": "FIC-INPC",
    "nombre": "INPC ficticio",
    "organismo": "BCV (ficticio)",
    "unidad": "indice_bs",
    "periodicidad": "mensual",
}
DEFINICION_TASA = {
    "serie": "BCV-USD-VENTA",
    "nombre": "Tasa de referencia USD (venta)",
    "organismo": "BCV",
    "unidad": "Bs/USD",
    "periodicidad": "diaria",
}
CAMPOS = {
    "fecha_inicio": "2026-01-15",
    "duracion_meses": "24",
    "fecha_referencia_primer_anio": "2026-01-15",
    "periodicidad": "mensual",
    "mecanismo": "escalatoria",
    "estructura": "declarada",
    "fecha_base_indices": "2026-01-01",
    "r": "0.10",
    "fuente_r": "contrato ficticio",
    "fuente": "contrato ficticio en USD",
    "responsable": "Ing. Prueba",
}
PERIODOS = [
    {"desde": "2027-02-01", "hasta": "2027-02-28", "version_comprobacion": "", "excepcion": ""}
]
EJECUTADO = [{"periodo": "1", "partida": PARTIDA, "cantidad": "1000", "fuente": "AV-01 ficticia"}]


def componentes(serie: str) -> list[dict[str, str]]:
    return [{"componente": "materiales", "serie": serie, "peso": "1"}]


def sembrar(sesion) -> None:
    lista = models.ListaPrecios(
        nombre="Contrato ficticio USD", moneda="USD", fecha_vigencia=date(2026, 1, 15)
    )
    sesion.add(lista)
    sesion.flush()
    apu = ComposicionAPU(
        PARTIDA,
        "Partida ficticia en dólares",
        "m3",
        D(1),
        (LineaMaterial("Insumo ficticio en dólares", "m3", D(1), D(100)),),
    )
    Catalogo(sesion).cargar_composicion(apu, lista, Dominio.CIVIL, date(2026, 1, 15), "ficticio")
    item = ItemComputo(
        PARTIDA, "Partida ficticia", "m3", D(1000), "ficticio", OrigenTipo.MANUAL, Dominio.CIVIL
    )
    hecho = elaborar(
        [item], {PARTIDA: apu}, CERO, codigo="001", fecha=date(2026, 1, 15), moneda="USD"
    )
    proyecto = crear_proyecto(sesion, NOMBRE)
    guardar_presupuesto(
        sesion, hecho.presupuesto, hecho.informe, proyecto=proyecto, lista=lista, parametros=CERO
    )
    sesion.flush()
