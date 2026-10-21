"""El bucle neutral de herramientas (S4 §5.3): un solo bucle para los dos proveedores.

El historial es solo de agregar. Cada llamada pasa por `validar_llamada` (esquema, semantica, citas,
construccion); una propuesta valida queda PENDIENTE y el borrador NO cambia hasta que la persona
acepta (RF-32). Topes: turnos (12), llamadas (60), costo (por defecto 2 USD) y tres rechazos
seguidos de la misma herramienta (9c). El turno que alcanza el tope de costo se completa (sus
llamadas se validan y se registran) y la sesion se detiene (9f): conserva lo propuesto.

Una pregunta del modelo (9g) puede PAUSAR la sesion: si `Servicios.responder` devuelve `ESPERAR`,
`ejecutar` termina con `MotivoFin.ESPERANDO_RESPUESTA`, la pregunta y una continuacion; la pantalla
muestra la pregunta y llama a `continuar(resultado, respuesta)`. Las demas llamadas de ese turno
esperan su turno.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum
from typing import Any

from aplicacion.hoja import Borrador, HojaInvalida
from asistente.catalogo import CatalogoVista
from asistente.herramientas import (
    HERRAMIENTAS,
    POR_NOMBRE,
    BuscarPartidas,
    ConsultarPartida,
    RetirarPropuesta,
    Terminar,
    TipoHerramienta,
)
from asistente.privacidad import (
    INSTRUCCIONES,
    TopeDePartidas,
    contiene_secreto,
    describir_partida,
    hallazgos_minimizados,
    primer_mensaje,
    resultado_para_el_modelo,
    resumen_del_borrador,
)
from asistente.propuestas import OrigenIA, Pendientes, Propuesta, aplicar
from asistente.proveedores.base import (
    ErrorDeProveedor,
    EsquemaHerramienta,
    FinTurno,
    LlamadaHerramienta,
    Mensaje,
    ProveedorIA,
    ResultadoHerramienta,
    Tarifa,
    Uso,
)
from asistente.registro import RegistroIA
from asistente.validacion import Contexto, Rechazo, validar_llamada
from core.verification.informe import InformeAuditoria


class MotivoFin(StrEnum):
    TERMINAR = "terminar"
    FIN_DEL_MODELO = "fin_del_modelo"
    TOPE_DE_TURNOS = "tope_de_turnos"
    TOPE_DE_LLAMADAS = "tope_de_llamadas"
    TOPE_DE_COSTO = "tope_de_costo"
    RECHAZOS_SEGUIDOS = "rechazos_seguidos"
    REHUSADO = "rehusado"
    LIMITE_DE_SALIDA = "limite_de_salida"
    CANCELADO = "cancelado"
    ERROR_DE_PROVEEDOR = "error_de_proveedor"
    ESPERANDO_RESPUESTA = "esperando_respuesta"


MENSAJES: dict[MotivoFin, str] = {
    MotivoFin.TERMINAR: "El asistente termino.",
    MotivoFin.FIN_DEL_MODELO: "El asistente termino sin llamar a terminar.",
    MotivoFin.TOPE_DE_TURNOS: "Se alcanzo el tope de turnos; se conservan las propuestas validas.",
    MotivoFin.TOPE_DE_LLAMADAS: "Se alcanzo el tope de llamadas; se conservan las propuestas.",
    MotivoFin.TOPE_DE_COSTO: "Se alcanzo el tope de costo; se conservan las propuestas.",
    MotivoFin.RECHAZOS_SEGUIDOS: "Tres rechazos seguidos de una herramienta: la sesion se detuvo.",
    MotivoFin.REHUSADO: "El proveedor rechazo el pedido; se conservan las ya validadas.",
    MotivoFin.LIMITE_DE_SALIDA: "La respuesta se corto por el limite de salida; turno descartado.",
    MotivoFin.CANCELADO: "Sesion cancelada.",
    MotivoFin.ERROR_DE_PROVEEDOR: "El proveedor no respondio.",
    MotivoFin.ESPERANDO_RESPUESTA: "El asistente espera su respuesta.",
}


class Espera:
    """El valor de `Servicios.responder` que pausa la sesion hasta que la persona conteste."""


ESPERAR = Espera()


@dataclass(frozen=True, slots=True)
class Topes:
    turnos: int = 12
    llamadas: int = 60
    costo: Decimal | None = Decimal(2)
    rechazos_seguidos: int = 3


@dataclass(frozen=True, slots=True)
class Servicios:
    catalogo: CatalogoVista
    tarifa: Tarifa
    auditar: Callable[[Borrador], InformeAuditoria]
    #: Responde una pregunta del modelo: un texto, `None` (cancela la sesion, 9h) o `ESPERAR`
    #: (la sesion se pausa hasta que la persona conteste, 9g).
    responder: Callable[[str], str | None | Espera] = lambda _pregunta: None
    registro: RegistroIA | None = None
    proyecto: str = ""
    version_partida: str = ""
    #: Condicion A del experimento: `pedir_informe_auditoria` desactivada (§9.3).
    informe_permitido: bool = True


@dataclass(frozen=True, slots=True)
class ResultadoSesion:
    sesion: int
    motivo: MotivoFin
    propuestas: tuple[Propuesta, ...]
    costo: Decimal
    turnos: int
    llamadas: int
    notas: tuple[str, ...]
    mensaje: str
    respuestas_de_la_persona: tuple[str, ...]
    #: Llamadas de propuesta, las que pasaron las cuatro capas y los rechazos por causa (§9.5).
    llamadas_de_propuesta: int = 0
    propuestas_validas: int = 0
    rechazos_por_causa: Mapping[str, int] = field(default_factory=dict)
    #: Si la sesion espera una respuesta: la pregunta (texto del modelo: va por `texto_seguro`).
    pregunta: str | None = None
    #: Fichas gastadas en total y modelos que respondieron (para la prueba real y el registro).
    uso: Uso = field(default_factory=Uso)
    modelos: tuple[str, ...] = ()
    #: El estado de la sesion pausada, para `continuar` (opaco).
    continuacion: Any = field(default=None, repr=False, compare=False)


def herramientas_visibles(informe_permitido: bool) -> tuple[EsquemaHerramienta, ...]:
    return tuple(
        EsquemaHerramienta(h.nombre, h.descripcion, h.esquema())
        for h in HERRAMIENTAS
        if informe_permitido or h.nombre != "pedir_informe_auditoria"
    )


@dataclass(frozen=True, slots=True)
class Ejecucion:
    """Lo que dejo ejecutar una llamada: el resultado para el modelo y lo que se registra."""

    resultado: ResultadoHerramienta
    veredicto: str
    motivo: str = ""
    respuesta: str | None = None
    cancelar: bool = False
    espera: str | None = None  # la pregunta, si la sesion se pausa


class _Sesion:
    """El estado mutable de una sesion; la pausa por una pregunta lo conserva para `continuar`."""

    def __init__(
        self,
        proveedor: ProveedorIA,
        pedido: str,
        borrador: Borrador,
        servicios: Servicios,
        topes: Topes,
        numero: int,
    ) -> None:
        self.proveedor = proveedor
        self.borrador = borrador
        self.servicios = servicios
        self.topes = topes
        self.numero = numero
        self.origen = OrigenIA(proveedor.nombre, proveedor.modelo, numero)
        self.textos = [pedido]
        self.pendientes = Pendientes.vacia()
        self.partidas_vistas = TopeDePartidas()
        self.rechazos: Counter[str] = Counter()
        self.rechazos_por_causa: Counter[str] = Counter()
        self.llamadas_de_propuesta = 0
        self.propuestas_validas = 0
        self.notas: tuple[str, ...] = ()
        self.nube = proveedor.envia_fuera_del_equipo
        self.herramientas = herramientas_visibles(servicios.informe_permitido)
        self.mensajes: list[Mensaje] = [Mensaje("usuario", primer_mensaje(pedido, borrador))]
        self.turnos = 0
        self.llamadas = 0
        self.costo = Decimal(0)
        self.uso = Uso()
        self.modelos: list[str] = []
        self.restantes: list[LlamadaHerramienta] = []
        self.resultados: list[ResultadoHerramienta] = []
        self.pregunta_en_espera: LlamadaHerramienta | None = None
        self.respuestas: list[str] = []

    # -- vistas -------------------------------------------------------------------------------

    def hipotetico(self) -> Borrador:
        try:
            return aplicar(
                self.borrador, self.pendientes.vigentes(), self.origen, self.servicios.catalogo
            )
        except HojaInvalida:  # no deberia ocurrir: cada pendiente se valido junto con las otras
            return self.borrador

    def contexto(self) -> Contexto:
        return Contexto(
            tuple(self.textos),
            self.borrador,
            self.pendientes.propuestas,
            self.servicios.catalogo,
            self.origen,
            self.pendientes.siguiente_id(),
        )

    # -- una llamada --------------------------------------------------------------------------

    def ejecutar(self, llamada: LlamadaHerramienta) -> Ejecucion:
        resultado = validar_llamada(llamada.nombre, llamada.argumentos, self.contexto())
        herramienta = POR_NOMBRE.get(llamada.nombre)
        if herramienta is not None and herramienta.tipo is TipoHerramienta.PROPUESTA:
            self.llamadas_de_propuesta += 1
        if isinstance(resultado, Rechazo):
            self.rechazos_por_causa[resultado.causa.value] += 1
            self.rechazos[llamada.nombre] += 1
            texto = f"rechazada ({resultado.causa.value}): {resultado.motivo}"
            return Ejecucion(
                ResultadoHerramienta(llamada.id, texto, True),
                resultado.causa.value,
                resultado.motivo,
            )
        self.rechazos[llamada.nombre] = 0
        if isinstance(resultado, Propuesta):
            self.propuestas_validas += 1
            self.pendientes.agregar(resultado)
            texto = f"propuesta {resultado.id} registrada"
            return Ejecucion(ResultadoHerramienta(llamada.id, texto), "valida")
        return self._lectura_o_control(llamada, resultado)

    def _lectura_o_control(self, llamada: LlamadaHerramienta, modelo: object) -> Ejecucion:
        def ok(datos: object) -> Ejecucion:
            contenido = resultado_para_el_modelo(datos)
            return Ejecucion(ResultadoHerramienta(llamada.id, contenido), "valida")

        def error(texto: str, *, cancelar: bool = False) -> Ejecucion:
            return Ejecucion(
                ResultadoHerramienta(llamada.id, texto, True),
                "no_disponible",
                texto,
                cancelar=cancelar,
            )

        nombre = llamada.nombre
        if nombre == "consultar_borrador":
            return ok(resumen_del_borrador(self.hipotetico()))
        if nombre == "pedir_informe_auditoria":
            if not self.servicios.informe_permitido:
                return error("herramienta no disponible en esta sesion")
            return ok(hallazgos_minimizados(self.servicios.auditar(self.hipotetico())))
        if isinstance(modelo, BuscarPartidas):
            texto = (
                f"{modelo.especialidad.value}: {modelo.texto}"
                if modelo.especialidad
                else modelo.texto
            )
            encontradas, semantica = self.servicios.catalogo.buscar(texto, modelo.cuantos)
            admitidas, omitida = self.partidas_vistas.admitir(encontradas)
            datos: dict[str, object] = {
                "partidas": [describir_partida(p, nube=self.nube) for p in admitidas],
                "busqueda": "semantica" if semantica else "palabras",
            }
            if omitida:
                datos["nota"] = "tope de partidas distintas por sesion: solo partidas ya vistas"
            return ok(datos)
        if isinstance(modelo, ConsultarPartida):
            partida = self.servicios.catalogo.partida(modelo.codigo)
            if partida is None:
                return error(f"la partida {modelo.codigo!r} no esta en el catalogo")
            admitidas, _ = self.partidas_vistas.admitir([partida])
            if not admitidas:
                return error("tope de partidas distintas por sesion alcanzado")
            return ok(describir_partida(partida, nube=self.nube))
        if isinstance(modelo, RetirarPropuesta):
            if not self.pendientes.retirar(modelo.propuesta_id):
                return error(f"no hay una propuesta pendiente {modelo.propuesta_id!r}")
            return ok({"retirada": modelo.propuesta_id})
        if isinstance(modelo, Terminar):
            self.notas = tuple(modelo.notas)
            return ok({"fin": True})
        return self._pregunta(llamada, modelo.pregunta)  # preguntar_al_usuario

    def _pregunta(self, llamada: LlamadaHerramienta, pregunta: str) -> Ejecucion:
        respuesta = self.servicios.responder(pregunta)
        if isinstance(respuesta, Espera):
            return Ejecucion(ResultadoHerramienta(llamada.id, ""), "espera", espera=pregunta)
        return self._respuesta(llamada, respuesta)

    def _respuesta(self, llamada: LlamadaHerramienta, respuesta: str | None) -> Ejecucion:
        """La respuesta de la persona (o su cancelacion) como resultado de la pregunta (9g, 9h)."""
        if respuesta is None:
            texto = "la persona cancelo la sesion"
            return Ejecucion(
                ResultadoHerramienta(llamada.id, texto, True), "no_disponible", texto, cancelar=True
            )
        if contiene_secreto(respuesta):
            aviso = (
                "respuesta no enviada: parece contener una clave; pida a la persona que la "
                "escriba de nuevo sin ella"
            )
            return Ejecucion(
                ResultadoHerramienta(llamada.id, aviso, True),
                "secreto_filtrado",
                "respuesta con marca de secreto",
            )
        self.textos.append(respuesta)
        return Ejecucion(ResultadoHerramienta(llamada.id, respuesta), "valida", respuesta=respuesta)

    # -- el bucle (reanudable) ----------------------------------------------------------------

    def _resultado(
        self, motivo: MotivoFin, mensaje: str = "", pregunta: str | None = None
    ) -> ResultadoSesion:
        registro = self.servicios.registro
        if registro and motivo is not MotivoFin.ESPERANDO_RESPUESTA:
            for p in self.pendientes.propuestas:
                registro.propuesta(
                    self.numero,
                    p.id,
                    p.tipo.value,
                    p.estado.value,
                    p.citas,
                    p.supuestos,
                    [dict(f) for f in p.filas],
                )
            registro.cerrar(self.numero, motivo.value)
        return ResultadoSesion(
            sesion=self.numero,
            motivo=motivo,
            propuestas=tuple(self.pendientes.propuestas),
            costo=self.costo,
            turnos=self.turnos,
            llamadas=self.llamadas,
            notas=self.notas,
            mensaje=mensaje or MENSAJES[motivo],
            respuestas_de_la_persona=tuple(self.respuestas),
            llamadas_de_propuesta=self.llamadas_de_propuesta,
            propuestas_validas=self.propuestas_validas,
            rechazos_por_causa=dict(self.rechazos_por_causa),
            pregunta=pregunta,
            uso=self.uso,
            modelos=tuple(dict.fromkeys(self.modelos)),
            continuacion=self if pregunta is not None else None,
        )

    def _registrar_turno(self, turno, gasto: Decimal) -> None:
        registro = self.servicios.registro
        if registro:
            registro.turno(
                self.numero,
                self.turnos,
                modelo=turno.modelo_que_respondio or self.proveedor.modelo,
                fin=turno.fin.value,
                uso={
                    "entrada": turno.uso.entrada,
                    "salida": turno.uso.salida,
                    "cache_lectura": turno.uso.cache_lectura,
                    "cache_escritura": turno.uso.cache_escritura,
                },
                costo=gasto,
                texto=turno.texto,
            )

    def _registrar_llamada(self, llamada: LlamadaHerramienta, hecho: Ejecucion) -> None:
        registro = self.servicios.registro
        if registro:
            registro.llamada(
                self.numero,
                self.turnos,
                llamada.nombre,
                llamada.argumentos,
                hecho.veredicto,
                hecho.motivo,
                hecho.respuesta,
            )

    def correr(self) -> ResultadoSesion:
        while True:
            if not self.restantes and not self.resultados:  # turno nuevo
                if self.turnos >= self.topes.turnos:
                    return self._resultado(MotivoFin.TOPE_DE_TURNOS)
                try:
                    turno = self.proveedor.turno(INSTRUCCIONES, self.mensajes, self.herramientas)
                except ErrorDeProveedor as error:
                    return self._resultado(MotivoFin.ERROR_DE_PROVEEDOR, str(error))
                self.turnos += 1
                gasto = self.servicios.tarifa.costo(turno.uso)
                self.costo += gasto
                self.uso = Uso(
                    self.uso.entrada + turno.uso.entrada,
                    self.uso.salida + turno.uso.salida,
                    self.uso.cache_lectura + turno.uso.cache_lectura,
                    self.uso.cache_escritura + turno.uso.cache_escritura,
                )
                self.modelos.append(turno.modelo_que_respondio or self.proveedor.modelo)
                self._registrar_turno(turno, gasto)
                if turno.fin is FinTurno.RECHAZO:
                    return self._resultado(MotivoFin.REHUSADO)
                if turno.fin is FinTurno.LIMITE:  # 9j: el turno se descarta entero
                    return self._resultado(MotivoFin.LIMITE_DE_SALIDA)
                self.mensajes.append(
                    Mensaje("asistente", turno.texto, turno.llamadas, crudo=turno.crudo)
                )
                if turno.fin is FinTurno.FIN or not turno.llamadas:
                    return self._resultado(MotivoFin.FIN_DEL_MODELO)
                self.restantes = list(turno.llamadas)
            while self.restantes:
                llamada = self.restantes.pop(0)
                if self.llamadas >= self.topes.llamadas:
                    return self._resultado(MotivoFin.TOPE_DE_LLAMADAS)
                self.llamadas += 1
                hecho = self.ejecutar(llamada)
                if hecho.espera is not None:  # 9g: pausa; las demas llamadas esperan su turno
                    self.pregunta_en_espera = llamada
                    return self._resultado(MotivoFin.ESPERANDO_RESPUESTA, pregunta=hecho.espera)
                self.resultados.append(hecho.resultado)
                if hecho.respuesta is not None:
                    self.respuestas.append(hecho.respuesta)
                self._registrar_llamada(llamada, hecho)
                if hecho.cancelar:
                    return self._resultado(MotivoFin.CANCELADO)
                if llamada.nombre == "terminar" and not hecho.resultado.es_error:
                    return self._resultado(MotivoFin.TERMINAR)
                if self.rechazos[llamada.nombre] >= self.topes.rechazos_seguidos:
                    return self._resultado(MotivoFin.RECHAZOS_SEGUIDOS)
            self.mensajes.append(Mensaje("usuario", resultados=tuple(self.resultados)))
            self.resultados = []
            if self.topes.costo is not None and self.costo >= self.topes.costo:
                return self._resultado(MotivoFin.TOPE_DE_COSTO)

    def contestar(self, respuesta: str | None) -> Ejecucion:
        """Pone la respuesta de la persona como resultado de la pregunta pausada."""
        llamada = self.pregunta_en_espera
        if llamada is None:
            raise ValueError("la sesion no espera ninguna respuesta")
        self.pregunta_en_espera = None
        hecho = self._respuesta(llamada, respuesta)
        if hecho.respuesta is not None:
            self.respuestas.append(hecho.respuesta)
        self.resultados.append(hecho.resultado)
        self._registrar_llamada(llamada, hecho)
        return hecho


def ejecutar(
    proveedor: ProveedorIA,
    pedido: str,
    borrador: Borrador,
    servicios: Servicios,
    topes: Topes = Topes(),  # noqa: B008
    *,
    sesion_n: int = 0,
) -> ResultadoSesion:
    registro = servicios.registro
    numero = (
        registro.iniciar(
            proyecto=servicios.proyecto,
            version_partida=servicios.version_partida,
            proveedor=proveedor.nombre,
            modelo=proveedor.modelo,
            pedido=pedido,
            topes={"turnos": topes.turnos, "llamadas": topes.llamadas, "costo": str(topes.costo)},
        )
        if registro
        else sesion_n
    )
    return _Sesion(proveedor, pedido, borrador, servicios, topes, numero).correr()


def continuar(resultado: ResultadoSesion, respuesta: str | None) -> ResultadoSesion:
    """Reanuda una sesion `ESPERANDO_RESPUESTA` con la respuesta de la persona (`None` cancela).

    Una respuesta con una marca de secreto (`sk-ant-`, `-----BEGIN`) no se envia ni se registra:
    el modelo recibe el aviso y puede preguntar de nuevo.
    """
    sesion = resultado.continuacion
    if sesion is None:
        raise ValueError("la sesion no esta esperando una respuesta")
    if sesion.contestar(respuesta).cancelar:
        return sesion._resultado(MotivoFin.CANCELADO)
    return sesion.correr()
