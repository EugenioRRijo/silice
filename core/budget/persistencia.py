"""Persistencia del presupuesto: guardar el documento emitido y volver a leerlo.

Implementa el versionado híbrido de `docs/modelo_datos.md` §5. Al guardar, cada renglón congela su
`ResultadoAPU` completo (la parte «documento»: lo que se firmó) y el presupuesto copia los cuatro
`ParametrosCosto` con que se calculó. Al cargar, la composición se **reconstruye** desde el catálogo
con la lista de precios que el presupuesto referencia y se vuelve a pasar por el motor: si el precio
unitario reconstruido no coincide con la instantánea, el presupuesto y el catálogo se han desligado
y `cargar_presupuesto` lo denuncia con `ValueError` en vez de devolver un documento adulterado.
El `Presupuesto` devuelto lleva la instantánea, no el recálculo: es lo que se emitió.

Los ítems **pendientes** de UC‑01 3a (sin partida en el catálogo) se guardan como ítems de cómputo
del presupuesto sin renglón, y `cargar_elaboracion` los vuelve a declarar en el informe recargado,
que así es el del documento emitido (INV‑080, expediente C3.1 de
`docs/bitacora/2026-09-24-C3-expedientes.md`). Lo mismo con los precios **atípicos** que declaró
una revaloración (`CODIGO_ATIPICO`, UC‑07 paso 5, expediente C6.5) y con los de cualquier regla
que no esté entre las que recarga corre (SF‑E1, RF‑62): la reauditoría no los puede recalcular, así
que se leen de los hallazgos guardados.

`core/catalog/mapeo.py` es el único lugar donde se cruza la frontera modelo↔contrato **del
catálogo**; este módulo es el único donde se cruza la del **presupuesto**. Los modelos se usan
siempre cualificados (`models.X`) y los contratos por su nombre: siete nombres coinciden.

Los tres campos JSON‑texto (`ItemComputo.parametros`, `ItemComputo.especificaciones` y
`Hallazgo.origen_ids`) se serializan con los `Decimal` **como cadena**, según
`docs/modelo_datos.md` §4.3, para que la ida y vuelta sea exacta.
"""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Mapping, Sequence
from decimal import Decimal

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from core import models
from core.budget._modelo import _buscar, _parametros_de, _sesion_de
from core.budget.curva import PeriodoPlan
from core.budget.instantanea import composiciones_de_version, congelar

# `_declarar_pendientes` y `_clave_pendiente` son ayudantes del módulo hermano del mismo paquete
# que redactan el hallazgo `PENDIENTE` y su clave: la recarga y la comprobación al guardar usan la
# misma única definición que la elaboración (mismo criterio de `actualizacion.py` con `_buscar`).
from core.budget.presupuesto import (
    CODIGO_PENDIENTE,
    ResultadoElaboracion,
    _clave_pendiente,
    _declarar_externos,
    _declarar_pendientes,
)
from core.catalog import Catalogo
from core.contracts.apu import ComposicionAPU, ParametrosCosto, ResultadoAPU
from core.contracts.dominio import Dominio
from core.contracts.item_computo import ItemComputo, OrigenTipo
from core.contracts.presupuesto import PartidaPresupuestada, Presupuesto, PuntoCurva
from core.contracts.verificacion import Hallazgo, ReglaVerificacion, Severidad
from core.costing import calcular_apu
from core.verification import REGLAS, auditar
from core.verification.directivas import CLAVE_UNIDAD_ORIGINAL
from core.verification.informe import InformeAuditoria

__all__ = [
    "TOLERANCIA_RECONSTRUCCION",
    "cargar_elaboracion",
    "cargar_presupuesto",
    "crear_proyecto",
    "guardar_presupuesto",
]

#: Diferencia máxima admitida entre el precio unitario reconstruido y el de la instantánea.
TOLERANCIA_RECONSTRUCCION = Decimal("0.000001")


