"""Análisis auditado del caso TI-001: laptops HP, cableado Cat 6, EMT y servidor en rack.

Todo el cálculo lo hace el sistema (adaptador telecom -> motor -> `elaborar` -> auditoría de las
siete reglas); los datos del caso viven una sola vez en `tests/fixtures/caso_ti001.py`. Este módulo
agrega lo que el informe necesita encima de eso:

- agrupación de los renglones por partida;
- recálculo independiente del precio unitario, con la fórmula de NORMAS.md §4 escrita de nuevo;
- pruebas de control: se siembra un error conocido y se comprueba qué regla lo detecta;
- sensibilidad del total a los supuestos que más pesan;
- punto de equilibrio del contrato, ubicado en la curva de inversión.

Uso::

    uv run python scripts/analisis_ti001.py     # resumen en consola

El PDF lo genera `scripts/informe_ti001.py` (extra `informes`).
"""

from __future__ import annotations

import sys
from collections import OrderedDict
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

# Ejecutado como `python scripts/...`, sys.path[0] es scripts/ (igual que en scripts/seed.py).
RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from core.budget import ResultadoElaboracion  # noqa: E402
from core.budget.curva import con_curva  # noqa: E402
from core.contracts import (  # noqa: E402
    ComposicionAPU,
    LineaEquipo,
    LineaManoObra,
    ModalidadManoObra,
    ParametrosCosto,
    Presupuesto,
    PuntoCurva,
    Severidad,
)
from core.costing import calcular_apu  # noqa: E402
from core.verification import auditar  # noqa: E402
from core.verification.informe import DECIMALES_PRESENTACION  # noqa: E402
from core.verification.texto import formatear_decimal  # noqa: E402
from tests.fixtures import caso_ti001 as caso  # noqa: E402

CERO = Decimal(0)
UNO = Decimal(1)
CIEN = Decimal(100)


def elaboracion() -> ResultadoElaboracion:
    return caso.elaborar_caso()


def por_partida(presupuesto: Presupuesto) -> OrderedDict[str, dict]:
    """Renglones agrupados por código: cantidad total, total, composición, resultado e ítems."""
    grupos: OrderedDict[str, dict] = OrderedDict()
    for partida in presupuesto.partidas:
        grupo = grupos.setdefault(
            partida.item.codigo_partida,
            {
                "apu": partida.apu,
                "resultado": partida.resultado,
                "cantidad": CERO,
                "total": CERO,
                "items": [],
            },
        )
        grupo["cantidad"] += partida.item.cantidad
        grupo["total"] += partida.total
        grupo["items"].append(partida.item)
    return grupos


# ---------------------------------------------------------------------------------------------
# Recálculo independiente
# ---------------------------------------------------------------------------------------------


def recalculo_manual(
    apu: ComposicionAPU, parametros: ParametrosCosto, bono_por_linea=None
) -> dict[str, Decimal]:
    """La fórmula de NORMAS.md §4 escrita línea por línea, sin llamar al motor.

    `bono_por_linea(linea) -> Decimal` reemplaza el bono único de `parametros` por uno propio de
    cada línea (lo usa la sensibilidad del bono exacto por oficio).
    """
    materiales = sum((linea.cantidad * linea.precio for linea in apu.materiales), CERO)
    equipos = (
        sum(
            (linea.cantidad * linea.precio * linea.depreciacion for linea in apu.equipos),
            CERO,
        )
        / apu.rendimiento
    )
    jornales = CERO
    bono = CERO
    destajo = CERO
    for linea in apu.mano_obra:
        if linea.modalidad is ModalidadManoObra.DESTAJO:
            destajo += linea.cantidad * linea.sueldo
            continue
        jornales += linea.cantidad * linea.sueldo * (UNO + parametros.fcas)
        propio = parametros.bono_alimentacion if bono_por_linea is None else bono_por_linea(linea)
        bono += linea.cantidad * propio
    mano_obra = (jornales + bono) / apu.rendimiento + destajo
    costo_directo = materiales + equipos + mano_obra
    con_administracion = costo_directo * (UNO + parametros.administracion)
    return {
        "materiales": materiales,
        "equipos": equipos,
        "mano_obra": mano_obra,
        "cd": costo_directo,
        "adm": con_administracion,
        "pu": con_administracion * (UNO + parametros.utilidad),
    }


def bono_exacto(linea: LineaManoObra) -> Decimal:
    """El bono MaPreX del oficio de la línea (su descripción termina en `[Ref]`)."""
    for insumo in caso.INSUMOS.values():
        if insumo.tipo == "mano_obra" and linea.descripcion == insumo.etiqueta:
            return insumo.bono
    raise KeyError(linea.descripcion)


