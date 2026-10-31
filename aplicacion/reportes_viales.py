"""Reportes viales, de riesgo y de mejora en Excel (plan vial, Tarea 21).

Seis reportes, cada uno `-> bytes` (un .xlsx) con una **hoja de portada** que dice, hoja por hoja,
de dónde sale cada cifra:

- `computos_por_tramo`: los tramos y las cantidades que derivan (cada una con su regla y su origen).
- `apu_con_origen`: cada línea de cada APU con la fuente de su precio y, si viene de un cálculo de
  producción, su n.º; y la conciliación CV1 a CV3 con `calculos_usados` armado desde esa fuente
  (`numero_de_calculo`), para que CV3 diga el cálculo usado y no «ningún cálculo publicado
  conocido» (árbitro de la Tarea 10).
- `costo_de_produccion`: los cálculos de un período con sus costos, lo producido y el costo por
  tonelada, y si se publicaron.
- `informe_de_riesgo`: P50, P80, reserva, contribución por insumo, supuestos y, si se pide, la
  comprobación hacia atrás.
- `informe_de_mejora`: los dos errores y la mejora en puntos.
- `resumen_con_iva`: subtotal, IVA y total del presupuesto (el IVA va sobre el total, no en el APU).

Las funciones puras reciben objetos de dominio ya cargados; las `*_de_la_version` y
`costo_de_produccion_del_periodo` los cargan de las bases (solo leen). Formato numérico: el patrón
de `hoja_exportar` (`#,##0.00`), que Excel muestra con coma decimal y punto de miles en un equipo
es-VE; las cantidades y las cifras exactas de la proyección llevan hasta cuatro decimales. Todo
texto pasa por `sanear_para_xlsx` (un carácter que un .xlsx no admite se cambia por U+FFFD).
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping, Sequence
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from io import BytesIO
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Font
from sqlalchemy.orm import Session

from adapters.vial.derivacion import derivar_tramos
from adapters.vial.modelo import Tramo
from aplicacion import vial
from aplicacion.conciliacion import conciliar, costos_propios_publicados, numero_de_calculo
from aplicacion.costo_propio import (
    CalculoGuardado,
    Publicacion,
    calculos_registrados,
    descripcion_de_costo_propio,
)
from aplicacion.hoja import FilaPrecio, precios_de_version
from aplicacion.hoja_exportar import sanear_para_xlsx
from aplicacion.impuestos import ALICUOTA_IVA, con_iva
from aplicacion.proyectos import resolver_proyecto
from aplicacion.riesgo.mejora import Mejora
from aplicacion.riesgo.obra import ComprobacionDeLaObra, ProyeccionDeLaObra
from aplicacion.vial import CantidadVial, RastroDeGuardado
from core import models
from core.budget import cargar_presupuesto, composiciones_de_presupuesto
from core.catalog import Catalogo
from core.contracts.apu import ComposicionAPU, ParametrosCosto
from core.contracts.presupuesto import Presupuesto

__all__ = [
    "FORMATO_CANTIDAD",
    "FORMATO_DINERO",
    "SinCalculosDelPeriodo",
    "apu_con_origen",
    "apu_de_la_version",
    "computos_de_la_version",
    "computos_por_tramo",
    "costo_de_produccion",
    "costo_de_produccion_del_periodo",
    "informe_de_mejora",
    "informe_de_riesgo",
    "nombre_de_reporte",
    "resumen_con_iva",
    "resumen_de_la_version",
]

FORMATO_DINERO = "#,##0.00"
FORMATO_CANTIDAD = "#,##0.00##"
FORMATO_FECHA = "DD/MM/YYYY"
FORMATO_FECHA_HORA = "DD/MM/YYYY HH:MM"
_CENTESIMA = Decimal("0.01")
_NO_SEGURO = re.compile(r"[^A-Za-z0-9._-]+")
_ANCHO_MAXIMO = 70
_SIN_ORIGEN = "sin origen registrado"
_SIN_FUENTE = "sin fuente registrada"

#: Una columna: su título y su formato numérico (`None`: el de la celda tal como viene).
Columna = tuple[str, str | None]
#: Un dato suelto: rótulo, valor y formato.
Dato = tuple[str, Any, str | None]


class SinCalculosDelPeriodo(ValueError):  # noqa: N818
    """No hay ningún cálculo de producción en ese período: la API lo responde 404."""


class SinTramos(ValueError):  # noqa: N818
    """La versión no tiene tramos guardados: no hay cómputos que reportar."""


def nombre_de_reporte(tipo: str, *partes: str) -> str:
    """`{tipo}_{partes}.xlsx` con cada parte ya segura para un `Content-Disposition`."""
    seguras = [_NO_SEGURO.sub("_", p[:40]).strip("_") for p in partes]
    return "_".join([tipo, *[s for s in seguras if s]]) + ".xlsx"


# --- El libro: portada y hojas --------------------------------------------------------------------


def _celda(valor: Any) -> Any:
    return sanear_para_xlsx(valor) if isinstance(valor, str) else valor


def _formato_de(valor: Any, formato: str | None) -> str | None:
    if formato is not None:
        return formato
    if isinstance(valor, datetime):
        return FORMATO_FECHA_HORA
    if isinstance(valor, date):
        return FORMATO_FECHA
    return None


class _Libro:
    """Un libro con su portada. `hoja` añade una hoja de datos y su fila en la portada."""

    def __init__(self, titulo: str, contexto: str) -> None:
        self._libro = Workbook()
        self._portada = self._libro.active
        self._portada.title = "Portada"
        self._portada.append([_celda(titulo)])
        self._portada.append([_celda(contexto)])
        self._portada.append([])
        self._portada.append(["Hoja", "Qué contiene", "De dónde sale cada cifra"])
        self._negrita(1)
        self._negrita(4)

    def _negrita(self, fila: int, hoja=None) -> None:
        for celda in (hoja or self._portada)[fila]:
            celda.font = Font(bold=True)

    def hoja(
        self,
        nombre: str,
        que: str,
        fuente: str,
        *,
        datos: Sequence[Dato] = (),
        columnas: Sequence[Columna] = (),
        filas: Iterable[Sequence[Any]] = (),
    ) -> None:
        """Una hoja: primero los `datos` (rótulo y valor), una fila en blanco si además hay tabla,
        y la tabla de `columnas` y `filas`."""
        hoja = self._libro.create_sheet(nombre)
        for rotulo, valor, formato in datos:
            hoja.append([_celda(rotulo), _celda(valor)])
            self._formatear(hoja[hoja.max_row][1], valor, formato)
            hoja[hoja.max_row][0].font = Font(bold=True)
        if columnas:
            if datos:
                hoja.append([])
            hoja.append([titulo for titulo, _ in columnas])
            self._negrita(hoja.max_row, hoja)
            for fila in filas:
                hoja.append([_celda(v) for v in fila])
                for celda, valor, (_, formato) in zip(
                    hoja[hoja.max_row], fila, columnas, strict=True
                ):
                    self._formatear(celda, valor, formato)
        self._ajustar(hoja)
        self._portada.append([_celda(nombre), _celda(que), _celda(fuente)])

    @staticmethod
    def _formatear(celda, valor: Any, formato: str | None) -> None:
        formato = _formato_de(valor, formato)
        if formato is not None and valor is not None and not isinstance(valor, str):
            celda.number_format = formato

    @staticmethod
    def _ajustar(hoja) -> None:
        for columna in hoja.columns:
            largo = max((len(str(c.value)) for c in columna if c.value is not None), default=8)
            hoja.column_dimensions[columna[0].column_letter].width = min(largo + 2, _ANCHO_MAXIMO)

    def bytes(self) -> bytes:
        self._ajustar(self._portada)
        salida = BytesIO()
        self._libro.save(salida)
        return salida.getvalue()


def _centimos(valor: Decimal) -> Decimal:
    return valor.quantize(_CENTESIMA, rounding=ROUND_HALF_UP)


# --- Cómputos por tramo ---------------------------------------------------------------------------


def computos_por_tramo(
    tramos: Sequence[Tramo],
    cantidades: Sequence[CantidadVial],
    *,
    proyecto: str,
    version: str,
    guardado: RastroDeGuardado | None = None,
) -> bytes:
    """Los tramos de la versión y las cantidades de obra que derivan de ellos."""
    libro = _Libro("Cómputos por tramo", f"Obra: {proyecto} · Versión: {version}")
    quien = (
        ""
        if guardado is None
        else f" Guardados por {guardado.usuario} el {guardado.fecha_hora:%d/%m/%Y %H:%M}; "
        f"fuente: {guardado.fuente or 'sin fuente'}."
    )
    libro.hoja(
        "Tramos",
        "Cada tramo con sus progresivas, su ancho y sus capas.",
        f"Los tramos guardados de la versión.{quien} La longitud es la diferencia de progresivas "
        "por 1.000.",
        columnas=[
            ("Tramo", None),
            ("Desde (km)", FORMATO_CANTIDAD),
            ("Hasta (km)", FORMATO_CANTIDAD),
            ("Longitud (m)", FORMATO_CANTIDAD),
            ("Ancho (m)", FORMATO_CANTIDAD),
            ("Distancia a la planta (km)", FORMATO_CANTIDAD),
            ("Capas", None),
        ],
        filas=[
            (
                t.id,
                t.progresiva_ini_km,
                t.progresiva_fin_km,
                (t.progresiva_fin_km - t.progresiva_ini_km) * 1000,
                t.ancho_m,
                t.distancia_planta_km,
                ", ".join(c.tipo for c in t.capas) or "ninguna",
            )
            for t in tramos
        ],
    )
    libro.hoja(
        "Cómputos por tramo",
        "Una fila por cantidad de obra: partida, unidad, cantidad, regla y origen.",
        "Derivadas de los tramos con `adapters.vial.derivar_tramos`; cada fila cita la regla que "
        "la produce y su origen (tramo y capa o línea).",
        columnas=[
            ("Tramo", None),
            ("Código", None),
            ("Descripción", None),
            ("Unidad", None),
            ("Cantidad", FORMATO_CANTIDAD),
            ("Regla", None),
            ("Origen", None),
        ],
        filas=[
            (c.tramo, c.codigo, c.descripcion, c.unidad, c.cantidad, c.regla, c.origen_id)
            for c in cantidades
        ],
    )
    totales: dict[str, list[Any]] = {}
    for c in cantidades:
        fila = totales.setdefault(c.codigo, [c.codigo, c.descripcion, c.unidad, Decimal(0)])
        fila[3] += c.cantidad
    libro.hoja(
        "Totales por partida",
        "La suma de las cantidades de todos los tramos por partida.",
        "Suma de la hoja «Cómputos por tramo»; es la cantidad con que la conciliación CV2 "
        "compara el presupuesto.",
        columnas=[
            ("Código", None),
            ("Descripción", None),
            ("Unidad", None),
            ("Cantidad total", FORMATO_CANTIDAD),
        ],
        filas=totales.values(),
    )
    return libro.bytes()


def computos_de_la_version(sesion: Session, proyecto: str, codigo: str) -> bytes:
    """`computos_por_tramo` con los tramos que valen para la versión (`SinTramos` si no tiene)."""
    version_id = vial.version_de(sesion, proyecto, codigo)
    tramos = vial.tramos_de_version(sesion, version_id)
    if not tramos:
        raise SinTramos(f"La versión {codigo} no tiene tramos guardados: cárguelos primero.")
    obra = resolver_proyecto(sesion, proyecto)
    return computos_por_tramo(
        tramos,
        vial.cantidades_de_tramos(tramos),
        proyecto=obra.nombre if obra else proyecto,
        version=codigo,
        guardado=vial.guardado_de_version(sesion, version_id),
    )


# --- APU con origen y conciliación ----------------------------------------------------------------


def _origen_del_precio(fila: FilaPrecio | None) -> str:
    if fila is None:
        return _SIN_ORIGEN
    return fila.fuente or _SIN_FUENTE


def _lineas_del_apu(
    codigo: str, apu: ComposicionAPU, moneda: str, precios: Mapping[str, FilaPrecio]
):
    lineas = (
        *(
            ("material", m.descripcion, m.unidad, m.cantidad, m.precio, m.total)
            for m in apu.materiales
        ),
        *(("equipo", e.descripcion, "", e.cantidad, e.precio, e.total) for e in apu.equipos),
        *(
            ("mano de obra", o.descripcion, "", o.cantidad, o.sueldo, o.total)
            for o in apu.mano_obra
        ),
    )
    for tipo, descripcion, unidad, cantidad, precio, total in lineas:
        fila = precios.get(descripcion)
        yield (
            codigo,
            tipo,
            descripcion,
            unidad,
            cantidad,
            precio,
            total,
            fila.moneda if fila else moneda,
            fila.lista if fila else "",
            _origen_del_precio(fila),
            numero_de_calculo(fila.fuente) if fila else None,
        )


def apu_con_origen(
    presupuesto: Presupuesto,
    composiciones: Mapping[str, ComposicionAPU],
    parametros: ParametrosCosto,
    precios: Sequence[FilaPrecio],
    *,
    items_viales: Sequence[Any],
    costos_propios: Mapping[str, CalculoGuardado],
    proyecto: str,
) -> bytes:
    """Las partidas del presupuesto, cada línea de su APU con la fuente de su precio y la
    conciliación CV1 a CV3. Un precio sin fila en `precios` dice «sin origen registrado»; el n.º
    del cálculo de producción sale de la fuente (`numero_de_calculo`) y alimenta a CV3."""
    por_descripcion: dict[str, FilaPrecio] = {}
    for fila in precios:
        por_descripcion.setdefault(fila.descripcion, fila)
    usados = {}
    for codigo in costos_propios:
        fila = por_descripcion.get(descripcion_de_costo_propio(codigo))
        numero = None if fila is None else numero_de_calculo(fila.fuente)
        if numero is not None:
            usados[codigo] = numero
    hallazgos = conciliar(
        presupuesto,
        composiciones,
        parametros,
        items_viales=items_viales,
        costos_propios=costos_propios,
        calculos_usados=usados,
    )
    libro = _Libro(
        "APU con origen",
        f"Obra: {proyecto} · Versión: {presupuesto.codigo} · Moneda: {presupuesto.moneda}",
    )
    libro.hoja(
        "Partidas",
        "Cada partida del presupuesto con su cantidad, su precio unitario y su total.",
        "El presupuesto de la versión, recalculado con el motor de costos desde la composición "
        "congelada de cada partida; la cantidad cita su origen.",
        columnas=[
            ("Código", None),
            ("Descripción", None),
            ("Unidad", None),
            ("Cantidad", FORMATO_CANTIDAD),
            ("Precio unitario", FORMATO_DINERO),
            ("Total", FORMATO_DINERO),
            ("Origen de la cantidad", None),
        ],
        filas=[
            (
                p.item.codigo_partida,
                p.item.descripcion,
                p.item.unidad,
                p.item.cantidad,
                p.resultado.precio_unitario,
                p.total,
                p.item.origen_id,
            )
            for p in presupuesto.partidas
        ],
    )
    libro.hoja(
        "APU con origen",
        "Cada línea de cada APU con el origen de su precio.",
        "La fuente es la de la lista de precios de la versión (`precios_de_version`), cotejada por "
        "la descripción del insumo; «Cálculo n.º» sale de la fuente «Producción, período …, "
        "cálculo n.º …» de un costo propio publicado. Una línea sin fila en la lista dice «sin "
        "origen registrado».",
        columnas=[
            ("Partida", None),
            ("Tipo de línea", None),
            ("Concepto", None),
            ("Unidad", None),
            ("Cantidad", FORMATO_CANTIDAD),
            ("Precio", FORMATO_DINERO),
            ("Total de la línea", FORMATO_DINERO),
            ("Moneda", None),
            ("Lista", None),
            ("Origen del precio", None),
            ("Cálculo n.º", None),
        ],
        filas=[
            linea
            for p in presupuesto.partidas
            for linea in _lineas_del_apu(
                p.item.codigo_partida,
                composiciones.get(p.item.codigo_partida, p.apu),
                presupuesto.moneda,
                por_descripcion,
            )
        ],
    )
    libro.hoja(
        "Conciliación",
        "Los hallazgos CV1 (precio contra APU), CV2 (cantidad contra tramos) y CV3 (costo propio).",
        "`aplicacion.conciliacion.conciliar`: CV1 recalcula el APU; CV2 suma las cantidades de los "
        "tramos; CV3 compara con el último cálculo publicado y nombra el cálculo del que viene el "
        "precio usado.",
        columnas=[
            ("Regla", None),
            ("Severidad", None),
            ("Qué dice", None),
            ("Observado", FORMATO_DINERO),
            ("Esperado", FORMATO_DINERO),
            ("Origen", None),
        ],
        filas=[
            (
                h.regla,
                h.severidad.name,
                h.descripcion,
                h.valor_observado,
                h.valor_esperado,
                ", ".join(h.origen_ids),
            )
            for h in hallazgos
        ]
        or [("—", "—", "Sin hallazgos de CV1 a CV3.", None, None, "")],
    )
    return libro.bytes()


def _version_cargada(sesion: Session, proyecto: str, codigo: str):
    version_id = vial.version_de(sesion, proyecto, codigo)
    modelo = sesion.get(models.Presupuesto, version_id)
    nombre = modelo.proyecto.nombre
    catalogo = Catalogo(sesion)
    parametros = ParametrosCosto(
        fcas=modelo.fcas,
        bono_alimentacion=modelo.bono_alimentacion,
        administracion=modelo.administracion,
        utilidad=modelo.utilidad,
    )
    return (
        version_id,
        nombre,
        cargar_presupuesto(sesion, nombre, codigo, catalogo),
        composiciones_de_presupuesto(sesion, nombre, codigo, catalogo),
        parametros,
    )


def apu_de_la_version(
    sesion_caso: Session, sesion_ins: Session, proyecto: str, codigo: str
) -> bytes:
    """`apu_con_origen` de una versión guardada: sus tramos (si tiene), los precios de su lista y
    los últimos cálculos de costo propio publicados de la instalación."""
    version_id, nombre, presupuesto, composiciones, parametros = _version_cargada(
        sesion_caso, proyecto, codigo
    )
    tramos = vial.tramos_de_version(sesion_caso, version_id)
    return apu_con_origen(
        presupuesto,
        composiciones,
        parametros,
        precios_de_version(sesion_caso, nombre, codigo),
        items_viales=derivar_tramos(tramos) if tramos else (),
        costos_propios=costos_propios_publicados(sesion_ins),
        proyecto=nombre,
    )


# --- Costo de producción --------------------------------------------------------------------------


def costo_de_produccion(
    calculos: Sequence[tuple[CalculoGuardado, Publicacion | None]], *, periodo: str
) -> bytes:
    """Los cálculos del `periodo` (el más reciente primero) con sus costos, lo producido y el costo
    por tonelada. `SinCalculosDelPeriodo` si no hay ninguno."""
    if not calculos:
        raise SinCalculosDelPeriodo(f"No hay cálculos de producción del período {periodo}.")
    libro = _Libro("Costo de producción", f"Período: {periodo}")
    datos = [(c, p, json.loads(c.instantanea)) for c, p in calculos]
    libro.hoja(
        "Cálculos",
        "Cada cálculo del período: quién y cuándo, los totales por centro y si se publicó.",
        "Los cálculos guardados en la instalación, cada uno verificado contra su huella (uno "
        "alterado no se lee); la publicación es la de `prod_publicacion`.",
        columnas=[
            ("Cálculo n.º", None),
            ("Período", None),
            ("Moneda", None),
            ("Registrado por", None),
            ("Registrado el", FORMATO_FECHA_HORA),
            ("Total de la cantera", FORMATO_DINERO),
            ("Total de la planta", FORMATO_DINERO),
            ("Planta por t", FORMATO_DINERO),
            ("Publicado", None),
            ("Lista n.º", None),
            ("Carpeta", None),
            ("Publicado por", None),
            ("Huella", None),
        ],
        filas=[
            (
                c.id,
                c.periodo,
                c.moneda,
                c.usuario,
                c.registrado,
                Decimal(r["resultado"]["total_cantera"]),
                Decimal(r["resultado"]["total_planta"]),
                None
                if r["resultado"]["planta_por_t"] is None
                else Decimal(r["resultado"]["planta_por_t"]),
                "No" if p is None else "Sí",
                None if p is None else p.lista_id,
                "" if p is None else p.caso,
                "" if p is None else p.usuario,
                c.huella[:16],
            )
            for c, p, r in datos
        ],
    )
    libro.hoja(
        "Costo por tonelada",
        "El costo por tonelada de cada agregado y mezcla, en la moneda del cálculo.",
        "El resultado del cálculo (`por_tonelada`): costos del período convertidos con la tasa BCV "
        "del día, repartidos entre lo producido; el tipo sale de si el producto es agregado.",
        columnas=[
            ("Cálculo n.º", None),
            ("Período", None),
            ("Producto", None),
            ("Tipo", None),
            ("Costo por t", FORMATO_DINERO),
            ("Moneda", None),
        ],
        filas=[
            (
                c.id,
                c.periodo,
                producto,
                "agregado" if producto in r["entradas"]["agregados"] else "mezcla",
                costo,
                c.moneda,
            )
            for c, _, r in datos
            for producto, costo in sorted(c.por_tonelada.items())
        ],
    )
    libro.hoja(
        "Costos del período",
        "Cada costo registrado que entró al cálculo, con su fuente y su conversión.",
        "Los costos registrados en `prod_costo` tal como los copió el cálculo: monto y moneda "
        "originales, fuente, y el monto convertido con la tasa BCV de su día (y su fuente).",
        columnas=[
            ("Cálculo n.º", None),
            ("Centro", None),
            ("Concepto", None),
            ("Monto", FORMATO_DINERO),
            ("Moneda", None),
            ("Fecha", FORMATO_FECHA),
            ("Convertido", FORMATO_DINERO),
            ("Fuente", None),
            ("Tasa BCV", FORMATO_DINERO),
            ("Fecha de la tasa", FORMATO_FECHA),
        ],
        filas=[
            (
                c.id,
                x["centro"],
                x["concepto"],
                Decimal(x["monto"]),
                x["moneda"],
                date.fromisoformat(x["fecha"]),
                Decimal(x["convertido"]),
                x["fuente"],
                None if x["tasa"] is None else Decimal(x["tasa"]["valor"]),
                None if x["tasa"] is None else date.fromisoformat(x["tasa"]["fecha"]),
            )
            for c, _, r in datos
            for x in r["entradas"]["costos"]
        ],
    )
    libro.hoja(
        "Producido",
        "Las toneladas producidas en el período, por producto.",
        "Las salidas de producción del período (`entradas.producido` del cálculo).",
        columnas=[("Cálculo n.º", None), ("Producto", None), ("Toneladas", FORMATO_CANTIDAD)],
        filas=[
            (c.id, producto, Decimal(toneladas))
            for c, _, r in datos
            for producto, toneladas in sorted(r["entradas"]["producido"].items())
        ],
    )
    return libro.bytes()


def costo_de_produccion_del_periodo(sesion_ins: Session, periodo: str) -> bytes:
    """`costo_de_produccion` con los cálculos registrados del `periodo` (`AAAA-MM`)."""
    return costo_de_produccion(calculos_registrados(sesion_ins, periodo), periodo=periodo)


# --- Riesgo ---------------------------------------------------------------------------------------

_ORIGEN_DEL_INICIO = {"linea_base": "línea base de la versión", "declarado": "declarado"}


def informe_de_riesgo(
    proyeccion: ProyeccionDeLaObra,
    comprobacion: ComprobacionDeLaObra | None = None,
    *,
    mapa: Mapping[str, str],
) -> bytes:
    """El percentil 50 y 80 de la obra, la reserva, la contribución por insumo, los supuestos y el
    mapa de series; con `comprobacion`, también la cobertura hacia atrás."""
    p, r = proyeccion.proyeccion, proyeccion
    libro = _Libro("Riesgo de la obra", f"Obra: {r.proyecto} · Versión: {r.version}")
    libro.hoja(
        "Proyección",
        "El total base, los percentiles 50 y 80 y la reserva (P80 menos el total base).",
        "Remuestreo de meses históricos completos de las series del mapa sobre el presupuesto "
        "recalculado (`aplicacion.riesgo.proyeccion.proyectar`); la IA no calcula. Cifras exactas.",
        datos=[
            ("Obra", r.proyecto, None),
            ("Versión", r.version, None),
            ("Moneda", r.moneda, None),
            ("Total base", p.total_base, FORMATO_CANTIDAD),
            ("P50", p.percentiles[50], FORMATO_CANTIDAD),
            ("P80", p.percentiles[80], FORMATO_CANTIDAD),
            ("Reserva (P80 − total base)", p.reserva, FORMATO_CANTIDAD),
            ("Inicio de la proyección", r.inicio, None),
            ("Origen del inicio", _ORIGEN_DEL_INICIO.get(r.inicio_de, r.inicio_de), None),
            ("Meses del plazo", r.parametros.meses, None),
            ("Trayectorias", r.parametros.trayectorias, None),
            ("Semilla", p.semilla, None),
            ("Meses de historia usados", p.meses_usados, None),
        ],
    )
    libro.hoja(
        "Contribución",
        "Cuánto aporta cada insumo a la proyección, de mayor a menor.",
        "La contribución por insumo de la misma proyección, en la moneda del presupuesto.",
        columnas=[("Insumo", None), ("Monto", FORMATO_CANTIDAD)],
        filas=list(p.contribucion),
    )
    libro.hoja(
        "Supuestos",
        "Los supuestos declarados de la proyección.",
        "Los supuestos que `proyectar` y la lectura de la obra declaran, en el orden en que "
        "salieron.",
        columnas=[("N.º", None), ("Supuesto", None)],
        filas=[(i, s) for i, s in enumerate(p.supuestos, 1)]
        or [(0, "La proyección no declaró supuestos.")],
    )
    libro.hoja(
        "Mapa de series",
        "Qué serie de precios sigue cada insumo.",
        "El mapa que declaró quien pidió el informe; un insumo sin serie queda en su precio base.",
        columnas=[("Insumo o componente", None), ("Serie", None)],
        filas=sorted(mapa.items()) or [("(ninguno)", "ningún insumo sigue una serie")],
    )
    libro.hoja(
        "Mezclas propias",
        "De qué cálculo publicado sale la receta de cada mezcla propia.",
        "El último cálculo publicado de la instalación para cada mezcla propia que usa el "
        "presupuesto (`mezclas_publicadas`).",
        columnas=[("Insumo de la mezcla propia", None), ("Cálculo n.º", None)],
        filas=sorted(r.mezclas.items()) or [("(ninguna)", None)],
    )
    if comprobacion is not None:
        _comprobacion(libro, comprobacion)
    return libro.bytes()


def _comprobacion(libro: _Libro, c: ComprobacionDeLaObra) -> None:
    cortes = c.comprobacion.cortes
    libro.hoja(
        "Comprobación",
        "Si lo real cayó bajo el P80 en cada corte móvil de la historia.",
        "`aplicacion.riesgo.comprobacion.comprobar_hacia_atras`: en cada corte se proyectó con "
        "la historia anterior y se comparó con lo que pasó; cobertura = cortes dentro ÷ cortes.",
        datos=[
            ("Cobertura (%)", _centimos(c.comprobacion.cobertura * 100), FORMATO_DINERO),
            ("Cortes dentro del P80", sum(1 for x in cortes if x.dentro), None),
            ("Cortes", c.comprobacion.n_cortes, None),
            ("Trayectorias por corte", c.parametros.trayectorias, None),
        ],
        columnas=[
            ("Corte", FORMATO_FECHA),
            ("P50", FORMATO_CANTIDAD),
            ("P80", FORMATO_CANTIDAD),
            ("Real", FORMATO_CANTIDAD),
            ("Dentro del P80", None),
        ],
        filas=[(x.corte, x.p50, x.p80, x.real, "Sí" if x.dentro else "No") for x in cortes],
    )


# --- Mejora ---------------------------------------------------------------------------------------


def informe_de_mejora(
    mejora: Mejora,
    *,
    costo_final_real: Decimal,
    presupuesto_original: Decimal,
    estimacion_silice: Decimal,
) -> bytes:
    """Los dos errores contra el costo final real y la mejora en puntos porcentuales (negativa si
    Sílice acertó menos: no se esconde)."""
    if mejora.mejora_pp > 0:
        conclusion = "Sílice acertó más que el presupuesto original."
    elif mejora.mejora_pp < 0:
        conclusion = "Sílice acertó menos que el presupuesto original."
    else:
        conclusion = "Sílice y el presupuesto original erraron lo mismo."
    libro = _Libro("Mejora de la estimación", "Costo final real contra dos estimaciones")
    libro.hoja(
        "Mejora",
        "El error de cada estimación y cuánto mejoró (o empeoró) la de Sílice.",
        "`aplicacion.riesgo.mejora.mejora_de_estimacion`: error = |estimado − real| ÷ real × 100 "
        "con dos decimales; mejora = error original − error de Sílice, ya redondeados. Las tres "
        "cifras las escribió quien pidió el informe y deben estar en la misma moneda y a la misma "
        "fecha de precios; el reporte no lo comprueba.",
        datos=[
            ("Costo final real", costo_final_real, FORMATO_DINERO),
            ("Presupuesto original", presupuesto_original, FORMATO_DINERO),
            ("Estimación de Sílice", estimacion_silice, FORMATO_DINERO),
            ("Error del presupuesto original (%)", mejora.error_original_pct, FORMATO_DINERO),
            ("Error de la estimación de Sílice (%)", mejora.error_silice_pct, FORMATO_DINERO),
            ("Mejora (puntos porcentuales)", mejora.mejora_pp, FORMATO_DINERO),
            ("Conclusión", conclusion, None),
        ],
    )
    return libro.bytes()


# --- Resumen con IVA ------------------------------------------------------------------------------


def resumen_con_iva(presupuesto: Presupuesto, *, proyecto: str, version: str) -> bytes:
    """El subtotal del presupuesto, el IVA y el total con IVA (sobre el total, nunca en el APU)."""
    alicuota = Decimal(str(ALICUOTA_IVA.valor))
    resumen = con_iva(presupuesto.total, alicuota)
    por_ciento = format((alicuota * 100).normalize(), "f")
    libro = _Libro("Resumen con IVA", f"Obra: {proyecto} · Versión: {version}")
    libro.hoja(
        "Resumen",
        "El subtotal, el IVA y el total con IVA.",
        f"`aplicacion.impuestos.con_iva` sobre el total del presupuesto recalculado; alícuota: "
        f"{ALICUOTA_IVA.fuente}. Montos a dos decimales; el total suma las cifras ya redondeadas.",
        datos=[
            ("Obra", proyecto, None),
            ("Versión", version, None),
            ("Moneda", presupuesto.moneda, None),
            ("Subtotal sin IVA", resumen.subtotal, FORMATO_DINERO),
            (f"IVA ({por_ciento} %)", resumen.iva, FORMATO_DINERO),
            ("Total con IVA", resumen.total, FORMATO_DINERO),
        ],
    )
    libro.hoja(
        "Partidas",
        "Las partidas que suman el subtotal.",
        "El presupuesto de la versión: cantidad × precio unitario del APU, sin IVA.",
        columnas=[
            ("Código", None),
            ("Descripción", None),
            ("Unidad", None),
            ("Cantidad", FORMATO_CANTIDAD),
            ("Precio unitario", FORMATO_DINERO),
            ("Total", FORMATO_DINERO),
        ],
        filas=[
            (
                p.item.codigo_partida,
                p.item.descripcion,
                p.item.unidad,
                p.item.cantidad,
                p.resultado.precio_unitario,
                p.total,
            )
            for p in presupuesto.partidas
        ],
    )
    return libro.bytes()


def resumen_de_la_version(sesion: Session, proyecto: str, codigo: str) -> bytes:
    """`resumen_con_iva` del presupuesto guardado de la versión."""
    _, nombre, presupuesto, _, _ = _version_cargada(sesion, proyecto, codigo)
    return resumen_con_iva(presupuesto, proyecto=nombre, version=codigo)
