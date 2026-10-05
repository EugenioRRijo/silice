"""Resultado de una importacion de plano, su informe y la reimportacion (spec §6.6, RF-50 y RF-51).

`ResultadoImportacion` junta las filas que el plano crea en la hoja (con su origen DXF o IFC) y el
**informe de importacion**: ítems tipados de lo importado, lo no reconocido, lo aproximado y lo que
queda pendiente. Lo que no sigue la convencion va al informe y no se adivina.

`fusionar` es la reimportacion del mismo plano (UC-04, 2a): empareja las filas por el
identificador de su origen (*handle* del DXF o `GlobalId` del IFC) DENTRO de un mismo archivo
(un archivo con otro nombre es otro plano), actualiza las que siguen, agrega las nuevas y
**marca** las que desaparecieron (`ORIGEN_DESAPARECIDA` en la referencia del origen, que R8
convierte en ADVERTENCIA): no las borra.

Decisiones (bitacora SF, SF5):

* Una fila emparejada conserva su `id` (otras filas la citan) y su `origen_id`; cambia el resto.
* Un ambiente emparejado conserva la altura ya cargada si el plano no la trae (la provisional).
* Los circuitos no vienen de una entidad con origen: los existentes se conservan tal cual (el
  usuario
  edita su orden y su maximo) y solo se agregan los nuevos.
* Un recorrido declarado no tiene origen en el modelo: se empareja por su `id` (`REC-<handle>`) y,
  si desaparece, solo se informa; no se puede marcar.
* Una fila nueva cuyo `id` ya usa otra fila de la hoja (por ejemplo una escrita a mano) se OMITE con
  su ítem; tambien las filas que la citan.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from decimal import Decimal
from enum import StrEnum

from adapters.espacio.modelo import Ambiente, Circuito, Espacio, Fuente, Punto, Recorrido
from adapters.espacio.origen import OrigenMedida, TipoOrigen
from adapters.espacio.reglas import ALTO_PROVISIONAL, ORIGEN_ALTURA_PENDIENTE, ORIGEN_DESAPARECIDA

__all__ = [
    "EstadoImportacion",
    "ItemInforme",
    "ResultadoImportacion",
    "TABLAS",
    "TipoItem",
    "cargar_alturas",
    "fusionar",
]

#: Las tablas `esp_*` que una importacion puede llenar, en el orden de `ResultadoImportacion.filas`.
TABLAS = (
    "esp_origenes",
    "esp_ambientes",
    "esp_fuentes",
    "esp_circuitos",
    "esp_puntos",
    "esp_recorridos",
)

#: Prefijo de los `id` de los recorridos declarados que crea la importacion de DXF (`REC-<handle>`).
PREFIJO_RECORRIDO_DXF = "REC-"


class EstadoImportacion(StrEnum):
    IMPORTADA = "importada"
    DETENIDA = (
        "detenida"  # falta un dato que solo el usuario sabe (la unidad); se reanuda con el dato
    )
    RECHAZADA = "rechazada"  # el archivo no se puede leer (malformado, demasiado grande, esquema)


class TipoItem(StrEnum):
    IMPORTADO = "importado"
    NO_RECONOCIDO = "no reconocido"
    APROXIMADO = "aproximado"
    PENDIENTE = "pendiente"
    DESAPARECIDO = "desaparecido"  # solo en la reimportacion
    OMITIDO = "omitido"  # solo en la reimportacion


@dataclass(frozen=True, slots=True)
class ItemInforme:
    """Una linea del informe. `tabla`: tabla `esp_*` de la fila o, para lo no reconocido, la capa o
    la clase IFC. `referencia`: *handle* o `GlobalId` en el plano. `fila`: `id` en la hoja."""

    tipo: TipoItem
    tabla: str
    referencia: str
    fila: str
    mensaje: str


@dataclass(frozen=True, slots=True)
class ResultadoImportacion:
    """Lo que un plano deja: filas por tabla del espacio y el informe. Inmutable."""

    formato: str  # "dxf" o "ifc"
    archivo: str
    estado: EstadoImportacion = EstadoImportacion.IMPORTADA
    mensaje: str = ""
    pide_unidad: bool = False
    origenes: tuple[OrigenMedida, ...] = ()
    ambientes: tuple[Ambiente, ...] = ()
    fuentes: tuple[Fuente, ...] = ()
    circuitos: tuple[Circuito, ...] = ()
    puntos: tuple[Punto, ...] = ()
    recorridos: tuple[Recorrido, ...] = ()
    informe: tuple[ItemInforme, ...] = ()

    @property
    def filas(self) -> dict[str, int]:
        """Cuantas filas crea la importacion en cada tabla."""
        n = (len(self.origenes), len(self.ambientes), len(self.fuentes))
        m = (len(self.circuitos), len(self.puntos), len(self.recorridos))
        return dict(zip(TABLAS, (*n, *m), strict=True))

    @property
    def conteos(self) -> dict[TipoItem, int]:
        """Items del informe por tipo (todos los tipos, con 0 si no hay)."""
        cuenta = dict.fromkeys(TipoItem, 0)
        for item in self.informe:
            cuenta[item.tipo] += 1
        return cuenta

    @property
    def origenes_por_id(self) -> dict[str, OrigenMedida]:
        return {o.id: o for o in self.origenes}

    def espacio(self) -> Espacio:
        """Las filas como un `Espacio` (vacio si la importacion se detuvo o se rechazo)."""
        return Espacio(
            origenes=self.origenes,
            ambientes=self.ambientes,
            fuentes=self.fuentes,
            circuitos=self.circuitos,
            puntos=self.puntos,
            recorridos=self.recorridos,
        )


def _sin_marca(origen: OrigenMedida, marca: tuple[str, str]) -> OrigenMedida:
    """El origen sin la marca `(clave, valor)` en su referencia (si la tenia)."""
    return replace(origen, referencia=tuple(par for par in origen.referencia if par != marca))


def _con_marca(origen: OrigenMedida, marca: tuple[str, str]) -> OrigenMedida:
    if marca in origen.referencia:
        return origen
    return replace(
        origen,
        referencia=tuple(par for par in origen.referencia if par[0] != marca[0]) + (marca,),
    )


def cargar_alturas(
    resultado: ResultadoImportacion, alturas: Mapping[str, Decimal]
) -> ResultadoImportacion:
    """Carga la altura de los ambientes cuyo `id` esta en `alturas` (metros) y les quita la marca de
    pendiente (en su origen y en el informe). Un `id` que no existe se ignora. No muta el
    original."""
    cargados = {a.id for a in resultado.ambientes if a.id in alturas}
    if not cargados:
        return resultado
    ambientes = tuple(
        replace(a, alto=alturas[a.id]) if a.id in cargados else a for a in resultado.ambientes
    )
    de_ambientes = {a.origen_id for a in resultado.ambientes if a.id in cargados}
    origenes = tuple(
        _sin_marca(o, ORIGEN_ALTURA_PENDIENTE) if o.id in de_ambientes else o
        for o in resultado.origenes
    )
    informe = tuple(
        i
        for i in resultado.informe
        if not (i.tipo is TipoItem.PENDIENTE and i.tabla == "esp_ambientes" and i.fila in cargados)
    )
    return replace(resultado, ambientes=ambientes, origenes=origenes, informe=informe)


def _identificador(origen: OrigenMedida | None) -> str | None:
    """Lo que identifica la entidad en el plano: *handle* (DXF) o `GlobalId` (IFC)."""
    if origen is None:
        return None
    referencia = dict(origen.referencia)
    return referencia.get("handle") or referencia.get("global_id") or None


class _Fusion:
    """Estado de una fusion: lo que ya hay, lo que queda y el informe."""

    def __init__(self, actual: Espacio, resultado: ResultadoImportacion) -> None:
        self.actual = actual
        self.resultado = resultado
        self.tipo_origen = TipoOrigen(resultado.formato)
        self.origenes = {o.id: o for o in actual.origenes}
        self.nuevos = resultado.origenes_por_id
        self.filas: dict[str, dict[str, object]] = {
            "esp_ambientes": {a.id: a for a in actual.ambientes},
            "esp_fuentes": {f.id: f for f in actual.fuentes},
            "esp_puntos": {p.id: p for p in actual.puntos},
        }
        self.ids: dict[str, dict[str, str]] = {t: {} for t in (*self.filas, "esp_circuitos")}
        self.circuitos = {c.id: c for c in actual.circuitos}
        self.recorridos = {r.id: r for r in actual.recorridos}
        self.informe: list[ItemInforme] = list(resultado.informe)

    def _item(self, tipo: TipoItem, tabla: str, referencia: str, fila: str, mensaje: str) -> None:
        self.informe.append(ItemInforme(tipo, tabla, referencia, fila, mensaje))

    def _en_alcance(self, fila) -> str | None:
        """Identificador en el plano de una fila que vino de ESTE archivo; si no, None."""
        origen = self.origenes.get(fila.origen_id)
        if origen is None or origen.tipo is not self.tipo_origen:
            return None
        if dict(origen.referencia).get("archivo") != self.resultado.archivo:
            return None
        return _identificador(origen)

    def _origen_libre(self, origen: OrigenMedida) -> OrigenMedida:
        """El origen con un `id` que no use otro (dos archivos pueden compartir un *handle*)."""
        id_ = origen.id
        n = 1
        while id_ in self.origenes:
            n += 1
            id_ = f"{origen.id}~{n}"
        return replace(origen, id=id_)

    def _remapear(self, fila, tabla: str):
        """La fila con sus referencias traducidas a los `id` finales; None si cita una omitida."""
        cambios: dict[str, str | None] = {}
        for campo, tabla_citada in _REFERENCIAS.get(tabla, ()):
            citado = getattr(fila, campo)
            if citado is None:
                continue
            final = self.ids[tabla_citada].get(citado)
            if final is None:
                return None, f"cita {citado!r}, que se omitio"
            cambios[campo] = final
        return (replace(fila, **cambios) if cambios else fila), ""

    def _tabla(self, tabla: str, nuevas, es_ambiente=False, es_punto=False) -> None:
        existentes: dict[str, object] = {}
        for fila in self.filas[tabla].values():
            clave = self._en_alcance(fila)
            if clave is not None:
                existentes[clave] = fila
        emparejadas: set[str] = set()
        for nueva in nuevas:
            origen_nuevo = self.nuevos.get(nueva.origen_id)
            clave = _identificador(origen_nuevo)
            fila_ref, motivo = self._remapear(nueva, tabla)
            if fila_ref is None:
                self._item(TipoItem.OMITIDO, tabla, clave or "", nueva.id, f"{nueva.id}: {motivo}")
                continue
            previa = existentes.get(clave) if clave else None
            if previa is not None:
                emparejadas.add(clave)
                self._actualizar(
                    tabla, nueva, fila_ref, previa, origen_nuevo, es_ambiente, es_punto
                )
            elif nueva.id in self.filas[tabla]:
                self._item(
                    TipoItem.OMITIDO,
                    tabla,
                    clave or "",
                    nueva.id,
                    f"{nueva.id}: su id ya lo usa otra fila de la hoja",
                )
            else:
                origen = self._origen_libre(origen_nuevo)
                self.origenes[origen.id] = origen
                self.filas[tabla][nueva.id] = replace(fila_ref, origen_id=origen.id)
                self.ids[tabla][nueva.id] = nueva.id
                self._item(
                    TipoItem.IMPORTADO, tabla, clave or "", nueva.id, f"{nueva.id}: agregada"
                )
        for clave, fila in existentes.items():
            if clave in emparejadas:
                continue
            origen = self.origenes[fila.origen_id]
            self.origenes[origen.id] = _con_marca(origen, ORIGEN_DESAPARECIDA)
            self._item(
                TipoItem.DESAPARECIDO,
                tabla,
                clave,
                fila.id,
                f"{fila.id}: ya no esta en el plano; se conserva marcada",
            )

    def _actualizar(self, tabla, nueva, fila_ref, previa, origen_nuevo, es_ambiente, es_punto):
        origen = replace(origen_nuevo, id=previa.origen_id)
        final = replace(fila_ref, id=previa.id, origen_id=previa.origen_id)
        if es_ambiente and ORIGEN_ALTURA_PENDIENTE in origen_nuevo.referencia:
            # el plano no trae altura: se conserva la ya cargada (y deja de estar pendiente)
            final = replace(final, alto=previa.alto)
            if previa.alto != ALTO_PROVISIONAL:
                origen = _sin_marca(origen, ORIGEN_ALTURA_PENDIENTE)
        if es_punto:
            final = replace(
                final,
                fuente_id=final.fuente_id if final.fuente_id is not None else previa.fuente_id,
                circuito_id=final.circuito_id
                if final.circuito_id is not None
                else previa.circuito_id,
            )
        self.origenes[origen.id] = origen
        self.filas[tabla][previa.id] = final
        self.ids[tabla][nueva.id] = previa.id
        clave = _identificador(origen_nuevo)
        self._item(TipoItem.IMPORTADO, tabla, clave or "", previa.id, f"{previa.id}: actualizada")

    def _circuitos(self) -> None:
        for c in self.resultado.circuitos:
            if c.id in self.circuitos:
                self.ids["esp_circuitos"][c.id] = c.id  # el existente manda (se edita en la hoja)
                continue
            tablero = self.ids["esp_fuentes"].get(c.tablero, c.tablero)
            self.circuitos[c.id] = replace(c, tablero=tablero, orden=())
            self.ids["esp_circuitos"][c.id] = c.id
            self._item(TipoItem.IMPORTADO, "esp_circuitos", "", c.id, f"{c.id}: agregado")

    def _recorridos(self) -> None:
        nuevos = {}
        for r in self.resultado.recorridos:
            punto = None if r.punto_id is None else self.ids["esp_puntos"].get(r.punto_id)
            circuito = (
                None if r.circuito_id is None else self.ids["esp_circuitos"].get(r.circuito_id)
            )
            if (r.punto_id is not None and punto is None) or (
                r.circuito_id is not None and circuito is None
            ):
                self._item(
                    TipoItem.OMITIDO,
                    "esp_recorridos",
                    "",
                    r.id,
                    f"{r.id}: cita una fila que se omitio",
                )
                continue
            final = replace(r, punto_id=punto, circuito_id=circuito)
            existia = r.id in self.recorridos
            self.recorridos[r.id] = final
            nuevos[r.id] = final
            self._item(
                TipoItem.IMPORTADO,
                "esp_recorridos",
                "",
                r.id,
                f"{r.id}: {'actualizado' if existia else 'agregado'}",
            )
        if self.resultado.formato != "dxf":
            return
        for id_ in sorted(self.recorridos):
            if id_.startswith(PREFIJO_RECORRIDO_DXF) and id_ not in nuevos:
                self._item(
                    TipoItem.DESAPARECIDO,
                    "esp_recorridos",
                    "",
                    id_,
                    f"{id_}: ya no esta en el plano; se conserva (un recorrido no lleva marca)",
                )

    def ejecutar(self) -> tuple[Espacio, tuple[ItemInforme, ...]]:
        r = self.resultado
        self._tabla("esp_ambientes", r.ambientes, es_ambiente=True)
        self._tabla("esp_fuentes", r.fuentes)
        self._circuitos()
        self._tabla("esp_puntos", r.puntos, es_punto=True)
        self._recorridos()
        espacio = Espacio(
            origenes=tuple(self.origenes.values()),
            ambientes=tuple(self.filas["esp_ambientes"].values()),
            fuentes=tuple(self.filas["esp_fuentes"].values()),
            circuitos=tuple(self.circuitos.values()),
            puntos=tuple(self.filas["esp_puntos"].values()),
            recorridos=tuple(self.recorridos.values()),
            sobrescrituras=self.actual.sobrescrituras,
        )
        return espacio, tuple(self.informe)


#: Referencias entre filas que hay que traducir: tabla -> ((campo, tabla citada), ...).
_REFERENCIAS: dict[str, tuple[tuple[str, str], ...]] = {
    "esp_fuentes": (("ambiente_id", "esp_ambientes"),),
    "esp_puntos": (
        ("ambiente_id", "esp_ambientes"),
        ("fuente_id", "esp_fuentes"),
        ("circuito_id", "esp_circuitos"),
    ),
}


def fusionar(
    espacio_actual: Espacio, resultado: ResultadoImportacion
) -> tuple[Espacio, tuple[ItemInforme, ...]]:
    """Reimporta un plano sobre la hoja: actualiza, agrega y marca lo que desaparecio.

    Devuelve el espacio resultante y el informe (el del resultado mas lo propio de la fusion). Si la
    importacion se detuvo o se rechazo, el espacio queda igual y el informe lleva su motivo."""
    if resultado.estado is not EstadoImportacion.IMPORTADA:
        motivo = ItemInforme(TipoItem.NO_RECONOCIDO, "", "", "", resultado.mensaje)
        return espacio_actual, (*resultado.informe, motivo)
    return _Fusion(espacio_actual, resultado).ejecutar()
