"""Las tres hojas nuevas de la devolución: AUDITORÍA, TRAZABILIDAD y ALERTAS USD-Bs (spec 1.5 §1).

Llevan la paleta y la fuente del propio libro (tomadas del kit de los APU), para que se lean como
parte de él. Nada de lo que muestran se calcula aquí: los hallazgos, las alertas y la trazabilidad
llegan hechos en `DatosDevolucion`; el resumen por severidad de AUDITORÍA y el número de hallazgos
de cada regla evaluada son fórmulas (COUNTIF) sobre la tabla de hallazgos. Una alerta sin tasa dice
"no contrastable": nunca se escribe un número que no se pueda rastrear (§4).

Los impactos NO se suman en ninguna parte: un mismo error real puede aparecer en varias reglas (por
ejemplo F1, L4 y L9 por el mismo equipo omitido del costo directo) y una suma lo contaría varias
veces. El resumen por severidad solo cuenta hallazgos y una nota bajo la tabla lo advierte.

AUDITORÍA lleva, debajo de los hallazgos, las reglas evaluadas, las NO evaluadas con su motivo
(R11, R12 y L10 u L11 según el PDF recibido; errata 4 y 6 del spec) y los "Cambios del calcado"
(errata 3): lo que la devolución no pudo dejar como estaba en el libro recibido. Los impactos van en
la moneda del libro (`DatosDevolucion.moneda`).
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from adapters.hoja_empresa.escritor.apu import Kit
from adapters.hoja_empresa.escritor.estilos import Estilo
from adapters.hoja_empresa.escritor.hoja import HojaSalida, Nota
from adapters.hoja_empresa.modelo import DatosDevolucion, FilaTraza

__all__ = ["HOJAS_NUEVAS", "hoja_alertas", "hoja_auditoria", "hoja_trazabilidad"]

HOJAS_NUEVAS = ("AUDITORÍA", "TRAZABILIDAD", "ALERTAS USD-Bs")
NO_CONTRASTABLE = "no contrastable"
#: Nota bajo la tabla de hallazgos de AUDITORÍA.
NOTA_IMPACTOS = (
    "Los impactos no se suman: un mismo error puede aparecer en varias reglas (por ejemplo F1, L4 "
    "y L9)."
)
_SEVERIDADES = ("CRITICO", "ERROR", "ADVERTENCIA", "INFO")
_COLOR_SEVERIDAD = {
    "CRITICO": ("7B1E1E", "FFFFFF"),
    "ERROR": ("F8D7DA", "9C0006"),
    "ADVERTENCIA": ("FFF3CD", "7F6000"),
    "INFO": ("DDEBF7", "1F4E79"),
}
_METADATOS = (
    ("sha256_origen", "SHA-256 del libro recibido"),
    ("sha256_pdf", "SHA-256 del PDF entregado"),
    ("version", "Versión de Silice"),
    ("fecha", "Fecha de la devolución"),
    ("fecha_libro", "Fecha del libro"),
    ("producido_por", "Producido por"),
)


class _Paleta:
    def __init__(self, kit: Kit) -> None:
        base = kit.base
        self.titulo = (kit.estilo("titulo", 1) or base).con(horizontal="left", ajuste=False)
        self.seccion = (kit.estilo("sec_mat", 1) or self.titulo).con(horizontal="left")
        enc = kit.estilo("enc_mat", 3) or self.seccion
        self.encabezado = enc.con(horizontal="center", vertical="vcenter", ajuste=True)
        texto = kit.estilo("lin_mat", 3) or base
        self.texto = texto.con(
            ajuste=True, vertical="top", formato=None, horizontal="left", patron=0, fondo=None
        )
        self.numero = self.texto.con(horizontal="right", formato="#,##0.00")
        self.entero = self.texto.con(horizontal="center", formato="0")
        self.porcentaje = self.texto.con(horizontal="right", formato="0.00%")
        nota = kit.estilo("nota", 1) or base
        self.nota = nota.con(ajuste=True, vertical="top", horizontal="left")
        sub = kit.estilo("sub_mat", 1) or self.encabezado
        self.total = sub.con(horizontal="left", ajuste=False)
        self.total_num = sub.con(horizontal="right", formato="#,##0.00")
        self.total_entero = sub.con(horizontal="center", formato="0")
        self.etiqueta = self.texto.con(negrita=True)
        self.tenue = self.texto.con(cursiva=True, color=nota.color or self.texto.color)


def _titulo(h: HojaSalida, p: _Paleta, texto: str, subtitulo: str, ancho: int) -> None:
    for c in range(1, ancho + 1):
        h.poner(1, c, None, estilo=p.titulo)
        h.poner(2, c, None, estilo=p.nota)
    h.poner(1, 1, texto)
    h.poner(2, 1, subtitulo)
    h.combinadas += [(1, 1, 1, ancho), (2, 1, 2, ancho)]
    h.altos[1] = (22.0, False)
    h.altos[2] = (30.0, False)
    h.sin_cuadricula = True


def _seccion(h: HojaSalida, p: _Paleta, fila: int, texto: str, ancho: int) -> None:
    for c in range(1, ancho + 1):
        h.poner(fila, c, None, estilo=p.seccion)
    h.poner(fila, 1, texto)
    h.combinadas.append((fila, 1, fila, ancho))


def _encabezados(h: HojaSalida, p: _Paleta, fila: int, textos: Sequence[str]) -> None:
    for c, t in enumerate(textos, start=1):
        h.poner(fila, c, t, estilo=p.encabezado)
    h.altos[fila] = (28.0, False)


def hoja_auditoria(
    datos: DatosDevolucion,
    kit: Kit,
    transformaciones: Sequence[tuple[str, str, str]] = (),
) -> HojaSalida:
    """La hoja AUDITORÍA. `transformaciones` son `(tipo, celda, descripción)` de los cambios que
    hizo el calcado (sección "CAMBIOS DEL CALCADO")."""
    p = _Paleta(kit)
    h = HojaSalida("AUDITORÍA")
    hallazgos = datos.hallazgos
    impacto = f"Impacto ({datos.moneda})"
    _titulo(
        h,
        p,
        "AUDITORÍA DEL LIBRO · hallazgos de Silice",
        f"Libro recibido: {datos.libro.nombre} · {len(hallazgos)} hallazgo(s). «corregido»: la "
        "devolución ya trae el valor recalculado; «a confirmar»: se conserva lo escrito y la "
        "empresa decide; «informado»: solo se informa. Las celdas citadas son las del libro "
        "recibido (los APU de esta devolución tienen forma uniforme).",
        6,
    )
    # Solo se cuentan hallazgos: los impactos no se suman (ver la nota bajo la tabla).
    _seccion(h, p, 4, "RESUMEN POR SEVERIDAD", 2)
    _encabezados(h, p, 5, ("Severidad", "Hallazgos"))
    ini = 13
    fin = ini + max(len(hallazgos), 1) - 1
    rango_b = f"$B${ini}:$B${fin}"
    for i, sev in enumerate(_SEVERIDADES):
        fila = 6 + i
        h.poner(fila, 1, sev, estilo=p.etiqueta)
        h.poner(fila, 2, formula=f'=COUNTIF({rango_b},"{sev}")', estilo=p.entero)
    h.poner(10, 1, "Total", estilo=p.total)
    h.poner(10, 2, formula="=SUM(B6:B9)", estilo=p.total_entero)
    _seccion(h, p, 11, "HALLAZGOS", 6)
    _encabezados(h, p, 12, ("Código", "Severidad", "Descripción", "Celda", impacto, "Acción"))
    if not hallazgos:
        h.poner(ini, 1, "Sin hallazgos.", estilo=p.tenue)
        h.combinadas.append((ini, 1, ini, 6))
    for i, x in enumerate(hallazgos):
        f = ini + i
        h.poner(f, 1, x.codigo, estilo=p.etiqueta)
        h.poner(f, 2, x.severidad, estilo=p.texto.con(horizontal="center"))
        h.poner(f, 3, x.descripcion, estilo=p.texto)
        h.poner(f, 4, x.celda, estilo=p.texto)
        h.poner(f, 5, x.impacto, estilo=p.numero)
        h.poner(f, 6, x.accion, estilo=p.texto)
    for sev, (fondo, color) in _COLOR_SEVERIDAD.items():
        h.condicionales.append(
            (
                f"B{ini}:B{fin}",
                {"type": "cell", "criteria": "==", "value": f'"{sev}"'},
                Estilo(patron=1, fondo=fondo, color=color, negrita=True),
            )
        )
        h.condicionales.append(
            (
                "A6:A9",
                {"type": "cell", "criteria": "==", "value": f'"{sev}"'},
                Estilo(patron=1, fondo=fondo, color=color, negrita=True),
            )
        )
    h.poner(fin + 1, 1, NOTA_IMPACTOS, estilo=p.tenue)
    for c in range(2, 7):
        h.poner(fin + 1, c, None, estilo=p.tenue)
    h.combinadas.append((fin + 1, 1, fin + 1, 6))
    ultima = _reglas_y_cambios(h, p, fin + 3, datos, f"$A${ini}:$A${fin}", transformaciones)
    h.anchos = {1: (12.0, False), 2: (14.0, False), 3: (70.0, False), 4: (24.0, False)}
    h.anchos |= {5: (15.0, False), 6: (14.0, False)}
    h.paneles = (12, 0)
    h.impresion = {"orientacion": "landscape", "ajuste": (1, 0), "area": f"A1:F{ultima}"}
    return h


def _fila_larga(h: HojaSalida, p: _Paleta, fila: int, textos: Sequence[str]) -> None:
    """Código, nombre (columna B) y un texto largo combinado en C:F."""
    h.poner(fila, 1, textos[0], estilo=p.etiqueta)
    h.poner(fila, 2, textos[1], estilo=p.texto)
    h.poner(fila, 3, textos[2], estilo=p.texto)
    for c in range(4, 7):
        h.poner(fila, c, None, estilo=p.texto)
    h.combinadas.append((fila, 3, fila, 6))


def _reglas_y_cambios(
    h: HojaSalida,
    p: _Paleta,
    fila: int,
    datos: DatosDevolucion,
    rango_codigos: str,
    transformaciones: Sequence[tuple[str, str, str]],
) -> int:
    """Reglas evaluadas (con su número de hallazgos), reglas no evaluadas (con su motivo) y cambios
    del calcado, desde `fila`. Devuelve la última fila escrita."""
    _seccion(h, p, fila, "REGLAS EVALUADAS", 6)
    fila += 1
    _encabezados(h, p, fila, ("Código", "Regla", "Hallazgos"))
    if not datos.reglas_evaluadas:
        fila += 1
        h.poner(fila, 1, "—", estilo=p.tenue)
    for codigo, nombre in datos.reglas_evaluadas:
        fila += 1
        h.poner(fila, 1, codigo, estilo=p.etiqueta)
        h.poner(fila, 2, nombre, estilo=p.texto)
        h.poner(fila, 3, formula=f'=COUNTIF({rango_codigos},"{codigo}")', estilo=p.entero)
    fila += 2
    _seccion(h, p, fila, "REGLAS NO EVALUADAS", 6)
    fila += 1
    _encabezados(h, p, fila, ("Código", "Regla", "Motivo"))
    if not datos.reglas_no_evaluadas:
        fila += 1
        h.poner(fila, 1, "Todas las reglas se evaluaron.", estilo=p.tenue)
        h.combinadas.append((fila, 1, fila, 6))
    for codigo, nombre, motivo in datos.reglas_no_evaluadas:
        fila += 1
        _fila_larga(h, p, fila, (codigo, nombre, motivo))
    fila += 2
    _seccion(h, p, fila, "CAMBIOS DEL CALCADO", 6)
    fila += 1
    _encabezados(h, p, fila, ("Tipo", "Celda", "Descripción"))
    if not transformaciones:
        fila += 1
        h.poner(
            fila, 1, "El calcado no cambió nada fuera de los valores de Silice.", estilo=p.tenue
        )
        h.combinadas.append((fila, 1, fila, 6))
    for tipo, celda, descripcion in transformaciones:
        fila += 1
        _fila_larga(h, p, fila, (tipo, celda, descripcion))
    return fila


def hoja_trazabilidad(datos: DatosDevolucion, notas: Sequence[Nota], kit: Kit) -> HojaSalida:
    p = _Paleta(kit)
    h = HojaSalida("TRAZABILIDAD")
    _titulo(
        h,
        p,
        "TRAZABILIDAD DE LA DEVOLUCIÓN",
        "De dónde sale cada dato que Silice usó y qué cambió el calcado respecto del libro "
        "recibido (celda de origen HOJA!CELDA).",
        4,
    )
    meta = dict(datos.metadatos)
    meta.setdefault("sha256_origen", datos.libro.sha256)
    fila = 4
    _seccion(h, p, fila, "DOCUMENTO", 4)
    fila += 1
    h.poner(fila, 1, "Libro recibido", estilo=p.etiqueta)
    h.poner(fila, 2, datos.libro.nombre, estilo=p.texto)
    h.combinadas.append((fila, 2, fila, 4))
    fila += 1
    vistos = set()
    for k, etiqueta in _METADATOS:
        if k in meta and meta[k]:
            vistos.add(k)
            h.poner(fila, 1, etiqueta, estilo=p.etiqueta)
            h.poner(fila, 2, str(meta[k]), estilo=p.texto)
            h.combinadas.append((fila, 2, fila, 4))
            fila += 1
    for k, v in meta.items():
        if k not in vistos and v:
            h.poner(fila, 1, k, estilo=p.etiqueta)
            h.poner(fila, 2, str(v), estilo=p.texto)
            h.combinadas.append((fila, 2, fila, 4))
            fila += 1
    fila += 1
    fila = _tabla_traza(h, p, fila, "DATOS QUE USÓ SILICE", datos.trazabilidad)
    fila += 1
    trans = [FilaTraza(n.dato, n.valor, n.origen, n.nota) for n in notas]
    _tabla_traza(h, p, fila, "TRANSFORMACIONES DEL CALCADO", trans)
    h.anchos = {1: (34.0, False), 2: (40.0, False), 3: (26.0, False), 4: (70.0, False)}
    h.impresion = {"orientacion": "landscape", "ajuste": (1, 0)}
    return h


def _tabla_traza(
    h: HojaSalida, p: _Paleta, fila: int, titulo: str, filas: Sequence[FilaTraza]
) -> int:
    _seccion(h, p, fila, titulo, 4)
    fila += 1
    _encabezados(h, p, fila, ("Dato", "Valor", "Origen", "Nota"))
    fila += 1
    if not filas:
        h.poner(fila, 1, "—", estilo=p.tenue)
        return fila + 1
    for x in filas:
        h.poner(fila, 1, x.dato, estilo=p.etiqueta)
        h.poner(fila, 2, x.valor, estilo=p.texto)
        h.poner(fila, 3, x.origen, estilo=p.texto)
        h.poner(fila, 4, x.nota, estilo=p.texto)
        fila += 1
    return fila


def hoja_alertas(datos: DatosDevolucion, kit: Kit) -> HojaSalida:
    p = _Paleta(kit)
    h = HojaSalida("ALERTAS USD-Bs")
    alertas = datos.alertas
    _titulo(
        h,
        p,
        "ALERTAS DE PRECIO EN USD Y Bs",
        "Insumos sin fuente, cambios contra la base de la empresa o contra otra versión del "
        "libro, y equivalente en Bs a la tasa BCV. Sin tasa, la alerta dice «no contrastable».",
        11,
    )
    _encabezados(
        h,
        p,
        4,
        (
            "Código",
            "Descripción",
            "Tipo",
            "Moneda",
            "Precio",
            "Fecha",
            "Fuente",
            "Tasa BCV (Bs/USD)",
            "Precio en Bs",
            "Variación",
            "Mensaje",
        ),
    )
    if not alertas:
        h.poner(5, 1, "Sin alertas.", estilo=p.tenue)
        h.combinadas.append((5, 1, 5, 11))
    for i, a in enumerate(alertas):
        f = 5 + i
        h.poner(f, 1, a.codigo, estilo=p.etiqueta)
        h.poner(f, 2, a.descripcion, estilo=p.texto)
        h.poner(f, 3, a.tipo, estilo=p.texto)
        h.poner(f, 4, a.moneda, estilo=p.texto.con(horizontal="center"))
        h.poner(f, 5, a.precio, estilo=p.numero)
        h.poner(f, 6, a.fecha, estilo=p.texto.con(horizontal="center"))
        h.poner(f, 7, a.fuente, estilo=p.texto)
        _o_no_contrastable(h, p, f, 8, a.tasa, p.numero.con(formato="#,##0.0000"))
        _o_no_contrastable(h, p, f, 9, a.precio_bs, p.numero)
        if a.variacion is None:
            h.poner(f, 10, "—", estilo=p.tenue.con(horizontal="center"))
        else:
            h.poner(f, 10, a.variacion, estilo=p.porcentaje)
        h.poner(f, 11, a.mensaje, estilo=p.texto)
    h.anchos = {1: (10.0, False), 2: (34.0, False), 3: (16.0, False), 4: (8.0, False)}
    h.anchos |= {5: (12.0, False), 6: (12.0, False), 7: (22.0, False), 8: (14.0, False)}
    h.anchos |= {9: (14.0, False), 10: (11.0, False), 11: (48.0, False)}
    h.paneles = (4, 0)
    h.impresion = {"orientacion": "landscape", "ajuste": (1, 0)}
    return h


def _o_no_contrastable(
    h: HojaSalida, p: _Paleta, f: int, c: int, v: Decimal | None, estilo: Estilo
) -> None:
    if v is None:
        h.poner(f, c, NO_CONTRASTABLE, estilo=p.tenue.con(horizontal="center"))
    else:
        h.poner(f, c, v, estilo=estilo)
