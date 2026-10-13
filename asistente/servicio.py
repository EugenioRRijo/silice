"""La sesion del asistente tal como la usa la pantalla (S4 §3.1 pasos 5-7), sin Streamlit.

La pantalla guarda UNA `SesionDeAsistente` en `st.session_state`; aceptar, rechazar y el resultado
hipotetico salen de aqui. Rechazar todo deja el borrador identico al de antes de la sesion (9h).
Guardar sigue siendo `ui.hoja.guardar_version`: este modulo solo prepara la fuente que el sistema
prellena («propuesta de IA, sesion N, proveedor/modelo»); el responsable es siempre una persona.
"""

from __future__ import annotations

import copy
from collections import Counter
from dataclasses import dataclass, replace
from decimal import Decimal
from typing import Any

from asistente.catalogo import CatalogoVista
from asistente.orquestador import ResultadoSesion, Servicios, Topes, continuar, ejecutar
from asistente.propuestas import (
    EstadoPropuesta,
    OrigenIA,
    Pendientes,
    Propuesta,
    TipoPropuesta,
    aplicar,
)
from asistente.proveedores.base import ProveedorIA, Tarifa, Uso
from asistente.registro import RegistroIA
from ui import hoja
from ui.hoja import Borrador, HojaInvalida

#: Cota superior por tarea de §8.4: <= 12 turnos; ~10 000 fichas de entrada sin cache, ~6 000 de
#: cache y ~3 000 de salida por turno. El panel la muestra ANTES de enviar.
TURNOS_ESTIMADOS = 12
USO_ESTIMADO_POR_TURNO = Uso(entrada=10_000, salida=3_000, cache_lectura=6_000)


class DependenciaPendiente(HojaInvalida):
    """Se acepto una propuesta que depende de otra que aun no se acepta."""


@dataclass(slots=True)
class SesionDeAsistente:
    resultado: ResultadoSesion
    pendientes: Pendientes
    base: Borrador
    origen: OrigenIA
    catalogo: CatalogoVista
    servicios: Servicios


def estimar_costo(tarifa: Tarifa) -> Decimal:
    """USD de una tarea en el peor caso razonable (§8.4): para el panel, antes de enviar."""
    return tarifa.costo(USO_ESTIMADO_POR_TURNO) * TURNOS_ESTIMADOS


def proponer(
    proveedor: ProveedorIA,
    pedido: str,
    borrador: Borrador,
    servicios: Servicios,
    topes: Topes = Topes(),  # noqa: B008
) -> SesionDeAsistente:
    """Corre el bucle; el borrador NO cambia (RF-32). Devuelve las propuestas pendientes.

    La sesion devuelta NO retiene el proveedor (que lleva la clave de IA y su cliente): la pantalla
    la guarda en su estado y la clave nunca va ahi (§8.3). `responder` recibe el vigente.
    """
    resultado = ejecutar(proveedor, pedido, borrador, servicios, topes)
    _soltar_proveedor(resultado)
    origen = OrigenIA(proveedor.nombre, proveedor.modelo, resultado.sesion)
    return SesionDeAsistente(
        resultado,
        Pendientes(list(resultado.propuestas)),
        borrador,
        origen,
        servicios.catalogo,
        servicios,
    )


_IGUAL: Any = object()  # «no cambiar el registro»: distinto de `None` (sin registro)


def _soltar_proveedor(resultado: ResultadoSesion) -> None:
    """Quita el proveedor de la sesion pausada: con el, la clave quedaria en el estado (§8.3)."""
    if resultado.continuacion is not None:
        resultado.continuacion.proveedor = None


