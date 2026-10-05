"""Reglas de auditoria del espacio: R8 (origen de la medida), R9 (coherencia espacial) y R10
(limites de la especialidad), spec §8.2.

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
modelo acepta ambos casos: es esta regla la que los valida (RF-44, UC-13a). ADVERTENCIA si ese
origen es un supuesto, si el punto declara su altura pendiente (`especificaciones["altura"] ==
"pendiente"`), si un ambiente importado de un plano conserva su alto provisional, si la fila
ya no esta en el plano de donde vino (SF5), si un circuito importado de un plano conserva los
conductores y puntos maximos SUPUESTOS (RS-17: origen SUPUESTO ligado al circuito por su referencia;
deja de avisar cuando el usuario los declara) o si un segmento vigente tiene diametro o empotrado
fijados a mano. Una sobrescritura huerfana no produce cantidad: es de R9.

**R9** (siempre ERROR), en este orden: 1. punto o fuente fuera de su ambiente (`Espacio.validar`,
tolerancia de §6.1; una altura de punto sobre el techo es esto mismo y se informa una vez);
2. un recorrido con una altura de vertice mayor que la del ambiente; 3. un recorrido mas corto que
la distancia ortogonal minima entre los extremos de su camino (los de los tramos encadenados, no
los de la lista; sin camino, sin extremos, no se compara); 4. segmentos solapados con empotrado
distinto sin declarar; 5. sobrescrituras de segmento huerfanas. Un recorrido en diagonal (mas corto
que la distancia ortogonal) es ERROR.

**R10**, en este orden: 1. pendiente del drenaje: un tramo de un recorrido de drenaje que declara su
pendiente (fraccion, positiva si baja hacia el colector) por debajo de la minima; un tramo sin
pendiente declarada no se evalua (la propuesta de §6.4 no la trae); 2. enlace de datos: recorrido
mas holguras (`datos.longitud_enlace`, sin la reserva) mayor que 90 m; 3. puntos por circuito: mas
puntos (los que citan el circuito mas los de su orden) que el maximo declarado. Severidad: ERROR si
la fuente del limite esta verificada, ADVERTENCIA si es un supuesto declarado (hoy los tres lo son).
Cada limite es una `Constante` de su especialidad; `Limites` los junta para probar ambos casos.
Limitacion (pendiente): R10 evalua solo tramos de drenaje que declaran su pendiente; el recorrido
propuesto de §6.4 no la trae, asi que con recorridos propuestos la condicion 1 no se dispara.
Decision (puntos por circuito, R10d): el maximo lo declara el usuario en cada circuito, pero la
severidad sigue a la fuente del limite base (`LIMITE_PUNTOS_POR_CIRCUITO`): mientras esa fuente sea
supuesta (RS-11, pendiente de ratificar por Eugenio) un exceso es ADVERTENCIA, no ERROR.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from adapters.espacio.especialidades import Constante
from adapters.espacio.especialidades.agua import LIMITE_PENDIENTE_DRENAJE
from adapters.espacio.especialidades.datos import LIMITE_ENLACE, longitud_enlace
from adapters.espacio.especialidades.electricidad import LIMITE_PUNTOS_POR_CIRCUITO
from adapters.espacio.geometria import (
    _agrupar_nodos,
    longitud_tramos,
    normalizar_diametro,
    unir_segmentos,
)
from adapters.espacio.modelo import (
    TOLERANCIA,
    Ambiente,
    Circuito,
    Coord,
    Espacio,
    Recorrido,
    TipoPunto,
    Tramo,
)
from adapters.espacio.origen import OrigenMedida, TipoOrigen, clave_esp
from core.contracts.presupuesto import Presupuesto
from core.contracts.verificacion import Hallazgo, ReglaVerificacion, Severidad

__all__ = [
    "ALTO_PROVISIONAL",
    "ALTURA_PENDIENTE",
    "CODIGO_R8",
    "CODIGO_R10",
    "CODIGO_R9",
    "CLAVE_CIRCUITO_SUPUESTO",
    "CoherenciaEspacial",
    "Limites",
    "LimitesDeEspecialidad",
    "ORIGEN_ALTURA_PENDIENTE",
    "ORIGEN_DESAPARECIDA",
    "OrigenDeLaMedida",
    "circuito_supuesto",
    "origen_circuito_supuesto",
    "reglas_espacio",
]

CODIGO_R8 = "R8"
CODIGO_R9 = "R9"
CODIGO_R10 = "R10"

#: Convencion de la altura pendiente: un punto cuya especificacion `altura` vale `pendiente`
#: (p. ej. un punto importado de un plano sin la altura cargada, SF5). No es un campo del modelo.
ALTURA_PENDIENTE = ("altura", "pendiente")

#: Marcas que la importacion de planos (SF5) deja en la REFERENCIA del origen de una fila. El modelo
#: no tiene campo para ellas (`Ambiente.alto` es obligatorio y las filas no tienen estado):
#: viven en el
#: origen, que ya se guarda con sus pares clave-valor.
#: «altura pendiente» (un ambiente importado de un DXF) vale mientras su alto siga siendo el
#: provisional.
ORIGEN_ALTURA_PENDIENTE = ("altura", "pendiente")
#: «desaparecida»: la fila vino de un plano y la ultima reimportacion ya no la trae (no se borra).
ORIGEN_DESAPARECIDA = ("importacion", "desaparecida")
#: Alto con que entra un ambiente cuyo plano no dice su altura. SUPUESTO_DECLARADO (RS-SF5-1):
#: 2,5 m es el alto de OF-001 (memoria `of001.md`); sin fuente normativa. R8 lo marca hasta
#: que se cargue el real.
ALTO_PROVISIONAL = Decimal("2.5")

#: Clave de la referencia de un origen SUPUESTO que ata el supuesto a un circuito (SF5, RS-17): el
#: circuito importado de un plano con conductores y puntos maximos que el plano no trae. `Circuito`
#: no tiene origen; el supuesto vive en un origen de `Espacio.origenes` (no en `parametros`,
#: DA-SF-8).
CLAVE_CIRCUITO_SUPUESTO = "circuito"

_TABLA_SEGMENTOS = "esp_segmentos"


def _n(valor: Decimal) -> str:
    """Un decimal tal cual, sin ceros de relleno ni notacion cientifica (mensajes deterministas)."""
    return format(valor.normalize(), "f")


def _hallazgo(
    regla: str,
    severidad: Severidad,
    origen: str | tuple[str, ...],
    descripcion: str,
    observado: Decimal | None = None,
    esperado: Decimal | None = None,
) -> Hallazgo:
    return Hallazgo(
        regla=regla,
        severidad=severidad,
        descripcion=descripcion,
        origen_ids=(origen,) if isinstance(origen, str) else tuple(origen),
        valor_observado=observado,
        valor_esperado=esperado,
    )


def _clave_segmento(clave: str) -> str:
    return clave_esp(_TABLA_SEGMENTOS, clave)


def _conductores_texto(conductores: tuple[int, int, int]) -> str:
    return "-".join(str(c) for c in conductores)


def origen_circuito_supuesto(
    circuito: Circuito, fuentes: tuple[str, ...], motivo: str
) -> OrigenMedida:
    """El origen SUPUESTO que marca los valores supuestos (conductores y puntos maximos) de un
    circuito importado. Guarda los valores supuestos: la marca vale mientras el circuito los
    conserve. `fuentes`: los `id` de las constantes declaradas (p. ej. `SF5-1`, `SF5-2`)."""
    return OrigenMedida(
        id=f"SUP-CIR-{circuito.id}",
        tipo=TipoOrigen.SUPUESTO,
        referencia=(
            ("motivo", motivo),
            (CLAVE_CIRCUITO_SUPUESTO, circuito.id),
            ("conductores", _conductores_texto(circuito.conductores)),
            ("puntos_maximos", str(circuito.puntos_maximos)),
            ("constantes", ", ".join(fuentes)),
        ),
    )


def circuito_supuesto(origen: OrigenMedida, circuito: Circuito) -> bool:
    """True si `origen` marca a `circuito` con supuestos y el circuito aun los conserva."""
    if origen.tipo is not TipoOrigen.SUPUESTO:
        return False
    ref = dict(origen.referencia)
    return (
        ref.get(CLAVE_CIRCUITO_SUPUESTO) == circuito.id
        and ref.get("conductores") == _conductores_texto(circuito.conductores)
        and ref.get("puntos_maximos") == str(circuito.puntos_maximos)
    )


# --- R8 -----------------------------------------------------------------------------------


def _hallazgos_r8(espacio: Espacio) -> list[Hallazgo]:
    origenes = {o.id: o for o in espacio.origenes}
    altos = {a.id: a.alto for a in espacio.ambientes}
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
        if tabla == "esp_ambientes":
            # importado de un plano sin altura: pendiente mientras siga el alto provisional
            pendiente = ORIGEN_ALTURA_PENDIENTE in origen.referencia and (
                altos[id_] == ALTO_PROVISIONAL
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
        if ORIGEN_DESAPARECIDA in origen.referencia:
            hallazgos.append(
                _hallazgo(
                    CODIGO_R8,
                    Severidad.ADVERTENCIA,
                    clave,
                    f"{quien}: ya no esta en el plano (origen {origen.id}); revisarla o retirarla",
                )
            )
    for c in espacio.circuitos:  # RS-17: circuito importado con valores supuestos sin declarar
        marca = next((o for o in espacio.origenes if circuito_supuesto(o, c)), None)
        if marca is not None:
            constantes = dict(marca.referencia).get("constantes", "")
            hallazgos.append(
                _hallazgo(
                    CODIGO_R8,
                    Severidad.ADVERTENCIA,
                    clave_esp("esp_circuitos", c.id),
                    f"circuito {c.id}: circuito importado con conductores y puntos supuestos "
                    f"({_conductores_texto(c.conductores)} y {c.puntos_maximos} puntos maximos; "
                    f"{constantes}); declarelos en la hoja",
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


def _extremos_del_camino(tramos: tuple[Tramo, ...]) -> tuple[Coord, Coord] | None:
    """Los dos extremos del camino que forman `tramos`, o `None` si no forman un camino.

    Si encadenan en el orden declarado (cada tramo empieza a TOLERANCIA o menos de donde termino el
    anterior) son el inicio del primero y el fin del ultimo. Si no (el `orden` no sigue la
    geometria), se encadenan por sus extremos: un camino tiene exactamente dos nodos de grado impar
    y una sola componente. Un recorrido ramificado, cerrado o partido no tiene extremos: R9 no le
    exige distancia ortogonal minima (ruling SF1, ledger)."""
    if all(
        a.vertices[-1].distancia(b.vertices[0]) <= TOLERANCIA
        for a, b in zip(tramos, tramos[1:], strict=False)
    ):
        return tramos[0].vertices[0], tramos[-1].vertices[-1]
    rep = _agrupar_nodos(c for t in tramos for c in (t.vertices[0], t.vertices[-1]))
    grado: dict[Coord, int] = {}
    padre: dict[Coord, Coord] = {n: n for n in set(rep.values())}

    def raiz(n: Coord) -> Coord:
        while padre[n] != n:
            n = padre[n]
        return n

    for t in tramos:
        a, b = rep[t.vertices[0]], rep[t.vertices[-1]]
        grado[a] = grado.get(a, 0) + 1
        grado[b] = grado.get(b, 0) + 1
        padre[raiz(a)] = raiz(b)
    impares = [n for n, g in grado.items() if g % 2]
    if len(impares) != 2 or len({raiz(n) for n in grado}) != 1:
        return None
    return impares[0], impares[1]


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
        extremos = _extremos_del_camino(r.tramos)
        if extremos is None:
            continue
        a, b = extremos
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


# --- R10 ----------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Limites:
    """Los tres limites de R10, cada uno con su fuente (una `Constante` de su especialidad)."""

    pendiente_minima: Constante
    enlace_maximo: Constante
    puntos_por_circuito: Constante

    @classmethod
    def por_defecto(cls) -> Limites:
        return cls(LIMITE_PENDIENTE_DRENAJE, LIMITE_ENLACE, LIMITE_PUNTOS_POR_CIRCUITO)


def _severidad_del_limite(limite: Constante) -> Severidad:
    """ERROR si el limite tiene fuente verificada; ADVERTENCIA si es un supuesto declarado."""
    return Severidad.ADVERTENCIA if limite.supuesto_declarado else Severidad.ERROR


def _hallazgos_r10(espacio: Espacio, limites: Limites) -> list[Hallazgo]:
    hallazgos: list[Hallazgo] = []
    puntos = {p.id: p for p in espacio.puntos}

    minima = Decimal(limites.pendiente_minima.valor)
    gravedad = _severidad_del_limite(limites.pendiente_minima)
    for r in espacio.recorridos:  # 1. pendiente del drenaje
        punto = puntos.get(r.punto_id) if r.punto_id is not None else None
        if punto is None or punto.tipo is not TipoPunto.DRENAJE:
            continue
        for t in r.tramos:
            if t.pendiente is not None and t.pendiente < minima:
                hallazgos.append(
                    _hallazgo(
                        CODIGO_R10,
                        gravedad,
                        (clave_esp("esp_recorridos", r.id), clave_esp("esp_puntos", punto.id)),
                        f"recorrido {r.id}: pendiente {_n(t.pendiente)} del tramo {t.orden} menor "
                        f"que la minima {_n(minima)} del drenaje "
                        f"(limite: {limites.pendiente_minima.fuente})",
                        observado=t.pendiente,
                        esperado=minima,
                    )
                )

    maximo = Decimal(limites.enlace_maximo.valor)
    gravedad = _severidad_del_limite(limites.enlace_maximo)
    for p in espacio.puntos:  # 2. enlace de datos
        enlace = longitud_enlace(espacio, p)
        if enlace is not None and enlace > maximo:
            hallazgos.append(
                _hallazgo(
                    CODIGO_R10,
                    gravedad,
                    clave_esp("esp_puntos", p.id),
                    f"punto {p.id}: enlace de {_n(enlace)} m mayor que el maximo de {_n(maximo)} m "
                    f"(recorrido mas holguras; limite: {limites.enlace_maximo.fuente})",
                    observado=enlace,
                    esperado=maximo,
                )
            )

    gravedad = _severidad_del_limite(limites.puntos_por_circuito)
    for c in espacio.circuitos:  # 3. puntos por circuito
        ids = sorted({p.id for p in espacio.puntos if p.circuito_id == c.id} | set(c.orden))
        if len(ids) > c.puntos_maximos:
            hallazgos.append(
                _hallazgo(
                    CODIGO_R10,
                    gravedad,
                    (clave_esp("esp_circuitos", c.id), *(clave_esp("esp_puntos", i) for i in ids)),
                    f"circuito {c.id}: {len(ids)} puntos, mas que el maximo declarado de "
                    f"{c.puntos_maximos} (limite: {limites.puntos_por_circuito.fuente})",
                    observado=Decimal(len(ids)),
                    esperado=Decimal(c.puntos_maximos),
                )
            )
    return hallazgos


class LimitesDeEspecialidad(ReglaVerificacion):
    """R10: pendiente minima del drenaje, 90 m por enlace de datos y puntos por circuito
    (spec §8.2). ERROR si el limite tiene fuente verificada, ADVERTENCIA si es supuesto."""

    codigo = CODIGO_R10
    nombre = "Límites de la especialidad"

    def __init__(self, espacio: Espacio, limites: Limites | None = None) -> None:
        self.espacio = espacio
        self.limites = limites if limites is not None else Limites.por_defecto()

    def evaluar(self, presupuesto: Presupuesto) -> list[Hallazgo]:
        return _hallazgos_r10(self.espacio, self.limites)


def reglas_espacio(espacio: Espacio) -> tuple[ReglaVerificacion, ...]:
    """R8, R9 y R10 sobre la instantanea `espacio`, listas para `elaborar(reglas=REGLAS + ...)`."""
    return (OrigenDeLaMedida(espacio), CoherenciaEspacial(espacio), LimitesDeEspecialidad(espacio))
