"""APU regenerados con forma uniforme (spec 1.5, F-D4 y F-D5).

Causa raíz C1/C3: cada APU de la empresa tenía su propia forma (de 41 a 81 filas) y las hojas que
los leían suponían una sola. En la devolución todos los APU del libro tienen **la misma maqueta**:
cada sección lleva el mismo número de filas de línea (el máximo de esa sección en el libro, mínimo
4), así cada rótulo cae en la misma celda en todos los APU. Además cada APU publica nombres
definidos (`APU_01_PU`, `APU_X_REND`…) y el resto del libro lee por nombre, nunca por posición
dentro de un texto.

El aspecto se toma del propio libro: los estilos de cada clase de fila (título, sección, encabezado,
línea, subtotal, resumen, nota), los anchos de columna y la impresión salen del primer APU unido a
una partida. Si falta alguna clase (por ejemplo, un libro sin bloque de transporte) se usa la más
cercana o la paleta del perfil.

Valores guardados: los componentes son los de Silice (`ApuCalculado`, sembrados en sus celdas); las
líneas valen cantidad × precio de INSUMOS (las calcula `calculos`).
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from adapters.hoja_empresa.escritor.estilos import Estilo, LectorEstilos
from adapters.hoja_empresa.escritor.formulas import cita, dir_celda, letra
from adapters.hoja_empresa.escritor.hoja import NADA, HojaSalida
from adapters.hoja_empresa.modelo import (
    ApuCalculado,
    ApuLeido,
    LibroLeido,
    ParametrosLibro,
    Rotulo,
    TipoInsumo,
)
from adapters.hoja_empresa.perfil import Perfil, coincide, normalizar
from adapters.hoja_empresa.plantilla import (
    divisor_equipos,
    es_destajo,
    factor_linea,
    filas_base_mo,
)

__all__ = [
    "PUBLICADOS",
    "Kit",
    "Maqueta",
    "extraer_kit",
    "generar_apu",
    "mapa_filas",
    "maqueta_del_libro",
]

#: Rótulos que cada APU publica como nombre definido `<ident>_<RÓTULO>`.
PUBLICADOS = (
    Rotulo.MAT,
    Rotulo.MO,
    Rotulo.EQ,
    Rotulo.TR,
    Rotulo.CD,
    Rotulo.ADM,
    Rotulo.SUB,
    Rotulo.UTI,
    Rotulo.PU,
    Rotulo.REND,
    Rotulo.ESC,
)
_MINIMO = 4
_SECCION = {
    TipoInsumo.MATERIAL: "mat",
    TipoInsumo.MANO_OBRA: "mo",
    TipoInsumo.EQUIPO: "eq",
}
_LISTA = {TipoInsumo.MATERIAL: "LMAT", TipoInsumo.MANO_OBRA: "LMO", TipoInsumo.EQUIPO: "LEQ"}

TEXTOS = {
    "titulo": "ANÁLISIS DE PRECIO UNITARIO (APU)",
    "cab_cod": "Código de partida:",
    "cab_und": "Unidad:",
    "cab_mon": "Moneda:",
    "cab_norma": "Norma de referencia:",
    "cab_cli": "Cliente:",
    "cab_fecha": "Fecha:",
    "sec_mat": "1.  MATERIALES",
    "sec_mo": "2.  MANO DE OBRA  (cuadrilla por día)",
    "sec_eq": "3.  EQUIPOS Y HERRAMIENTAS  (costo por día)",
    "sec_tr": "4.  TRANSPORTE Y DISPOSICIÓN DE ESCOMBROS",
    "sec_res": "RESUMEN DE COSTOS",
    "sub_mat": "SUBTOTAL MATERIALES (USD/u)",
    "base": "Subtotal salarios base ($/día)",
    "rend": "FCAS × Rendimiento (u/día)",
    "costo": "Costo mano de obra ($/u) = Base × FCAS ÷ Rendimiento",
    "sub_mo": "SUBTOTAL MANO DE OBRA (USD/u)",
    "eq_dia": "Subtotal equipos ($/día)",
    "herr": "Herramientas menores (% de la mano de obra) ($/u)",
    "sub_eq": "SUBTOTAL EQUIPOS Y HERRAMIENTAS (USD/u) = Equipos/día ÷ Rend + Herr. menores",
    "esc": "Escombro a botar, esponjado (m³/u)",
    "flete": "Flete a vertedero ($/u) = FLETE × Escombro ÷ CAMION",
    "disp": "Derecho de disposición ($/u) = Escombro × VERT",
    "sub_tr": "SUBTOTAL TRANSPORTE Y DISPOSICIÓN (USD/u)",
    "mat_r": "Materiales (USD/u)",
    "mo_r": "Mano de obra (USD/u)",
    "eq_r": "Equipos y herramientas (USD/u)",
    "tr_r": "Transporte y disposición (USD/u)",
    "cd": "COSTO DIRECTO TOTAL (USD/u)",
    "adm": "Administración y gastos generales",
    "sub": "SUB-TOTAL (Costo Directo + Administración) (USD/u)",
    "uti": "Utilidad e imprevistos (sobre sub-total)",
    "pu": "PRECIO UNITARIO TOTAL (USD/u)",
}
_ENCABEZADOS = {
    "mat": (
        "Ítem",
        "Código",
        "Descripción",
        "Unidad",
        "Cantidad",
        "P.U. (USD)",
        "Subtotal (USD)",
        "CONSUMO/u",
    ),
    "mo": (
        "Ítem",
        "Código",
        "Descripción",
        "Unidad",
        "Cuadrilla",
        "Jornal/día (USD)",
        "Total/día (USD)",
        "CONSUMO/u",
    ),
    "eq": (
        "Ítem",
        "Código",
        "Descripción",
        "Unidad",
        "Cantidad",
        "Costo/día (USD)",
        "Total/día (USD)",
        "CONSUMO/u",
    ),
}
#: Clase de fila de la maqueta ↔ rótulo del perfil.
_CLASE_ROTULO = {
    "base": Rotulo.BASE_MO,
    "rend": Rotulo.REND,
    "eq_dia": Rotulo.EQ_DIA,
    "herr": Rotulo.HERR,
    "esc": Rotulo.ESC,
    "mat_r": Rotulo.MAT,
    "mo_r": Rotulo.MO,
    "eq_r": Rotulo.EQ,
    "tr_r": Rotulo.TR,
    "cd": Rotulo.CD,
    "adm": Rotulo.ADM,
    "sub": Rotulo.SUB,
    "uti": Rotulo.UTI,
    "pu": Rotulo.PU,
}
_ROTULO_CLASE = {v: k for k, v in _CLASE_ROTULO.items()}
#: Prefijos (normalizados) de las filas que no son rótulos del perfil.
_PREFIJOS = (
    ("sub_mat", "subtotal materiales"),
    ("sub_mo", "subtotal mano de obra"),
    ("sub_eq", "subtotal equipos y herramientas"),
    ("sub_tr", "subtotal transporte"),
    ("costo", "costo mano de obra"),
    ("flete", "flete a vertedero"),
    ("disp", "derecho de disposición"),
    ("sec_mat", "1."),
    ("sec_mo", "2."),
    ("sec_eq", "3."),
    ("sec_tr", "4."),
    ("sec_res", "resumen de costos"),
)
_RESPALDOS = {
    "sec_mo": "sec_mat",
    "sec_eq": "sec_mat",
    "sec_tr": "sec_mat",
    "sec_res": "sec_mat",
    "enc_mo": "enc_mat",
    "enc_eq": "enc_mat",
    "lin_mo": "lin_mat",
    "lin_eq": "lin_mo",
    "sub_mo": "sub_mat",
    "sub_eq": "sub_mat",
    "sub_tr": "sub_mat",
    "eq_dia": "base",
    "costo": "base",
    "herr": "costo",
    "flete": "herr",
    "disp": "flete",
    "esc": "flete",
    "mo_r": "mat_r",
    "eq_r": "mat_r",
    "tr_r": "mat_r",
    "cd": "mat_r",
    "adm": "mat_r",
    "sub": "cd",
    "uti": "adm",
    "pu": "sub_mat",
    "nota": "base",
}


@dataclass(frozen=True, slots=True)
class Maqueta:
    """Filas de la maqueta uniforme del libro (las mismas en todos sus APU)."""

    n_mat: int
    n_mo: int
    n_eq: int
    filas: Mapping[str, int] = field(default_factory=dict)

    @staticmethod
    def crear(n_mat: int, n_mo: int, n_eq: int) -> Maqueta:
        f: dict[str, int] = {"titulo": 1, "partida": 2, "cab1": 4, "cab2": 5, "cab3": 6}
        f["sec_mat"] = 8
        f["enc_mat"] = 9
        f["lin_mat"] = 10
        f["sub_mat"] = 10 + n_mat
        f["sec_mo"] = f["sub_mat"] + 2
        f["enc_mo"] = f["sec_mo"] + 1
        f["lin_mo"] = f["enc_mo"] + 1
        f["base"] = f["lin_mo"] + n_mo
        f["rend"] = f["base"] + 1
        f["costo"] = f["rend"] + 1
        f["sub_mo"] = f["costo"] + 1
        f["sec_eq"] = f["sub_mo"] + 2
        f["enc_eq"] = f["sec_eq"] + 1
        f["lin_eq"] = f["enc_eq"] + 1
        f["eq_dia"] = f["lin_eq"] + n_eq
        f["herr"] = f["eq_dia"] + 1
        f["sub_eq"] = f["herr"] + 1
        f["sec_tr"] = f["sub_eq"] + 2
        f["esc"] = f["sec_tr"] + 1
        f["flete"] = f["esc"] + 1
        f["disp"] = f["flete"] + 1
        f["sub_tr"] = f["disp"] + 1
        f["sec_res"] = f["sub_tr"] + 2
        for i, k in enumerate(("mat_r", "mo_r", "eq_r", "tr_r", "cd", "adm", "sub", "uti", "pu")):
            f[k] = f["sec_res"] + 1 + i
        f["nota"] = f["pu"] + 2
        return Maqueta(n_mat, n_mo, n_eq, f)

    def n(self, tipo: TipoInsumo) -> int:
        return {"mat": self.n_mat, "mo": self.n_mo, "eq": self.n_eq}[_SECCION[tipo]]

    def lineas(self, tipo: TipoInsumo) -> range:
        ini = self.filas["lin_" + _SECCION[tipo]]
        return range(ini, ini + self.n(tipo))

    def celda(self, r: Rotulo) -> tuple[int, int]:
        """(fila, columna) del rótulo en la maqueta (REND en F, el resto en G)."""
        return self.filas[_ROTULO_CLASE[r]], 6 if r is Rotulo.REND else 7

    @property
    def primera_linea(self) -> int:
        return self.filas["lin_mat"]

    @property
    def ultima_linea(self) -> int:
        return self.filas["lin_eq"] + self.n_eq - 1


def maqueta_del_libro(apus: list[ApuLeido]) -> Maqueta:
    def mayor(tipo: TipoInsumo) -> int:
        return max(
            [_MINIMO, *(sum(1 for x in a.lineas if x.tipo is tipo) for a in apus)],
        )

    return Maqueta.crear(
        mayor(TipoInsumo.MATERIAL), mayor(TipoInsumo.MANO_OBRA), mayor(TipoInsumo.EQUIPO)
    )


# --- Kit de estilos ------------------------------------------------------------------------------


@dataclass(slots=True)
class Kit:
    """Aspecto de los APU del libro: estilos por clase de fila y columna, textos y dimensiones."""

    estilos: dict[str, dict[int, Estilo]] = field(default_factory=dict)
    textos: dict[str, str] = field(default_factory=dict)
    encabezados: dict[str, tuple[str, ...]] = field(default_factory=dict)
    altos: dict[str, float] = field(default_factory=dict)
    anchos: dict[int, tuple[float | None, bool]] = field(default_factory=dict)
    impresion: dict[str, Any] = field(default_factory=dict)
    moneda: str = "USD ($)"
    sin_cuadricula: bool = False
    zoom: int | None = None
    base: Estilo = field(default_factory=Estilo)

    def estilo(self, clase: str, col: int) -> Estilo | None:
        vistos = set()
        k: str | None = clase
        while k is not None and k not in vistos:
            vistos.add(k)
            fila = self.estilos.get(k)
            if fila:
                return fila.get(col)
            k = _RESPALDOS.get(k)
        return None


def _clases_de_filas(ws: Any, apu: ApuLeido, perfil: Perfil) -> dict[int, str]:
    """Fila del APU original → clase de fila de la maqueta."""
    clases: dict[int, str] = {}
    for r, celda in apu.rotulos.items():
        clase = _ROTULO_CLASE.get(r)
        if clase is not None:
            fila = int("".join(ch for ch in celda.ref if ch.isdigit()))
            clases.setdefault(fila, clase)
    seccion = "mat"
    for fila in range(1, ws.max_row + 1):
        texto = ws.cell(fila, 1).value
        if fila in clases or not isinstance(texto, str):
            codigo = ws.cell(fila, 2).value
            if fila not in clases and perfil.es_codigo_insumo(codigo):
                tipo = TipoInsumo(str(codigo).strip()[:2].upper())
                clases[fila] = "lin_" + _SECCION[tipo]
            continue
        n = normalizar(texto)
        if n in ("ítem", "item"):
            clases[fila] = "enc_" + seccion
            continue
        for clase, prefijo in _PREFIJOS:
            if n.startswith(prefijo):
                clases[fila] = clase
                if clase.startswith("sec_") and clase[4:] in ("mat", "mo", "eq"):
                    seccion = clase[4:]
                break
        else:
            codigo = ws.cell(fila, 2).value
            if perfil.es_codigo_insumo(codigo):
                tipo = TipoInsumo(str(codigo).strip()[:2].upper())
                clases[fila] = "lin_" + _SECCION[tipo]
    return clases


def extraer_kit(
    ws: Any,
    apu: ApuLeido,
    perfil: Perfil,
    estilos: LectorEstilos,
    impresion: dict[str, Any],
    anchos: dict[int, tuple[float | None, bool]],
) -> Kit:
    """Lee el aspecto de un APU original (`ws`) para la maqueta uniforme."""
    kit = Kit(impresion=dict(impresion), anchos=dict(anchos))
    kit.base = Estilo(fuente=perfil.fuente, tamano=9, color=perfil.paleta.get("texto"))

    def fila_estilos(fila: int) -> dict[int, Estilo]:
        return {c: estilos.de_celda(ws.cell(fila, c)) for c in range(1, 9)}

    def alto(fila: int) -> float | None:
        rd = ws.row_dimensions.get(fila) if hasattr(ws.row_dimensions, "get") else None
        return rd.height if rd is not None and rd.height else None

    for clase, fila in (("titulo", 1), ("partida", 2), ("cab1", 4), ("cab2", 5), ("cab3", 6)):
        kit.estilos[clase] = fila_estilos(fila)
        if (h := alto(fila)) is not None:
            kit.altos[clase] = h
    clases = _clases_de_filas(ws, apu, perfil)
    ultima_pu = 0
    for fila, clase in sorted(clases.items()):
        if clase not in kit.estilos:
            kit.estilos[clase] = fila_estilos(fila)
            if (h := alto(fila)) is not None:
                kit.altos[clase] = h
            texto = ws.cell(fila, 1).value
            if isinstance(texto, str) and texto.strip() and not clase.startswith(("lin_", "enc_")):
                kit.textos[clase] = texto
            if clase.startswith("enc_"):
                kit.encabezados[clase[4:]] = tuple(
                    str(ws.cell(fila, c).value or "") for c in range(1, 9)
                )
        if clase == "pu":
            ultima_pu = fila
    for fila in range(ultima_pu + 1, ws.max_row + 1):
        texto = ws.cell(fila, 1).value
        if isinstance(texto, str) and texto.strip():
            kit.estilos["nota"] = fila_estilos(fila)
            if (h := alto(fila)) is not None:
                kit.altos["nota"] = h
            break
    for clase, col in (("titulo", 1), ("cab1", 1), ("cab1", 5), ("cab2", 1), ("cab2", 5)):
        texto = ws.cell({"titulo": 1, "cab1": 4, "cab2": 5}[clase], col).value
        if isinstance(texto, str) and texto.strip():
            kit.textos[f"{clase}_{col}"] = texto
    for col, clave_t in ((1, "cab3_1"), (5, "cab3_5")):
        texto = ws.cell(6, col).value
        if isinstance(texto, str) and texto.strip():
            kit.textos[clave_t] = texto
    moneda = ws.cell(6, 2).value
    if isinstance(moneda, str) and moneda.strip():
        kit.moneda = moneda
    vista = ws.sheet_view
    if vista is not None:
        kit.sin_cuadricula = vista.showGridLines is False
        kit.zoom = int(vista.zoomScale) if vista.zoomScale else None
    # Los rótulos deben seguir coincidiendo con el perfil (el libro devuelto se puede releer).
    for clase, r in _CLASE_ROTULO.items():
        texto = kit.textos.get(clase)
        if texto is not None and not coincide(texto, perfil.rotulos_apu[r].variantes):
            del kit.textos[clase]
    return kit


# --- Mapa de filas original → maqueta ------------------------------------------------------------


def mapa_filas(ws: Any, apu: ApuLeido, perfil: Perfil, maq: Maqueta) -> dict[int, int]:
    """Fila del APU original → fila de la maqueta (para reescribir referencias directas)."""
    mapa = {f: f for f in range(1, 7)}
    clases = _clases_de_filas(ws, apu, perfil)
    for fila, clase in clases.items():
        if clase in maq.filas and not clase.startswith("lin_"):
            mapa.setdefault(fila, maq.filas[clase])
    cuenta = {t: 0 for t in TipoInsumo}
    for linea in apu.lineas:
        fila = int("".join(ch for ch in linea.celda_codigo.ref if ch.isdigit()))
        i = cuenta[linea.tipo]
        cuenta[linea.tipo] += 1
        if i < maq.n(linea.tipo):
            mapa[fila] = maq.lineas(linea.tipo)[i]
    return mapa


# --- Generación ----------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DatosApu:
    """Lo que necesita `generar_apu` para una hoja."""

    apu: ApuLeido
    calculado: ApuCalculado
    fila_presupuesto: int | None
    hoja_presupuesto: str
    parametros: ParametrosLibro
    nombres: frozenset[str]
    libro: LibroLeido
    perfil: Perfil
    nota_extra: str = ""
    nota_original: str | None = None


_NO_INS = "⚠ no está en INSUMOS"


def _numero(d: Decimal) -> str:
    """Un Decimal como literal de fórmula, sin exponente."""
    t = format(d.normalize(), "f")
    return t.rstrip("0").rstrip(".") if "." in t else t


def _txt(kit: Kit, clase: str) -> str:
    return kit.textos.get(clase, TEXTOS.get(clase, ""))


def generar_apu(datos: DatosApu, maq: Maqueta, kit: Kit) -> HojaSalida:
    """La hoja APU con la maqueta uniforme, sus fórmulas y sus valores sembrados."""
    a, k = datos.apu, datos.calculado
    h = HojaSalida(a.hoja)
    h.anchos = dict(kit.anchos)
    h.sin_cuadricula = kit.sin_cuadricula
    h.zoom = kit.zoom
    f = maq.filas
    nombres = datos.nombres
    pres = cita(datos.hoja_presupuesto)

    def estilo(clase: str, col: int) -> Estilo:
        return kit.estilo(clase, col) or kit.base

    def fila_vacia(clase: str, fila: int, hasta: int = 8) -> None:
        for c in range(1, hasta + 1):
            h.poner(fila, c, None, estilo=estilo(clase, c))
        if clase in kit.altos:
            h.altos[fila] = (kit.altos[clase], False)

    def nombre_o(nombre: str, literal: Decimal) -> tuple[str | None, Decimal]:
        return (nombre if nombre in nombres else None), literal

    # Cabecera
    fila_vacia("titulo", 1)
    h.poner(1, 1, kit.textos.get("titulo_1", TEXTOS["titulo"]))
    h.combinadas.append((1, 1, 1, 7))
    fila_vacia("partida", 2)
    if datos.fila_presupuesto is not None:
        h.poner(2, 1, formula=f"=+{pres}!D{datos.fila_presupuesto}")
    else:
        h.poner(2, 1, a.titulo)
    h.combinadas.append((2, 1, 2, 7))
    t = kit.textos
    cab = (
        (4, "cab1", t.get("cab1_1", TEXTOS["cab_cod"]), "C", t.get("cab1_5", TEXTOS["cab_norma"])),
        (5, "cab2", t.get("cab2_1", TEXTOS["cab_und"]), "E", t.get("cab2_5", TEXTOS["cab_cli"])),
        (6, "cab3", t.get("cab3_1", TEXTOS["cab_mon"]), None, t.get("cab3_5", TEXTOS["cab_fecha"])),
    )
    nombre_cab = {4: "NORMA", 5: "CLIENTE", 6: "FECHAP"}
    respaldo_cab = {4: a.codigo_partida, 5: a.unidad, 6: kit.moneda}
    for fila, clase, etiqueta, col_pres, etiqueta2 in cab:
        nombre = nombre_cab[fila]
        fila_vacia(clase, fila)
        h.poner(fila, 1, etiqueta)
        if col_pres is not None and datos.fila_presupuesto is not None:
            h.poner(fila, 2, formula=f"=+{pres}!{col_pres}{datos.fila_presupuesto}")
        else:
            h.poner(fila, 2, respaldo_cab[fila])
        h.poner(fila, 5, etiqueta2)
        if nombre in nombres:
            h.poner(fila, 6, formula=f"={nombre}")
        h.combinadas.append((fila, 6, fila, 7))

    # Secciones de líneas (cantidad × precio de INSUMOS × factor de la plantilla; destajo aparte)
    rend = dir_celda(*maq.celda(Rotulo.REND))
    libro, perfil = datos.libro, datos.perfil
    base_filas = filas_base_mo(a, libro)
    divisor = divisor_equipos(a, libro)
    destajos: list[int] = []
    for tipo in (TipoInsumo.MATERIAL, TipoInsumo.MANO_OBRA, TipoInsumo.EQUIPO):
        s = _SECCION[tipo]
        fila_vacia("sec_" + s, f["sec_" + s])
        h.poner(f["sec_" + s], 1, _txt(kit, "sec_" + s))
        h.combinadas.append((f["sec_" + s], 1, f["sec_" + s], 7))
        fila_vacia("enc_" + s, f["enc_" + s])
        for c, texto in enumerate(kit.encabezados.get(s, _ENCABEZADOS[s]), start=1):
            h.poner(f["enc_" + s], c, texto or _ENCABEZADOS[s][c - 1])
        lineas = [x for x in a.lineas if x.tipo is tipo]
        for i, fila in enumerate(maq.lineas(tipo)):
            fila_vacia("lin_" + s, fila)
            linea = lineas[i] if i < len(lineas) else None
            factor = factor_linea(linea, libro, perfil) if linea else Decimal(1)
            por = "" if factor == 1 else f"*{_numero(factor)}"
            destajo = linea is not None and es_destajo(linea, libro, base_filas)
            h.poner(fila, 1, Decimal(i + 1))
            h.poner(fila, 2, linea.codigo if linea else None)
            b = f"$B{fila}"
            insumo = libro.insumo(linea.codigo) if linea else None
            if linea is not None and insumo is None:
                # Código que no está en INSUMOS: Silice usa lo que muestra el APU.
                h.poner(fila, 3, linea.descripcion or "⚠ no está en INSUMOS")
                h.poner(fila, 4, linea.unidad)
                h.poner(fila, 6, linea.precio)
            else:
                h.poner(
                    fila,
                    3,
                    formula=f'=IF({b}="","—",IFERROR(VLOOKUP({b},PRECIOS,2,0),"{_NO_INS}"))',
                )
                h.poner(fila, 4, formula=f'=IF({b}="","",IFERROR(VLOOKUP({b},PRECIOS,3,0),""))')
                h.poner(fila, 6, formula=f'=IF({b}="","",IFERROR(VLOOKUP({b},PRECIOS,4,0),0))')
            h.poner(fila, 5, linea.cantidad if linea else None)
            h.poner(fila, 7, formula=f'=IF({b}="",0,N($E{fila})*N($F{fila}){por})')
            if tipo is TipoInsumo.MATERIAL or destajo:
                h.poner(fila, 8, formula=f"=N($E{fila}){por}")
            elif tipo is TipoInsumo.EQUIPO and divisor is not None:
                h.poner(fila, 8, formula=f"=N($E{fila}){por}/{_numero(divisor)}")
            else:
                h.poner(fila, 8, formula=f"=IF(N({rend})=0,0,N($E{fila}){por}/{rend})")
            if destajo:
                destajos.append(fila)
        if _LISTA[tipo] in nombres:
            r = maq.lineas(tipo)
            h.validaciones.append(
                (f"B{r.start}:B{r.stop - 1}", {"validate": "list", "source": "=" + _LISTA[tipo]})
            )

    def rango_g(tipo: TipoInsumo) -> str:
        r = maq.lineas(tipo)
        return f"G{r.start}:G{r.stop - 1}"

    rango_mat = rango_g(TipoInsumo.MATERIAL)
    rango_mo = rango_g(TipoInsumo.MANO_OBRA)
    rango_eq = rango_g(TipoInsumo.EQUIPO)
    menos_destajo = "".join(f"-G{x}" for x in destajos)
    mas_destajo = "".join(f"+G{x}" for x in destajos)

    def rotulo(clase: str, formula: str | None, fijo: object, valor: object = None,
               col: int = 7, unir_hasta: int = 6) -> None:  # fmt: skip
        fila = f[clase]
        fila_vacia(clase, fila)
        h.poner(fila, 1, _txt(kit, clase))
        if formula is not None:
            h.poner(fila, col, formula=formula, fijo=NADA if fijo is None else fijo)
        else:
            h.poner(fila, col, valor)
        if unir_hasta >= 2:
            h.combinadas.append((fila, 1, fila, unir_hasta))

    g = {k2: f"G{v}" for k2, v in f.items()}
    rotulo("sub_mat", f"=SUM({rango_mat})", k.materiales)
    rotulo("base", f"=SUM({rango_mo}){menos_destajo}", k.base_mo_dia)
    # FCAS × Rendimiento: E = FCAS (nombre), F = rendimiento (editable)
    fila = f["rend"]
    fila_vacia("rend", fila)
    h.poner(fila, 1, _txt(kit, "rend"))
    fcas, fcas_lit = nombre_o("FCAS", datos.parametros.fcas)
    if fcas:
        h.poner(fila, 5, formula="=FCAS")
    else:
        h.poner(fila, 5, fcas_lit)
    h.poner(fila, 6, a.rendimiento)
    fcas_txt = "FCAS" if fcas else f"$E${fila}"
    rotulo(
        "costo",
        f"=IF(N({rend})=0,0,{g['base']}*{fcas_txt}/{rend}){mas_destajo}",
        k.mano_obra,
    )
    rotulo("sub_mo", f"={g['costo']}", k.mano_obra)
    rotulo("eq_dia", f"=SUM({rango_eq})", k.equipos_dia)
    if a.herramientas == 0:
        rotulo("herr", None, None, valor=Decimal(0))
    elif "HERR" in nombres:
        rotulo("herr", f"=HERR*{g['sub_mo']}", k.herramientas)
    else:
        rotulo("herr", f"={datos.parametros.herramientas}*{g['sub_mo']}", k.herramientas)
    if divisor is not None:
        rotulo("sub_eq", f"={g['eq_dia']}/{_numero(divisor)}+{g['herr']}", k.equipos)
    else:
        rotulo("sub_eq", f"=IF(N({rend})=0,0,{g['eq_dia']}/{rend})+{g['herr']}", k.equipos)
    fila_vacia("sec_tr", f["sec_tr"])
    h.poner(f["sec_tr"], 1, _txt(kit, "sec_tr"))
    h.combinadas.append((f["sec_tr"], 1, f["sec_tr"], 7))
    rotulo("esc", None, None, valor=a.escombro)
    esc = dir_celda(f["esc"], 7)
    p = datos.parametros
    flete = "FLETE" if "FLETE" in nombres else str(p.flete)
    camion = "CAMION" if "CAMION" in nombres else str(p.capacidad_camion)
    vert = "VERT" if "VERT" in nombres else str(p.tarifa_vertedero)
    rotulo("flete", f"=IF(OR(N({esc})=0,N({camion})=0),0,{flete}*{esc}/{camion})", None)
    rotulo("disp", f"=IF(N({esc})=0,0,{esc}*{vert})", None)
    rotulo("sub_tr", f"={g['flete']}+{g['disp']}", k.transporte)

    fila_vacia("sec_res", f["sec_res"])
    h.poner(f["sec_res"], 1, _txt(kit, "sec_res"))
    h.combinadas.append((f["sec_res"], 1, f["sec_res"], 7))
    rotulo("mat_r", f"={g['sub_mat']}", k.materiales)
    rotulo("mo_r", f"={g['sub_mo']}", k.mano_obra)
    rotulo("eq_r", f"={g['sub_eq']}", k.equipos)
    rotulo("tr_r", f"={g['sub_tr']}", k.transporte)
    rotulo("cd", f"={g['mat_r']}+{g['mo_r']}+{g['eq_r']}+{g['tr_r']}", k.costo_directo)
    for clase, rot, nombre, pct in (
        ("adm", "cd", "ADMON", a.administracion),
        ("uti", "sub", "UTIL", a.utilidad),
    ):
        global_ = p.administracion if clase == "adm" else p.utilidad
        fila = f[clase]
        monto = k.administracion if clase == "adm" else k.utilidad
        rotulo(clase, f"={g[rot]}*F{fila}", monto, unir_hasta=5)
        if nombre in nombres and pct == global_:
            h.poner(fila, 6, formula=f"={nombre}")
        else:
            h.poner(fila, 6, pct)
        if clase == "adm":
            rotulo("sub", f"={g['cd']}+{g['adm']}", k.subtotal)
    rotulo("pu", f"={g['sub']}+{g['uti']}", k.precio_unitario)

    fila = f["nota"]
    fila_vacia("nota", fila)
    silice = (
        "Hoja regenerada por Silice con forma uniforme: cada rótulo está en la misma celda en "
        "todos los APU y se publica como nombre definido (por ejemplo "
        f"{datos.nota_extra or 'APU_01_PU'}); el resto del libro lee por esos nombres."
    )
    celdas = {"rendimiento": f"{letra(6)}{f['rend']}", "escombro": f"{letra(7)}{f['esc']}"}
    if datos.nota_original:
        # La nota de la empresa se conserva; sus direcciones de celda pasan a las de la maqueta
        # (la plantilla decía "rendimiento (F28)" cuando el APU lo tenía en F27: causa C1).
        original = re.sub(
            r"(rendimiento|escombro)(\s*)\(\s*[A-Z]{1,3}\d+\s*\)",
            lambda m: f"{m.group(1)}{m.group(2)}({celdas[m.group(1).lower()]})",
            datos.nota_original,
            flags=re.IGNORECASE,
        )
        nota = f"{original.rstrip()} {silice}"
    else:
        nota = (
            "Celdas ámbar = editables: código (lista desplegable), cantidad/consumo, rendimiento "
            f"({celdas['rendimiento']}) y escombro ({celdas['escombro']}). Descripción, unidad y "
            "precio se llenan solos desde INSUMOS. Para quitar una línea borre código y cantidad. "
            + silice
        )
    h.poner(fila, 1, nota)
    h.combinadas.append((fila, 1, fila, 7))
    if "nota" not in kit.altos:
        h.altos[fila] = (48.0, False)

    imp = dict(kit.impresion)
    imp["area"] = f"{cita(a.hoja)}!$A$1:$G${fila}"
    h.impresion = imp
    return h