def crear_proyecto(
    session: Session,
    nombre: str,
    descripcion: str = "",
    dominio: Dominio | str = "",
) -> models.Proyecto:
    """UC‑01, paso 1: crea el proyecto que agrupará los presupuestos (expediente C6.3).

    El nombre se guarda sin espacios sobrantes y es único (`ValueError` si queda vacío o si ya
    existe: chocar con la restricción única en el `flush` daría un `IntegrityError` en vez de un
    rechazo legible). `dominio` es opcional; si se indica, debe ser un valor de `Dominio` y se
    guarda como texto, como en la siembra. Hace `flush`, no `commit`, como `guardar_presupuesto`.
    """
    nombre = nombre.strip()
    if not nombre:
        raise ValueError("el nombre del proyecto no puede estar vacio")
    if dominio != "":
        try:
            dominio = Dominio(dominio)
        except ValueError:
            esperados = ", ".join(d.value for d in Dominio)
            raise ValueError(
                f"dominio {dominio!r} desconocido; se espera uno de {esperados}"
            ) from None
    existente = session.scalar(select(models.Proyecto.id).where(models.Proyecto.nombre == nombre))
    if existente is not None:
        raise ValueError(f"ya existe un proyecto llamado {nombre!r}")
    proyecto = models.Proyecto(nombre=nombre, descripcion=descripcion, dominio=str(dominio))
    session.add(proyecto)
    session.flush()
    return proyecto


def guardar_presupuesto(
    session: Session,
    presupuesto: Presupuesto,
    informe: InformeAuditoria,
    proyecto: models.Proyecto,
    lista: models.ListaPrecios,
    parametros: ParametrosCosto,
    pendientes: Sequence[ItemComputo] = (),
    plan: Sequence[PeriodoPlan] | None = None,
    version_origen: models.Presupuesto | None = None,
    motivo: str = "",
    heredar_insumos: bool = False,
) -> models.Presupuesto:
    """Persiste el presupuesto con su cómputo, su curva y los hallazgos de su informe.

    `pendientes` son los ítems que la elaboración dejó sin partida (`ResultadoElaboracion`,
    UC‑01 3a). Se guardan como ítems de cómputo del presupuesto **sin renglón**, para que
    `cargar_elaboracion` los vuelva a declarar (INV‑080). La correspondencia se exige en los dos
    sentidos (`ValueError` si falla): cada pendiente tiene su hallazgo `CODIGO_PENDIENTE` en el
    informe, porque guardar uno que el documento no declara haría que la recarga dijera más que el
    documento; y cada hallazgo `CODIGO_PENDIENTE` del informe tiene su pendiente, porque sin él la
    recarga diría menos (un informe emitido NO CUMPLE recargado como CUMPLE).

    Deja la transacción abierta: confirmar o deshacer es decisión de quien llama. Cada partida del
    presupuesto debe existir en el catálogo (`KeyError` si no), porque el renglón persistido la
    referencia por clave foránea, y el informe tiene que ser el de este presupuesto (`ValueError`):
    los hallazgos se guardan colgando de él y atribuirlos a otro documento sería falsear la
    auditoría.

    SF‑E6: congela además la instantánea de la versión (la composición y el rendimiento de cada
    partida distinta, y el plan: `plan` o, sin él, el que revela la curva si es inferible).
    SF‑E2: `version_origen` y `motivo` (`models.MOTIVOS_VERSION`) declaran de qué versión salió
    esta; van juntos o ninguno. `heredar_insumos` (solo con `version_origen`: edición y
    restauración) copia el `insumo_id` de cada línea de la instantánea de origen (SF3 R‑7).
    """
    if (version_origen is None) != (motivo == ""):
        raise ValueError("version_origen y motivo se declaran juntos o ninguno")
    if motivo and motivo not in models.MOTIVOS_VERSION:
        raise ValueError(f"motivo {motivo!r} desconocido; se espera {models.MOTIVOS_VERSION}")
    if informe.codigo_presupuesto != presupuesto.codigo:
        raise ValueError(
            f"el informe audita el presupuesto {informe.codigo_presupuesto!r}, "
            f"no el {presupuesto.codigo!r} que se está guardando"
        )
    _exigir_correspondencia(pendientes, informe)

    catalogo = Catalogo(session)
    # Las partidas del catálogo se resuelven antes de construir nada: así un código desconocido
    # falla sin dejar a medias el presupuesto, y ninguna consulta posterior dispara el autoflush
    # de una jerarquía todavía incompleta.
    catalogadas = [catalogo.partida(p.item.codigo_partida) for p in presupuesto.partidas]

    modelo = models.Presupuesto(
        codigo=presupuesto.codigo,
        proyecto=proyecto,
        fecha=presupuesto.fecha,
        moneda=presupuesto.moneda,
        lista_precios=lista,
        fcas=parametros.fcas,
        bono_alimentacion=parametros.bono_alimentacion,
        administracion=parametros.administracion,
        utilidad=parametros.utilidad,
    )

    for orden, (partida, catalogada) in enumerate(
        zip(presupuesto.partidas, catalogadas, strict=True)
    ):
        item = _a_modelo_item(partida.item, modelo)
        modelo.partidas.append(_a_modelo_renglon(partida, catalogada, item, orden))

    # Después de los renglones: sus `id` quedan en el orden de `pendientes`, que es el que
    # `cargar_elaboracion` restituye.
    for pendiente in pendientes:
        _a_modelo_item(pendiente, modelo)

    for orden, punto in enumerate(presupuesto.curva):
        modelo.curva.append(
            models.PuntoCurva(
                orden=orden,
                periodo=punto.periodo,
                monto=punto.monto,
                acumulado=punto.acumulado,
            )
        )

    for hallazgo in informe.hallazgos:
        modelo.hallazgos.append(
            models.Hallazgo(
                regla=hallazgo.regla,
                severidad=int(hallazgo.severidad),
                descripcion=hallazgo.descripcion,
                impacto=hallazgo.impacto,
                origen_ids=json.dumps(list(hallazgo.origen_ids)),
                valor_observado=hallazgo.valor_observado,
                valor_esperado=hallazgo.valor_esperado,
            )
        )

    session.add(modelo)
    session.flush()
    congelar(
        session, modelo, presupuesto, lista, plan, version_origen if heredar_insumos else None
    )
    if version_origen is not None:
        session.add(
            models.VersionOrigen(
                presupuesto_id=modelo.id, origen_id=version_origen.id, motivo=motivo
            )
        )
        session.flush()
    return modelo


