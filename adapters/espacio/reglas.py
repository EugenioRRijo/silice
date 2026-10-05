"""Reglas de auditoria del espacio: R8 (origen de la medida) y R9 (coherencia espacial), spec §8.2.

Son `ReglaVerificacion` del contrato de `core`: `elaborar(reglas=REGLAS + reglas_espacio(espacio))`
las corre con las siete. Cada regla guarda la instantanea del espacio de la version (DA-SF-8): el
`Espacio` es inmutable, asi que la referencia es la instantanea. El presupuesto que reciben
`evaluar` no se lee: la regla habla del espacio, no de las partidas.

Cada hallazgo cita en `origen_ids` la clave `esp_*` de la fila (formato de `origen.clave_esp`), que
es lo que usa la columna Estado. No implementan `atribuir` (`ReglaAtribuible` no es un contrato) y
`Hallazgo.regla` mide a lo mas 10 caracteres (`R8`, `R9`). Un hallazgo por condicion y por fila; el
orden es estable: por tabla y, dentro de ella, por id (el modelo ya ordena sus tuplas).

**R8**, una fila del espacio que produce cantidad (ambiente, fuente o punto) cita un origen de
medida registrado y completo; si no, ERROR («origen no registrado» si el `origen_id` esta vacio o no
existe, «origen sin referencia» si al origen le falta un dato de su referencia obligatoria). El
modelo acepta ambos casos: es esta regla la que los valida (RF-44, UC-13a). ADVERTENCIA si ese origen es un supuesto, si el punto declara su
altura pendiente (`especificaciones["altura"] == "pendiente"`) o si un segmento vigente tiene
diametro o empotrado fijados a mano. Una sobrescritura huerfana no produce cantidad: es de R9.

**R9** (siempre ERROR), en este orden: 1. punto o fuente fuera de su ambiente (`Espacio.validar`,
tolerancia de §6.1; una altura de punto sobre el techo es esto mismo y se informa una vez);
2. un recorrido con una altura de vertice mayor que la del ambiente; 3. un recorrido mas corto que
la distancia ortogonal minima entre sus extremos; 4. segmentos solapados con empotrado distinto sin
declarar; 5. sobrescrituras de segmento huerfanas.
"""

from __future__ import annotations

from decimal import Decimal

from adapters.espacio.geometria import (
    longitud_tramos,
    normalizar_diametro,
    unir_segmentos,
)
from adapters.espacio.modelo import TOLERANCIA, Ambiente, Espacio, Recorrido
from adapters.espacio.origen import clave_esp
from core.contracts.presupuesto import Presupuesto
from core.contracts.verificacion import Hallazgo, ReglaVerificacion, Severidad

__all__ = [
    "ALTURA_PENDIENTE",
    "CODIGO_R8",
    "CODIGO_R9",
    "CoherenciaEspacial",
    "OrigenDeLaMedida",
    "reglas_espacio",
]

CODIGO_R8 = "R8"
CODIGO_R9 = "R9"

#: Convencion de la altura pendiente: un punto cuya especificacion `altura` vale `pendiente`
#: (p. ej. un punto importado de un plano sin la altura cargada, SF5). No es un campo del modelo.
ALTURA_PENDIENTE = ("altura", "pendiente")

_TABLA_SEGMENTOS = "esp_segmentos"


def _n(valor: Decimal) -> str:
    """Un decimal tal cual, sin ceros de relleno ni notacion cientifica (mensajes deterministas)."""
    return format(valor.normalize(), "f")


def _hallazgo(
    regla: str,
    severidad: Severidad,
    origen: str,
    descripcion: str,
    observado: Decimal | None = None,
    esperado: Decimal | None = None,
) -> Hallazgo:
    return Hallazgo(
        regla=regla,
        severidad=severidad,
        descripcion=descripcion,
        origen_ids=(origen,),
        valor_observado=observado,
        valor_esperado=esperado,
    )


def _clave_segmento(clave: str) -> str:
    return clave_esp(_TABLA_SEGMENTOS, clave)