def verificaciones_motor(presupuesto: Presupuesto) -> list[tuple[str, Decimal, Decimal, Decimal]]:
    """`(codigo, PU del motor, PU recalculado, diferencia)` por partida."""
    filas = []
    for codigo, grupo in por_partida(presupuesto).items():
        manual = recalculo_manual(grupo["apu"], caso.PARAMETROS)["pu"]
        motor = calcular_apu(grupo["apu"], caso.PARAMETROS).precio_unitario
        filas.append((codigo, motor, manual, motor - manual))
    return filas


# ---------------------------------------------------------------------------------------------
# Pruebas de control: errores sembrados
# ---------------------------------------------------------------------------------------------


def _reglas_graves(informe) -> list[str]:
    return sorted({h.regla for h in informe.hallazgos if h.severidad >= Severidad.ERROR})


def _control(nombre: str, esperado: list[str], informe) -> dict:
    detectadas = _reglas_graves(informe)
    ejemplo = next(
        (
            h.descripcion
            for h in informe.hallazgos
            if h.regla in esperado and h.severidad >= Severidad.ERROR
        ),
        "",
    )
    return {
        "nombre": nombre,
        "esperado": esperado,
        "detectadas": detectadas,
        "ok": all(regla in detectadas for regla in esperado),
        "ejemplo": ejemplo,
    }


def pruebas_de_control() -> list[dict]:
    """Siete errores conocidos, cada uno en una copia del caso, y la regla que debería verlo.

    El cuarto (1/2 pulg frente a 1 pulg) se escapaba hasta SF‑E5: R4 comparaba por subcadena y el
    APU cita la «Dobladora de tubo EMT 1/2 a 1 1/2 pulg» (A‑2, bitácora del caso). Desde SF‑E5 R4
    compara especificaciones normalizadas y lo detecta: siete de siete.
    """
    base = caso.items()

    def mutar(origen_id: str, **cambios):
        return [replace(i, **cambios) if i.origen_id == origen_id else i for i in base]

    def informe(computo=None, composiciones=None):
        return caso.elaborar_caso(composiciones=composiciones, computo=computo).informe

    tramo = next(i for i in base if i.origen_id == "EMT-TA")
    medio = {**tramo.especificaciones, "diametro": "1/2 pulg"}
    tres = {**tramo.especificaciones, "diametro": "3 pulg"}

    composiciones = dict(caso.COMPOSICIONES)
    utp = composiciones["TI-UTP"]
    composiciones["TI-UTP"] = replace(
        utp,
        equipos=tuple(
            LineaEquipo(e.descripcion, e.cantidad, e.precio, Decimal("0.5"))
            if e.descripcion.startswith("Herramientas menores")
            else e
            for e in utp.equipos
        ),
    )

    presupuesto = caso.elaborar_caso().presupuesto
    curva: list[PuntoCurva] = []
    acumulado = CERO
    for indice, punto in enumerate(presupuesto.curva):
        monto = punto.monto - (Decimal("150.00") if indice == 2 else CERO)
        acumulado += monto
        curva.append(PuntoCurva(punto.periodo, monto, acumulado))

    return [
        _control(
            "Se computan 12 salidas de datos en vez de 14",
            ["R5"],
            informe(mutar("PTO-LOTE", cantidad=Decimal(12))),
        ),
        _control(
            "Tramo UTP-B3 transcrito como 30 m (la regla da 37,4 m)",
            ["R1"],
            informe(mutar("UTP-B3", cantidad=Decimal(30))),
        ),
        _control(
            "Tramo UTP-A1 computado en piezas y costeado por metro",
            ["R3"],
            informe(mutar("UTP-A1", unidad="pieza")),
        ),
        _control(
            "Troncal EMT-TA especificada en 1/2 pulg y costeada en 1 pulg",
            ["R4"],
            informe(mutar("EMT-TA", especificaciones=medio)),
        ),
        _control(
            "Troncal EMT-TA especificada en 3 pulg y costeada en 1 pulg",
            ["R4"],
            informe(mutar("EMT-TA", especificaciones=tres)),
        ),
        _control(
            "Herramientas menores con factor 0,5 en TI-UTP y 1,0 en los demas",
            ["R6"],
            informe(composiciones=composiciones),
        ),
        _control(
            "Curva transcrita con 150 USD de menos en el Dia 3",
            ["R2", "R7"],
            auditar(con_curva(presupuesto, curva)),
        ),
    ]