def cargar_presupuesto(
    session: Session, proyecto_nombre: str, codigo: str, catalogo: Catalogo
) -> Presupuesto:
    """Reconstruye el `Presupuesto` del contrato a partir de lo persistido.

    Cada renglón se revalora con `Catalogo.composicion` sobre la lista de precios que el propio
    presupuesto referencia y se compara con la instantánea guardada: una diferencia mayor que
    `TOLERANCIA_RECONSTRUCCION` en el precio unitario es `ValueError`.
    """
    return _presupuesto_de(_buscar(session, proyecto_nombre, codigo), catalogo)


def _presupuesto_de(modelo: models.Presupuesto, catalogo: Catalogo) -> Presupuesto:
    """La reconstrucción de `cargar_presupuesto` sobre una fila ya encontrada."""
    sesion = _sesion_de(modelo)
    parametros = _parametros_de(modelo)
    # SF‑E6: la composición de cada partida sale de la instantánea de la versión y, solo si falta,
    # del catálogo (versiones anteriores a SF‑E6).
    congeladas = composiciones_de_version(sesion, modelo)

    partidas = tuple(
        _a_contrato_renglon(renglon, modelo, catalogo, parametros, congeladas)
        for renglon in modelo.partidas
    )
    curva = tuple(
        PuntoCurva(periodo=punto.periodo, monto=punto.monto, acumulado=punto.acumulado)
        for punto in modelo.curva
    )
    return Presupuesto(
        codigo=modelo.codigo,
        fecha=modelo.fecha,
        moneda=modelo.moneda,
        partidas=partidas,
        curva=curva,
    )