# --- R8 -----------------------------------------------------------------------------------


def _hallazgos_r8(espacio: Espacio) -> list[Hallazgo]:
    origenes = {o.id: o for o in espacio.origenes}
    hallazgos: list[Hallazgo] = []
    filas = (
        [("esp_ambientes", "ambiente", a.id, a.origen_id, False) for a in espacio.ambientes]
        + [("esp_fuentes", "fuente", f.id, f.origen_id, False) for f in espacio.fuentes]
        + [
            ("esp_puntos", "punto", p.id, p.origen_id, ALTURA_PENDIENTE in p.especificaciones)
            for p in espacio.puntos
        ]
    )
    for tabla, que, id_, origen_id, pendiente in filas:
        clave, quien = clave_esp(tabla, id_), f"{que} {id_}"
        origen = origenes.get(str(origen_id).strip())
        if origen is None:
            hallazgos.append(
                _hallazgo(
                    CODIGO_R8,
                    Severidad.ERROR,
                    clave,
                    f"{quien}: origen no registrado (origen_id {origen_id!r})",
                )
            )
            continue
        if origen.incompleto:
            faltan = ", ".join(f"«{c}»" for c in origen.faltantes)
            hallazgos.append(
                _hallazgo(
                    CODIGO_R8,
                    Severidad.ERROR,
                    clave,
                    f"{quien}: origen sin referencia (origen {origen.id}: falta {faltan})",
                )
            )
        elif origen.es_supuesto:
            motivo = dict(origen.referencia).get("motivo", "")
            hallazgos.append(
                _hallazgo(
                    CODIGO_R8,
                    Severidad.ADVERTENCIA,
                    clave,
                    f"{quien}: la medida es un supuesto declarado (origen {origen.id}: {motivo})",
                )
            )
        if pendiente:
            hallazgos.append(
                _hallazgo(
                    CODIGO_R8,
                    Severidad.ADVERTENCIA,
                    clave,
                    f"{quien}: altura pendiente; la medida vertical es provisional",
                )
            )
    vigentes = {s.clave for s in unir_segmentos(espacio)}
    for s in espacio.sobrescrituras:
        if s.clave not in vigentes:
            continue
        partes = []
        if s.diametro is not None:
            partes.append(f"diametro {normalizar_diametro(s.diametro)}")
        if s.empotrado is not None:
            partes.append(f"empotrado {'si' if s.empotrado else 'no'}")
        detalle = f" ({', '.join(partes)})" if partes else ""
        hallazgos.append(
            _hallazgo(
                CODIGO_R8,
                Severidad.ADVERTENCIA,
                _clave_segmento(s.clave),
                f"segmento {s.clave}: fijado a mano{detalle}",
            )
        )
    return hallazgos


class OrigenDeLaMedida(ReglaVerificacion):
    """R8: toda fila que produce una cantidad cita su origen de medida; supuestos, alturas
    pendientes y sobrescrituras a mano se marcan (spec §8.2)."""

    codigo = CODIGO_R8
    nombre = "Origen de la medida"

    def __init__(self, espacio: Espacio) -> None:
        self.espacio = espacio

    def evaluar(self, presupuesto: Presupuesto) -> list[Hallazgo]:
        return _hallazgos_r8(self.espacio)


# --- R9 -----------------------------------------------------------------------------------


def _ambientes_del_recorrido(espacio: Espacio, r: Recorrido) -> list[Ambiente]:
    """Ambientes que acotan la altura de un recorrido: los de sus puntos y su fuente."""
    ambientes = {a.id: a for a in espacio.ambientes}
    puntos = {p.id: p for p in espacio.puntos}
    fuentes = {f.id: f for f in espacio.fuentes}
    ids: set[str] = set()
    if r.punto_id is not None and r.punto_id in puntos:
        p = puntos[r.punto_id]
        ids.add(p.ambiente_id)
        if p.fuente_id in fuentes:
            ids.add(fuentes[p.fuente_id].ambiente_id)
    if r.circuito_id is not None:
        circuito = next((c for c in espacio.circuitos if c.id == r.circuito_id), None)
        if circuito is not None:
            ids.update(puntos[i].ambiente_id for i in circuito.orden if i in puntos)
            if circuito.tablero in fuentes:
                ids.add(fuentes[circuito.tablero].ambiente_id)
    return [ambientes[i] for i in sorted(ids) if i in ambientes]