def _copia_de_trabajo(continuacion: Any) -> Any:
    """Una copia del estado pausado del orquestador sobre la que se reanuda: si el bucle falla, la
    sesion original sigue intacta esperando la misma pregunta.

    Lo mutable de `orquestador._Sesion` se copia por su nombre; lo demas (borrador, servicios,
    topes, contadores, tuplas) es inmutable y se comparte.
    """
    copia = copy.copy(continuacion)
    for nombre in ("textos", "mensajes", "modelos", "restantes", "resultados", "respuestas"):
        setattr(copia, nombre, list(getattr(continuacion, nombre)))
    copia.rechazos = Counter(continuacion.rechazos)
    copia.rechazos_por_causa = Counter(continuacion.rechazos_por_causa)
    copia.pendientes = Pendientes(list(continuacion.pendientes.propuestas))
    copia.partidas_vistas = copy.deepcopy(continuacion.partidas_vistas)
    return copia


def responder(
    sesion: SesionDeAsistente,
    respuesta: str | None,
    registro: RegistroIA | None = _IGUAL,
    *,
    proveedor: ProveedorIA | None = None,
) -> None:
    """La respuesta de la persona a la pregunta del modelo (9g); `None` cancela la sesion (9h).

    Reanuda el bucle: las propuestas nuevas llegan como pendientes. No se puede decidir una
    propuesta mientras haya una pregunta sin responder.

    `proveedor` es el VIGENTE de la instalacion (la sesion guardada no lo retiene, por la clave):
    hace falta para responder y no para cancelar. Al terminar se suelta otra vez.

    `registro` es el de la conexion VIGENTE (la de la ejecucion ya se cerro): la pantalla abre una
    por respuesta. Si el bucle falla (por ejemplo, la base), la sesion sigue esperando la misma
    pregunta y el error sube.
    """
    continuacion = sesion.resultado.continuacion
    if continuacion is None:
        raise ValueError("la sesion no esta esperando una respuesta")
    if respuesta is not None and proveedor is None:
        raise ValueError("responder exige el proveedor vigente de la instalacion")
    trabajo = _copia_de_trabajo(continuacion)
    trabajo.proveedor = proveedor
    servicios = sesion.servicios
    if registro is not _IGUAL:
        trabajo.servicios = replace(trabajo.servicios, registro=registro)
        servicios = replace(servicios, registro=registro)
    try:
        resultado = continuar(replace(sesion.resultado, continuacion=trabajo), respuesta)
    finally:
        trabajo.proveedor = None  # la copia puede quedar como la continuacion de otra pregunta
    sesion.resultado = resultado
    sesion.servicios = servicios
    sesion.pendientes = Pendientes(list(resultado.propuestas))


def borrador_resultante(sesion: SesionDeAsistente) -> Borrador:
    """La base con las propuestas aceptadas (o editadas) aplicadas."""
    return aplicar(sesion.base, sesion.pendientes.aceptadas(), sesion.origen, sesion.catalogo)


def hipotetico(sesion: SesionDeAsistente) -> Borrador:
    """Lo que quedaria si se aceptara todo lo pendiente ademas de lo aceptado (§3.1 paso 5)."""
    todas = [*sesion.pendientes.aceptadas(), *sesion.pendientes.vigentes()]
    return aplicar(sesion.base, todas, sesion.origen, sesion.catalogo)


