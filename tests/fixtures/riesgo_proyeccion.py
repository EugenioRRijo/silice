"""Fixtures ficticias compartidas por las pruebas de la proyección y de la comprobación hacia atrás
del riesgo (plan vial, Tareas 13 y 14): insumos, recetas, series y tasa inventados, ninguna cifra
real. Las pruebas no se importan entre sí (norma de arquitectura): lo común vive aquí."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from aplicacion.riesgo.proyeccion import SERIE_TASA
from core.budget import generar_presupuesto
from core.contracts.apu import ComposicionAPU, LineaMaterial, ParametrosCosto
from core.contracts.dominio import Dominio
from core.contracts.item_computo import ItemComputo, OrigenTipo
from produccion.receta import Componente, Receta

D = Decimal
PPI = "CEMENTO_ASFALTICO_PPI"
GASOIL = "GASOIL_USD"
INICIO = date(2027, 1, 1)
CIEN = Decimal(100)
UNO = Decimal(1)
CASCADA = D("1.15") * D("1.10")  # administración y utilidad en cascada: 1,265
PARAMETROS = ParametrosCosto(
    fcas=D(0), bono_alimentacion=D(0), administracion=D("0.15"), utilidad=D("0.10")
)
TOLERANCIA = D("0.000001")

#: Suma de 1,01^k para k = 1..6, escrita a mano (véase el encabezado).
SUMA_UNO_POR_CIENTO = D("6.213535210701")
F_UNO = SUMA_UNO_POR_CIENTO / 6

MEZCLA = "Costo propio de mezcla 01"
ASFALTO = "Cemento asfáltico"
GASOIL_LITRO = "Gasoil"
FLETE = "Flete"


# --- Historia ficticia ----------------------------------------------------------------------------


def _mes(base: date, desplazamiento: int) -> date:
    indice = base.year * 12 + base.month - 1 + desplazamiento
    return date(indice // 12, indice % 12 + 1, 1)


def _meses(n: int, *, hasta_antes_de: date = INICIO) -> list[date]:
    """Los `n` meses que terminan el mes anterior a `hasta_antes_de`, en orden."""
    return [_mes(hasta_antes_de, -i) for i in range(n, 0, -1)]


def _creciente(variacion: Decimal, n: int = 37, inicial: Decimal = CIEN) -> dict[date, Decimal]:
    """`n` meses con la misma variación mensual (37 puntos = 36 variaciones antes de INICIO)."""
    return {m: inicial * variacion**i for i, m in enumerate(_meses(n))}


def _con_variaciones(variaciones: list[Decimal], inicial: Decimal = CIEN) -> dict[date, Decimal]:
    valores = [inicial]
    for v in variaciones:
        valores.append(valores[-1] * v)
    return dict(zip(_meses(len(valores)), valores, strict=True))


def _historia(ppi=UNO, gasoil=UNO, tasa=UNO, n: int = 37):
    return {
        PPI: _creciente(ppi, n),
        GASOIL: _creciente(gasoil, n),
        SERIE_TASA: _creciente(tasa, n, inicial=D(40)),
    }


def _promedio_compuesto(variacion: Decimal, meses: int = 6) -> Decimal:
    """El oráculo del gasto uniforme: promedio de variacion^k, k = 1..meses."""
    return sum((variacion**k for k in range(1, meses + 1)), D(0)) / meses


# --- Presupuesto ficticio -------------------------------------------------------------------------


def _apu(codigo: str, lineas: list[tuple[str, str, Decimal, Decimal]]) -> ComposicionAPU:
    return ComposicionAPU(
        codigo_partida=codigo,
        descripcion=f"Partida ficticia {codigo}",
        unidad="t",
        rendimiento=D(1),
        materiales=tuple(LineaMaterial(d, u, q, p) for d, u, q, p in lineas),
    )


CARPETA = _apu("VIA-01", [(MEZCLA, "t", D(1), D("46.75"))])
RIEGO = _apu("VIA-02", [(ASFALTO, "t", D("0.5"), D(600)), (GASOIL_LITRO, "l", D(10), D("0.5"))])
TRANSPORTE = _apu("VIA-03", [(FLETE, "t", D(1), D(20))])


def _obra(cantidades: dict[ComposicionAPU, Decimal], moneda: str = "USD"):
    composiciones = {apu.codigo_partida: apu for apu in cantidades}
    items = [
        ItemComputo(
            codigo_partida=apu.codigo_partida,
            descripcion=apu.descripcion,
            unidad=apu.unidad,
            cantidad=cantidad,
            origen_id=f"ficticio:{apu.codigo_partida}",
            origen_tipo=OrigenTipo.MANUAL,
            dominio=Dominio.CIVIL,
        )
        for apu, cantidad in cantidades.items()
    ]
    presupuesto = generar_presupuesto(
        items, composiciones, PARAMETROS, codigo="RV-1", fecha=date(2026, 12, 15), moneda=moneda
    )
    return presupuesto, composiciones


RECETA = Receta(
    id=1,
    producto="01",
    componentes=(
        Componente("AGR-12", D("0.95"), "t", "propio"),
        Componente("CA-30", D("0.05"), "t", "comprado"),
    ),
    fuente="Dosificación ficticia",
    vigente_desde=date(2026, 1, 1),
)
#: 0,95 × 5 + 0,05 × 600 + 12 de planta = 4,75 + 30 + 12 = 46,75 (el precio de la carpeta).
COMPONENTES = {"AGR-12": D(5), "CA-30": D(600)}


def _historia_variable():
    """Variaciones escritas a mano (36), distintas entre series para que el remuestreo importe."""
    ppi = [D(x) for x in ("1.03", "0.97", "1.05", "1.00", "0.98", "1.08")] * 6
    gasoil = [D(x) for x in ("1.00", "1.00", "1.10", "1.00", "1.00", "0.95")] * 6
    tasa = [D(x) for x in ("1.02", "1.06", "1.01", "1.12", "1.00", "1.04")] * 6
    return {
        PPI: _con_variaciones(ppi),
        GASOIL: _con_variaciones(gasoil, inicial=D("0.5")),
        SERIE_TASA: _con_variaciones(tasa, inicial=D(40)),
    }