def _hallazgos_r9(espacio: Espacio) -> list[Hallazgo]:
    hallazgos = [
        _hallazgo(CODIGO_R9, Severidad.ERROR, clave, mensaje)
        for clave, mensaje in espacio.validar()
    ]
    con_tramos = [r for r in espacio.recorridos if r.tramos]

    for r in con_tramos:  # 2. alturas
        candidatos = _ambientes_del_recorrido(espacio, r)
        if not candidatos:
            continue
        techo = min(candidatos, key=lambda a: (-a.alto, a.id))
        mas_alta = max(v.z for t in r.tramos for v in t.vertices)
        if mas_alta > techo.alto + TOLERANCIA:
            hallazgos.append(
                _hallazgo(
                    CODIGO_R9,
                    Severidad.ERROR,
                    clave_esp("esp_recorridos", r.id),
                    f"recorrido {r.id}: la altura {_n(mas_alta)} supera la del ambiente "
                    f"{techo.id} ({_n(techo.alto)})",
                    observado=mas_alta,
                    esperado=techo.alto,
                )
            )

    for r in con_tramos:  # 3. recorrido mas corto que la distancia ortogonal minima
        a, b = r.tramos[0].vertices[0], r.tramos[-1].vertices[-1]
        minima = abs(b.x - a.x) + abs(b.y - a.y) + abs(b.z - a.z)
        longitud = longitud_tramos(r.tramos)
        if longitud < minima:
            hallazgos.append(
                _hallazgo(
                    CODIGO_R9,
                    Severidad.ERROR,
                    clave_esp("esp_recorridos", r.id),
                    f"recorrido {r.id}: longitud {_n(longitud)} menor que la distancia ortogonal "
                    f"minima {_n(minima)} entre sus extremos",
                    observado=longitud,
                    esperado=minima,
                )
            )

    segmentos = unir_segmentos(espacio)
    for s in segmentos:  # 4. empotrado en conflicto
        if s.conflicto_empotrado:
            hallazgos.append(
                _hallazgo(
                    CODIGO_R9,
                    Severidad.ERROR,
                    _clave_segmento(s.clave),
                    f"segmento {s.clave}: tramos solapados con empotrado distinto sin declarar",
                )
            )

    vigentes = {s.clave for s in segmentos}
    for sobre in espacio.sobrescrituras:  # 5. sobrescrituras huerfanas
        if sobre.clave not in vigentes:
            hallazgos.append(
                _hallazgo(
                    CODIGO_R9,
                    Severidad.ERROR,
                    _clave_segmento(sobre.clave),
                    f"sobrescritura del segmento {sobre.clave}: ningun segmento vigente tiene "
                    "esa clave",
                )
            )
    return hallazgos


class CoherenciaEspacial(ReglaVerificacion):
    """R9: la geometria declarada es coherente con los ambientes y con los segmentos que la unen
    (spec §8.2)."""

    codigo = CODIGO_R9
    nombre = "Coherencia espacial"

    def __init__(self, espacio: Espacio) -> None:
        self.espacio = espacio

    def evaluar(self, presupuesto: Presupuesto) -> list[Hallazgo]:
        return _hallazgos_r9(self.espacio)


def reglas_espacio(espacio: Espacio) -> tuple[ReglaVerificacion, ...]:
    """R8 y R9 sobre la instantanea `espacio`, listas para `elaborar(reglas=REGLAS + ...)`.

    R10 (limites de la especialidad) llega con SF2 y se agregara aqui.
    """
    return (OrigenDeLaMedida(espacio), CoherenciaEspacial(espacio))
