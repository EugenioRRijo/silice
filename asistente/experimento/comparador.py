"""Comparador determinista del borrador final con la referencia (S4 §9.5). Taxonomia cerrada E1-E8.

El modelo inventa sus propios ids, asi que el comparador NUNCA empareja por id (PRU-H7). Empareja
como R16 (S3 §11.4):

1. candidatos: misma clase (ambiente, fuente, punto, recorrido, partida), misma especialidad y
   mismo tipo enumerado;
2. distancia: ambientes, entre sus esquinas (`x0`, `y0`); fuentes y puntos, en 3D. Si la tarea es de
   POSICION LIBRE, antes de emparejar se traslada el borrador para que la esquina de su primer
   ambiente (en orden canonico) coincida con la de la referencia; la traslacion se registra;
3. vecino mas cercano con tolerancia: todos los pares candidatos por distancia (empates: orden
   canonico por coordenadas, nunca por id) y se toma cada par con los dos lados libres y distancia
   <= 0,10 m (`SUPUESTO_DECLARADO`, la de R16);
4. clasificacion de cada par, 5. sobrantes (E6 de la referencia, E7 del borrador).

Un elemento desplazado mas de 0,10 m cuenta como omitido mas sobrante (E6 + E7), no como E3
(RS4-12).
E8: el valor sembrado en el pedido que QUEDA en el borrador (no lo que el modelo diga en texto).
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from decimal import Decimal

from adapters.espacio import Espacio
from asistente.experimento.modelo import Referencia
from core.contracts.item_computo import ItemComputo, OrigenTipo
from core.contracts.unidades import unidades_equivalentes
from core.contracts.verificacion import Hallazgo

TOLERANCIA_EMPAREJAMIENTO = Decimal("0.10")  # SUPUESTO_DECLARADO (la de R16)
TOLERANCIA_MEDIDA = Decimal("0.001")
CLASES = ("ambiente", "fuente", "punto", "recorrido", "partida")


@dataclass(frozen=True, slots=True)
class Error:
    tipo: str  # E1..E8
    clase: str
    clave_borrador: str | None  # `esp_puntos:P1`, `ia:7:P5`...; None si no hay fila (E6)
    clave_referencia: str | None
    campo: str = ""


@dataclass(frozen=True, slots=True)
class Comparacion:
    errores: tuple[Error, ...]
    #: (clase, id del borrador) -> id de la referencia, para traducir las claves de los hallazgos
    pares: dict[tuple[str, str], str]
    traslacion: tuple[Decimal, Decimal] = (Decimal(0), Decimal(0))
    sobrantes_de_referencia: tuple[str, ...] = field(default=())


@dataclass(frozen=True, slots=True)
class _El:
    clase: str
    id: str
    especialidad: str
    tipo: str
    pos: tuple[Decimal, ...]  # ambiente: (x0, y0); fuente/punto: (x, y, z)
    datos: dict[str, object]

    def orden(self) -> tuple:
        """Orden canonico: por coordenadas y tipo, NUNCA por id."""
        return (
            *self.pos,
            self.tipo,
            str(self.datos.get("dims", "")),
            str(self.datos.get("codigo", "")),
        )


def _elementos(
    espacio: Espacio, items: Iterable[ItemComputo], dx: Decimal, dy: Decimal
) -> list[_El]:
    elementos: list[_El] = []
    for a in espacio.ambientes:
        elementos.append(
            _El(
                "ambiente",
                a.id,
                "",
                "",
                (a.x0 + dx, a.y0 + dy),
                {"dims": (a.largo, a.ancho, a.alto), "ambiente": a},
            )
        )
    for f in espacio.fuentes:
        p = f.posicion
        elementos.append(
            _El(
                "fuente",
                f.id,
                f.especialidad.value,
                f.tipo.value,
                (p.x + dx, p.y + dy, p.z),
                {"ambiente_id": f.ambiente_id},
            )
        )
    for p in espacio.puntos:
        c = p.posicion
        elementos.append(
            _El(
                "punto",
                p.id,
                p.especialidad.value,
                p.tipo.value,
                (c.x + dx, c.y + dy, c.z),
                {
                    "ambiente_id": p.ambiente_id,
                    "fuente_id": p.fuente_id,
                    "circuito_id": p.circuito_id,
                    "coord": c,
                },
            )
        )
    for r in espacio.recorridos:
        tramos = tuple(tuple((v.x + dx, v.y + dy, v.z) for v in t.vertices) for t in r.tramos)
        elementos.append(
            _El(
                "recorrido",
                r.id,
                "",
                r.modo.value,
                (),
                {"punto_id": r.punto_id, "circuito_id": r.circuito_id, "tramos": tramos},
            )
        )
    for i in items:
        if i.origen_tipo is OrigenTipo.MANUAL:
            elementos.append(
                _El(
                    "partida",
                    i.origen_id,
                    i.dominio.value,
                    "",
                    (),
                    {"codigo": i.codigo_partida, "unidad": i.unidad, "cantidad": i.cantidad},
                )
            )
    return elementos


def _distancia(a: _El, b: _El) -> Decimal:
    return sum(((x - y) ** 2 for x, y in zip(a.pos, b.pos, strict=True)), Decimal(0)).sqrt()


def _emparejar(refs: Sequence[_El], bs: Sequence[_El]) -> list[tuple[_El, _El]]:
    candidatos = sorted(
        (
            (_distancia(r, b), r.orden(), b.orden(), i, j)
            for i, r in enumerate(refs)
            for j, b in enumerate(bs)
            if (r.especialidad, r.tipo) == (b.especialidad, b.tipo)
        ),
        key=lambda c: c[:3] + (c[3], c[4]),
    )
    libres_r, libres_b = set(range(len(refs))), set(range(len(bs)))
    pares: list[tuple[_El, _El]] = []
    for distancia, _, _, i, j in candidatos:
        if distancia <= TOLERANCIA_EMPAREJAMIENTO and i in libres_r and j in libres_b:
            libres_r.discard(i)
            libres_b.discard(j)
            pares.append((refs[i], bs[j]))
    return pares


def _difiere(a: Decimal, b: Decimal) -> bool:
    return abs(a - b) > TOLERANCIA_MEDIDA


TABLAS = {
    "ambiente": "esp_ambientes",
    "fuente": "esp_fuentes",
    "punto": "esp_puntos",
    "recorrido": "esp_recorridos",
}
CLASE_DE_TABLA = {tabla: clase for clase, tabla in TABLAS.items()}


def _clave(el: _El) -> str:
    return el.id if el.clase == "partida" else f"{TABLAS[el.clase]}:{el.id}"


def _esquina(espacio: Espacio) -> tuple[Decimal, Decimal] | None:
    if not espacio.ambientes:
        return None
    primero = min(espacio.ambientes, key=lambda a: (a.x0, a.y0, a.largo, a.ancho, a.alto))
    return primero.x0, primero.y0


def comparar(referencia: Referencia, espacio: Espacio, items: Sequence[ItemComputo]) -> Comparacion:
    dx = dy = Decimal(0)
    if referencia.posicion_libre:
        esquina_ref, esquina_b = _esquina(referencia.espacio), _esquina(espacio)
        if esquina_ref and esquina_b:
            dx, dy = esquina_ref[0] - esquina_b[0], esquina_ref[1] - esquina_b[1]
    refs = _elementos(referencia.espacio, referencia.items, Decimal(0), Decimal(0))
    bs = _elementos(espacio, items, dx, dy)
    por_clase = {
        c: ([e for e in refs if e.clase == c], [e for e in bs if e.clase == c]) for c in CLASES
    }
    errores: list[Error] = []
    pares_id: dict[tuple[str, str], str] = {}
    emparejados: dict[str, list[tuple[_El, _El]]] = {}
    # ambientes, fuentes y puntos por distancia; recorridos y partidas por su propia llave
    for clase in ("ambiente", "fuente", "punto"):
        pares = _emparejar(*por_clase[clase])
        pares += _emparejar_sembrados(clase, referencia.sembrados, por_clase[clase], pares)
        emparejados[clase] = pares
        for r, b in pares:
            pares_id[(clase, b.id)] = r.id
    emparejados["recorrido"] = _pares_de_recorridos(*por_clase["recorrido"], pares_id)
    emparejados["partida"] = _pares_de_partidas(*por_clase["partida"])
    for clase in ("recorrido", "partida"):
        for r, b in emparejados[clase]:
            pares_id[(clase, b.id)] = r.id
    for clase in CLASES:
        usados_r = {r.id for r, _ in emparejados[clase]}
        usados_b = {b.id for _, b in emparejados[clase]}
        for r, b in emparejados[clase]:
            errores.extend(_clasificar(clase, r, b, referencia, espacio, pares_id))
        errores.extend(
            Error("E6", clase, None, _clave(r)) for r in por_clase[clase][0] if r.id not in usados_r
        )
        errores.extend(
            Error("E7", clase, _clave(b), None) for b in por_clase[clase][1] if b.id not in usados_b
        )
    errores = _aplicar_sembrados(errores, referencia, emparejados, pares_id)
    return Comparacion(tuple(errores), pares_id, (dx, dy))


def _emparejar_sembrados(clase, sembrados, elementos, pares) -> list[tuple[_El, _El]]:
    """Segundo pase: el elemento de la referencia con un dato sembrado se empareja tambien contra
    su variante con el valor sembrado, para que un E8 lejos de la referencia no sea E6 + E7."""
    refs, bs = elementos
    usados_r = {r.id for r, _ in pares}
    usados_b = {b.id for _, b in pares}
    nuevos: list[tuple[_El, _El]] = []
    for s in sembrados:
        r = next((x for x in refs if x.id == s.id_referencia and x.clase == clase), None)
        indice = _CAMPOS.get(s.campo)
        if r is None or indice is None or r.id in usados_r or indice >= len(r.pos):
            continue
        pos = list(r.pos)
        pos[indice] = s.valor
        variante = _El(r.clase, r.id, r.especialidad, r.tipo, tuple(pos), r.datos)
        libres = [b for b in bs if b.id not in usados_b]
        for _, b in _emparejar([variante], libres):
            nuevos.append((r, b))
            usados_r.add(r.id)
            usados_b.add(b.id)
    return nuevos


def _pares_de_recorridos(refs, bs, pares_id):
    pares, libres = [], list(bs)
    for r in refs:
        for b in libres:
            traducido = (
                pares_id.get(("punto", b.datos["punto_id"])) if b.datos["punto_id"] else None
            )
            mismo_punto = r.datos["punto_id"] is not None and traducido == r.datos["punto_id"]
            mismo_circuito = (
                r.datos["circuito_id"] is not None
                and r.datos["circuito_id"] == b.datos["circuito_id"]
            )
            if mismo_punto or mismo_circuito:
                pares.append((r, b))
                libres.remove(b)
                break
    return pares


def _pares_de_partidas(refs, bs):
    pares, libres_r, libres_b = [], list(refs), list(bs)
    for r in list(libres_r):  # primero, por codigo igual
        for b in libres_b:
            if b.datos["codigo"] == r.datos["codigo"]:
                pares.append((r, b))
                libres_r.remove(r)
                libres_b.remove(b)
                break
    for r in list(
        libres_r
    ):  # luego, las sobrantes de la misma especialidad, en el orden de los items
        for b in libres_b:
            if b.especialidad == r.especialidad:
                pares.append((r, b))
                libres_r.remove(r)
                libres_b.remove(b)
                break
    return pares


def _clasificar(clase, r: _El, b: _El, referencia, espacio, pares_id) -> list[Error]:
    cb, cr = _clave(b), _clave(r)

    def e(tipo: str, campo: str = "") -> Error:
        return Error(tipo, clase, cb, cr, campo)

    errores: list[Error] = []
    if clase == "ambiente":
        for campo, vr, vb in zip(("x0", "y0"), r.pos, b.pos, strict=True):
            if _difiere(vr, vb):
                errores.append(e("E3", campo))
        for campo, vr, vb in zip(
            ("largo", "ancho", "alto"), r.datos["dims"], b.datos["dims"], strict=True
        ):
            if _difiere(vr, vb):
                errores.append(e("E3", campo))
    elif clase in ("fuente", "punto"):
        for campo, vr, vb in zip(("x", "y", "z"), r.pos, b.pos, strict=True):
            if _difiere(vr, vb):
                errores.append(e("E3", campo))
        if pares_id.get(("ambiente", b.datos["ambiente_id"])) != r.datos["ambiente_id"]:
            errores.append(e("E4", "ambiente_id"))
        elif clase == "punto" and not any(a.contiene(b.datos["coord"]) for a in espacio.ambientes):
            errores.append(e("E4", "fuera"))
        if clase == "punto":
            fuente_b = b.datos["fuente_id"]
            if (pares_id.get(("fuente", fuente_b)) if fuente_b else None) != r.datos["fuente_id"]:
                errores.append(e("E5", "fuente_id"))
            if b.datos["circuito_id"] != r.datos["circuito_id"]:
                errores.append(e("E5", "circuito_id"))
    elif clase == "recorrido":
        if r.tipo != b.tipo:
            errores.append(e("E3", "modo"))
        elif not _mismos_tramos(r.datos["tramos"], b.datos["tramos"]):
            errores.append(e("E3", "tramos"))
    else:  # partida
        if r.datos["codigo"] != b.datos["codigo"]:
            errores.append(
                e("E1" if unidades_equivalentes(r.datos["unidad"], b.datos["unidad"]) else "E2")
            )
        elif not unidades_equivalentes(r.datos["unidad"], b.datos["unidad"]):
            errores.append(e("E2"))
        if _difiere(r.datos["cantidad"], b.datos["cantidad"]):
            errores.append(e("E3", "cantidad"))
    return errores


def _mismos_tramos(a, b) -> bool:
    return len(a) == len(b) and all(
        len(ta) == len(tb)
        and all(
            not _difiere(x, y)
            for va, vb in zip(ta, tb, strict=True)
            for x, y in zip(va, vb, strict=True)
        )
        for ta, tb in zip(a, b, strict=True)
    )


_CAMPOS = {"x0": 0, "y0": 1, "x": 0, "y": 1, "z": 2}


def _valor(el: _El, campo: str) -> Decimal | None:
    if campo in _CAMPOS and _CAMPOS[campo] < len(el.pos):
        return el.pos[_CAMPOS[campo]]
    dims = {"largo": 0, "ancho": 1, "alto": 2}
    if campo in dims and "dims" in el.datos:
        return el.datos["dims"][dims[campo]]
    if campo == "cantidad":
        return el.datos.get("cantidad")
    return None


def _aplicar_sembrados(errores, referencia, emparejados, pares_id) -> list[Error]:
    """E8: el valor sembrado queda en el borrador. Un E8 no se cuenta ademas como E3."""
    resultado = list(errores)
    for s in referencia.sembrados:
        par = next((p for p in emparejados[s.clase] if p[0].id == s.id_referencia), None)
        if par is None:
            continue  # el elemento no aparece: es E6, no E8
        valor = _valor(par[1], s.campo)
        if valor is None or _difiere(valor, s.valor):
            continue
        clave_ref = _clave(par[0])
        for i, e in enumerate(resultado):
            if (e.tipo, e.clase, e.clave_referencia, e.campo) == (
                "E3",
                s.clase,
                clave_ref,
                s.campo,
            ):
                resultado[i] = Error("E8", e.clase, e.clave_borrador, e.clave_referencia, e.campo)
        # el mismo defecto no se cuenta dos veces: el punto «fuera» por el valor sembrado es E8
        resultado = [
            e
            for e in resultado
            if not (e.tipo == "E4" and e.campo == "fuera" and e.clave_referencia == clave_ref)
        ]
    return resultado


# --- hallazgos: esperados por construccion, detecciones y falsas alarmas -----------------------


def _partes(origen_ids: Iterable[str]) -> list[str]:
    return [p.strip() for o in origen_ids for p in o.split(";") if p.strip()]


def _traducir(clave: str, pares_id: dict[tuple[str, str], str] | None) -> str:
    """La clave del borrador llevada a la de la referencia; `None`: ya es de la referencia."""
    if pares_id is None:
        return clave
    tabla, _, id_ = clave.partition(":")
    if tabla in CLASE_DE_TABLA:
        ref = pares_id.get((CLASE_DE_TABLA[tabla], id_))
        return f"{tabla}:{ref}" if ref is not None else f"?{clave}"
    ref = pares_id.get(("partida", clave))
    return ref if ref is not None else clave


def clave_de_hallazgo(h: Hallazgo, pares_id: dict[tuple[str, str], str] | None) -> tuple:
    """(regla, severidad, claves traducidas): sin descripcion, que repite los ids del modelo."""
    claves = sorted(_traducir(c, pares_id) for c in _partes(h.origen_ids))
    return (h.regla, h.severidad.name, tuple(claves))


@dataclass(frozen=True, slots=True)
class Veredicto:
    """Lo que dejo el auditor sobre una corrida: errores detectados y hallazgos sin esperar."""

    detectados: tuple[Error, ...]
    escapan: tuple[Error, ...]
    inesperados: int
    falsas_alarmas: int


def evaluar_hallazgos(
    comparacion: Comparacion,
    hallazgos_borrador: Sequence[Hallazgo],
    hallazgos_referencia: Sequence[Hallazgo],
) -> Veredicto:
    """Un error se DETECTA si algun hallazgo NO esperado cita su fila o su item; una FALSA ALARMA
    es un hallazgo no esperado que no cita ninguna fila con error. Los hallazgos que da la
    referencia misma (R8 de constantes supuestas, R1 de cada MANUAL...) no cuentan (§9.5)."""
    esperados = Counter(clave_de_hallazgo(h, None) for h in hallazgos_referencia)
    inesperados: list[Hallazgo] = []
    for h in hallazgos_borrador:
        clave = clave_de_hallazgo(h, comparacion.pares)
        if esperados[clave] > 0:
            esperados[clave] -= 1
        else:
            inesperados.append(h)
    claves_con_error = {e.clave_borrador for e in comparacion.errores if e.clave_borrador}
    citadas = [set(_partes(h.origen_ids)) for h in inesperados]
    detectados = tuple(
        e
        for e in comparacion.errores
        if e.clave_borrador and any(e.clave_borrador in c for c in citadas)
    )
    escapan = tuple(e for e in comparacion.errores if e not in detectados)
    falsas = sum(1 for c in citadas if not (c & claves_con_error))
    return Veredicto(detectados, escapan, len(inesperados), falsas)