def cargar_elaboracion(
    session: Session,
    proyecto_nombre: str,
    codigo: str,
    catalogo: Catalogo,
    reglas: Sequence[ReglaVerificacion] = REGLAS,
) -> ResultadoElaboracion:
    """El presupuesto guardado con el informe del documento emitido, pendientes incluidos.

    `presupuesto` es el de `cargar_presupuesto` (la misma reconstrucción y la misma denuncia de un
    catálogo desligado). `pendientes` son los ítems de cómputo del presupuesto que ningún renglón
    cita, en el orden en que se guardaron. El informe es la reauditoría del presupuesto con esos
    pendientes declarados otra vez, como en `elaborar` (UC‑01 3a): así el informe recargado es el
    emitido y no puede declarar CUMPLE un presupuesto emitido NO CUMPLE (RF‑02, INV‑080).

    La reauditoría corre `reglas` (las siete por defecto). Los hallazgos guardados cuya regla no
    está en `reglas` (los `CODIGO_ATIPICO` de la revaloración que emitió esta versión, UC‑07
    paso 5, y los de toda regla externa, SF‑E1) se vuelven a declarar tal cual: la reauditoría no
    puede recalcularlos. Los de una regla que sí está en `reglas` se recalculan y no se leen, así
    que pasar `reglas` ampliadas reemplaza los guardados de esas reglas sin duplicarlos.

    Límite: un presupuesto guardado antes de INV‑080 no tiene sus pendientes persistidos y su
    recarga no los inventa: su informe es `auditar(cargar_presupuesto(...))` (expediente C3.1).
    """
    reglas = tuple(reglas)
    modelo = _buscar(session, proyecto_nombre, codigo)
    presupuesto = _presupuesto_de(modelo, catalogo)
    pendientes = _cargar_pendientes(session, modelo)
    informe = _declarar_pendientes(auditar(presupuesto, reglas), pendientes)
    return ResultadoElaboracion(
        presupuesto=presupuesto,
        informe=_declarar_externos(informe, _cargar_externos(session, modelo, reglas)),
        pendientes=pendientes,
    )


def _cargar_externos(
    session: Session,
    modelo: models.Presupuesto,
    reglas: Sequence[ReglaVerificacion] = REGLAS,
    *,
    sin: Sequence[str] = (),
) -> tuple[Hallazgo, ...]:
    """Los hallazgos guardados del presupuesto cuya regla no es de `reglas`, ni `CODIGO_PENDIENTE`
    (que se declara aparte), ni de `sin`; en el orden en que se guardaron (SF‑E1).

    `actualizar_precios` pasa `sin=(CODIGO_ATIPICO,)`: los atípicos de la lista anterior no son
    los de la nueva.
    """
    excluidas = {regla.codigo for regla in reglas} | {CODIGO_PENDIENTE, *sin}
    filas = session.scalars(
        select(models.Hallazgo)
        .where(
            models.Hallazgo.presupuesto_id == modelo.id,
            models.Hallazgo.regla.not_in(excluidas),
        )
        .order_by(models.Hallazgo.id)
    )
    return tuple(
        Hallazgo(
            regla=fila.regla,
            severidad=Severidad(fila.severidad),
            descripcion=fila.descripcion,
            impacto=fila.impacto,
            origen_ids=tuple(json.loads(fila.origen_ids)),
            valor_observado=fila.valor_observado,
            valor_esperado=fila.valor_esperado,
        )
        for fila in filas
    )


def _cargar_pendientes(session: Session, modelo: models.Presupuesto) -> tuple[ItemComputo, ...]:
    """Los ítems de cómputo del presupuesto que ningún renglón cita (sus pendientes), en el orden
    en que se guardaron (por `id`). Lo comparten `cargar_elaboracion` y `actualizar_precios`."""
    con_renglon = exists().where(
        models.PartidaPresupuestada.item_computo_id == models.ItemComputo.id
    )
    filas = session.scalars(
        select(models.ItemComputo)
        .where(models.ItemComputo.presupuesto_id == modelo.id, ~con_renglon)
        .order_by(models.ItemComputo.id)
    )
    return tuple(_a_contrato_item(fila) for fila in filas)


def _exigir_correspondencia(pendientes: Sequence[ItemComputo], informe: InformeAuditoria) -> None:
    """Los pendientes y los hallazgos `CODIGO_PENDIENTE` del informe se corresponden uno a uno,
    por `_clave_pendiente` (partida y origen)."""
    declarados = Counter(
        tuple(hallazgo.origen_ids)
        for hallazgo in informe.hallazgos
        if hallazgo.regla == CODIGO_PENDIENTE
    )
    guardados = Counter(_clave_pendiente(item) for item in pendientes)
    problemas = [
        *(
            f"el informe no declara el pendiente {codigo} ({origen})"
            for codigo, origen in guardados - declarados
        ),
        *(
            f"el informe declara pendiente {' '.join(clave)} sin pasarlo en 'pendientes'"
            for clave in declarados - guardados
        ),
    ]
    if problemas:
        raise ValueError("pendientes e informe no se corresponden: " + "; ".join(problemas))


# ---------------------------------------------------------------------------------------------
# Contrato -> modelo
# ---------------------------------------------------------------------------------------------