# ---------------------------------------------------------------------------------------------
# Sensibilidad
# ---------------------------------------------------------------------------------------------


def _total(parametros: ParametrosCosto = caso.PARAMETROS, composiciones=None) -> Decimal:
    return caso.elaborar_caso(parametros, composiciones).presupuesto.total


def _composiciones_laptop(factor: Decimal) -> dict[str, ComposicionAPU]:
    composiciones = dict(caso.COMPOSICIONES)
    laptop = composiciones["TI-LAP"]
    composiciones["TI-LAP"] = replace(
        laptop,
        materiales=tuple(
            replace(m, precio=m.precio * factor) if m.descripcion.startswith("Laptop") else m
            for m in laptop.materiales
        ),
    )
    return composiciones


def sensibilidad(presupuesto: Presupuesto) -> list[tuple[str, Decimal, Decimal, Decimal]]:
    """`(escenario, total, variación, variación %)` frente al caso base."""
    par = caso.PARAMETROS
    bono = sum(
        (
            p.item.cantidad * recalculo_manual(p.apu, par, bono_exacto)["pu"]
            for p in presupuesto.partidas
        ),
        CERO,
    )
    sumado = sum(
        (
            p.item.cantidad * p.resultado.costo_directo * (UNO + par.administracion + par.utilidad)
            for p in presupuesto.partidas
        ),
        CERO,
    )
    escenarios = [
        ("Caso base (parametros del informe)", presupuesto.total),
        (
            "Laptops 30 % mas baratas (cotizacion HP en vez de proxy MaPreX)",
            _total(composiciones=_composiciones_laptop(Decimal("0.70"))),
        ),
        ("FCAS 300 % en vez de 600 %", _total(replace(par, fcas=Decimal("3.00")))),
        ("Bono exacto por oficio (MaPreX) en vez de bono unico", bono),
        ("Error tipico: sumar adm. + util. (1,25) en vez de encadenar (1,265)", sumado),
    ]
    base = presupuesto.total
    return [(n, t, t - base, (t - base) / base * CIEN) for n, t in escenarios]


# ---------------------------------------------------------------------------------------------
# Punto de equilibrio
# ---------------------------------------------------------------------------------------------


def punto_equilibrio(presupuesto: Presupuesto) -> dict:
    """Costo variable = costo directo; costo fijo = administración (gastos generales).

    Margen de contribución m = (V - CV) / V; PE = CF / m. Se ubica en la curva: el primer período
    cuya valuación acumulada alcanza el PE, y la fracción de ese período en que se alcanza.
    """
    cv = sum((p.item.cantidad * p.resultado.costo_directo for p in presupuesto.partidas), CERO)
    cf = cv * caso.PARAMETROS.administracion
    v = presupuesto.total
    margen = (v - cv) / v
    pe = cf / margen
    periodo = None
    fraccion = None
    anterior = CERO
    for punto in presupuesto.curva:
        if punto.acumulado >= pe:
            periodo = punto.periodo
            fraccion = (pe - anterior) / punto.monto if punto.monto else CERO
            break
        anterior = punto.acumulado
    return {
        "V": v,
        "CV": cv,
        "CF": cf,
        "U": v - cv - cf,
        "m": margen,
        "PE": pe,
        "PE_pct": pe / v * CIEN,
        "periodo": periodo,
        "fraccion_periodo": fraccion,
    }


def _usd(valor: Decimal) -> str:
    return formatear_decimal(valor, DECIMALES_PRESENTACION)


def main() -> int:
    resultado = elaboracion()
    presupuesto = resultado.presupuesto
    print(f"Presupuesto {presupuesto.codigo}: {_usd(presupuesto.total)} USD")
    for codigo, grupo in por_partida(presupuesto).items():
        pu = _usd(grupo["resultado"].precio_unitario)
        cantidad = formatear_decimal(grupo["cantidad"])
        print(f"  {codigo:9} {pu:>10} x {cantidad:>7} = {_usd(grupo['total'])}")
    veredicto = "CUMPLE" if resultado.informe.cumple else "NO CUMPLE"
    print(f"Auditoria: {veredicto} ({len(resultado.informe.hallazgos)} hallazgos)")
    equilibrio = punto_equilibrio(presupuesto)
    print(
        f"Punto de equilibrio: {_usd(equilibrio['PE'])} USD "
        f"({_usd(equilibrio['PE_pct'])} %), {equilibrio['periodo']}"
    )
    for control in pruebas_de_control():
        estado = "detectado" if control["ok"] else "NO detectado"
        print(f"  control: {control['nombre']}: {estado}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