def decidir(
    sesion: SesionDeAsistente,
    propuesta_id: str,
    estado: EstadoPropuesta,
    usuario: str,
    registro: RegistroIA | None = None,
    *,
    sobre: Borrador | None = None,
) -> Borrador | None:
    """Acepta, edita o rechaza UNA propuesta pendiente y lo anota en el registro `ia_*`.

    Devuelve el borrador con la decision aplicada (`None` al rechazar, que no lo toca):

    * sin `sobre`, la base de la sesion con todo lo aceptado (`borrador_resultante` tras decidir);
    * con `sobre` (la hoja tal como la dejo la persona al editarla a mano), SOLO esta propuesta
      aplicada sobre ella: sus ediciones se conservan.

    Si la propuesta depende de otra aun pendiente, `DependenciaPendiente`; si no se puede aplicar
    sobre `sobre`, `HojaInvalida`. En los dos casos nada queda decidido ni registrado.

    `registro` es el de la conexion VIGENTE (la de la ejecucion ya se cerro): la pantalla abre una
    por decision.
    """
    if estado is EstadoPropuesta.PENDIENTE:
        raise ValueError("decidir exige aceptada, editada o rechazada")
    propuesta = sesion.pendientes.buscar(propuesta_id)
    if propuesta is None or propuesta.estado is not EstadoPropuesta.PENDIENTE:
        raise KeyError(f"no hay una propuesta pendiente {propuesta_id!r}")
    nuevo: Borrador | None = None
    if estado is not EstadoPropuesta.RECHAZADA:
        decidida = replace(propuesta, estado=estado)
        # lo aceptado tal como quedara tras decidir, en el orden de la lista (`aceptadas()`)
        aceptadas = [
            decidida if p.id == propuesta_id else p
            for p in sesion.pendientes.propuestas
            if p.id == propuesta_id
            or p.estado in (EstadoPropuesta.ACEPTADA, EstadoPropuesta.EDITADA)
        ]
        try:
            nuevo = aplicar(sesion.base, aceptadas, sesion.origen, sesion.catalogo)
        except HojaInvalida as error:
            raise DependenciaPendiente(
                f"{propuesta_id} depende de una propuesta que aun no acepto: {error}"
            ) from error
        if sobre is not None:
            nuevo = aplicar(sobre, [decidida], sesion.origen, sesion.catalogo)
    if registro is not None:  # primero el registro: si la base falla, nada queda decidido
        registro.decidir(sesion.resultado.sesion, propuesta_id, estado.value, usuario)
    sesion.pendientes.marcar(propuesta_id, estado)
    return nuevo


def fuente_del_cambio(sesion: SesionDeAsistente) -> str:
    """La fuente que prellena `guardar_version`: nunca la IA como responsable (§3.1 paso 7)."""
    o = sesion.origen
    return f"propuesta de IA, sesion {o.sesion}, {o.proveedor}/{o.modelo}"


def descripcion(propuesta: Propuesta) -> str:
    """Una linea legible de la propuesta, para la lista del panel (texto ajeno: va por
    `texto_seguro`)."""
    fila = propuesta.filas[0]
    if propuesta.tipo is TipoPropuesta.AMBIENTE:
        return f"Ambiente {fila['id']}: {fila['largo']} x {fila['ancho']} x {fila['alto']} m"
    if propuesta.tipo is TipoPropuesta.FUENTE:
        return f"Fuente {fila['id']} ({fila['tipo']}) en ({fila['x']}; {fila['y']}; {fila['z']})"
    if propuesta.tipo is TipoPropuesta.PUNTO:
        return (
            f"Punto {fila['id']} {fila['nombre']} ({fila['tipo']}) en "
            f"({fila['x']}; {fila['y']}; {fila['z']})"
        )
    if propuesta.tipo is TipoPropuesta.RECORRIDO:
        destino = fila.get("punto_id") or fila.get("circuito_id")
        modo = "declarado" if propuesta.declarado else "calculado por el sistema"
        return f"Recorrido de {destino} ({modo})"
    if propuesta.tipo is TipoPropuesta.PARTIDA:
        return f"Partida {fila['codigo']}: {fila['cantidad']} {fila['unidad']}"
    return f"Sin partida en el catalogo: {fila['necesidad']}"


@dataclass(frozen=True, slots=True)
class ResumenHipotetico:
    total: Decimal
    moneda: str
    hallazgos: dict[str, int]  # severidad -> cantidad


def resumen_hipotetico(borrador: Borrador) -> ResumenHipotetico:
    """Lo que el SISTEMA calcula sobre un borrador hipotetico (presupuesto y auditoria)."""
    resultado = hoja.elaborar_borrador(borrador)
    conteo = Counter(h.severidad.name for h in resultado.elaboracion.informe.hallazgos)
    return ResumenHipotetico(resultado.elaboracion.presupuesto.total, borrador.moneda, dict(conteo))