def _a_modelo_item(item: ItemComputo, presupuesto: models.Presupuesto) -> models.ItemComputo:
    """La cantidad de obra, con su unidad original y sus dos diccionarios en JSON‑texto."""
    return models.ItemComputo(
        codigo_partida=item.codigo_partida,
        descripcion=item.descripcion,
        unidad_original=item.especificaciones.get(CLAVE_UNIDAD_ORIGINAL, item.unidad),
        unidad=item.unidad,
        cantidad=item.cantidad,
        origen_id=item.origen_id,
        origen_tipo=str(item.origen_tipo),
        dominio=str(item.dominio),
        presupuesto=presupuesto,
        regla=item.regla,
        parametros=_json_decimales(item.parametros),
        especificaciones=json.dumps(dict(item.especificaciones)),
    )


def _a_modelo_renglon(
    partida: PartidaPresupuestada,
    catalogada: models.Partida,
    item: models.ItemComputo,
    orden: int,
) -> models.PartidaPresupuestada:
    """El renglón con la instantánea completa del `ResultadoAPU` (desnormalización de §4.2)."""
    resultado = partida.resultado
    return models.PartidaPresupuestada(
        partida=catalogada,
        item_computo=item,
        orden=orden,
        cantidad=partida.item.cantidad,
        materiales=resultado.materiales,
        equipos=resultado.equipos,
        mano_obra=resultado.mano_obra,
        costo_directo=resultado.costo_directo,
        con_administracion=resultado.con_administracion,
        precio_unitario=resultado.precio_unitario,
        total=partida.total,
    )


def _json_decimales(valores: Mapping[str, Decimal]) -> str:
    """JSON de un diccionario de `Decimal`, con cada valor como cadena (§4.3)."""
    return json.dumps({clave: str(valor) for clave, valor in valores.items()})


# ---------------------------------------------------------------------------------------------
# Modelo -> contrato
# ---------------------------------------------------------------------------------------------


def _a_contrato_renglon(
    renglon: models.PartidaPresupuestada,
    presupuesto: models.Presupuesto,
    catalogo: Catalogo,
    parametros: ParametrosCosto,
    congeladas: Mapping[str, ComposicionAPU],
) -> PartidaPresupuestada:
    codigo = renglon.partida.codigo
    composicion = congeladas.get(codigo) or catalogo.composicion(
        codigo, fecha=presupuesto.fecha, lista=presupuesto.lista_precios
    )
    reconstruido = calcular_apu(composicion, parametros)
    _verificar(codigo, reconstruido, renglon)
    return PartidaPresupuestada(
        item=_a_contrato_item(renglon.item_computo),
        apu=composicion,
        resultado=_a_contrato_resultado(renglon),
    )


def _verificar(
    codigo: str, reconstruido: ResultadoAPU, renglon: models.PartidaPresupuestada
) -> None:
    diferencia = abs(reconstruido.precio_unitario - renglon.precio_unitario)
    if diferencia > TOLERANCIA_RECONSTRUCCION:
        raise ValueError(
            f"la partida {codigo} no se reconstruye: el catálogo da un precio unitario de "
            f"{reconstruido.precio_unitario} y el presupuesto guardó "
            f"{renglon.precio_unitario} (difieren en {diferencia})"
        )


def _a_contrato_item(item: models.ItemComputo) -> ItemComputo:
    return ItemComputo(
        codigo_partida=item.codigo_partida,
        descripcion=item.descripcion,
        unidad=item.unidad,
        cantidad=item.cantidad,
        origen_id=item.origen_id,
        origen_tipo=OrigenTipo(item.origen_tipo),
        dominio=Dominio(item.dominio),
        regla=item.regla,
        parametros={clave: Decimal(valor) for clave, valor in json.loads(item.parametros).items()},
        especificaciones=json.loads(item.especificaciones),
    )


def _a_contrato_resultado(renglon: models.PartidaPresupuestada) -> ResultadoAPU:
    """La instantánea tal como se emitió, no el recálculo: es la parte «documento» del modelo."""
    return ResultadoAPU(
        materiales=renglon.materiales,
        equipos=renglon.equipos,
        mano_obra=renglon.mano_obra,
        costo_directo=renglon.costo_directo,
        con_administracion=renglon.con_administracion,
        precio_unitario=renglon.precio_unitario,
    )
