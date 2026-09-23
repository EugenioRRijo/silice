"""Consulta y carga de partidas, insumos, precios y rendimientos.

`Catalogo` es la única puerta de entrada al catálogo persistido. Devuelve **contratos** cuando el
resultado va a cruzar una frontera de paquete (`ComposicionAPU`, `Rendimiento`) y **modelos** cuando
el llamador va a seguir trabajando con la sesión (`Partida`, `Insumo`, `ListaPrecios`).

Aquí se orquestan la sesión y las consultas; **ningún contrato se arma ni se traduce a modelo en
este módulo**: las dos direcciones están en `core/catalog/mapeo.py` (`a_composicion`,
`a_modelo_insumo`…). La única fila que este módulo construye por su cuenta es `models.PrecioInsumo`
en `_fijar_precio`, que no traduce ningún contrato: es la relación (lista, insumo) → precio, sin
contraparte en `core.contracts`.
"""

from __future__ import annotations

import string
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from core import models
from core.catalog.errores import CatalogoIncompleto
from core.catalog.mapeo import (
    LineaCatalogo,
    a_composicion,
    a_modelo_insumo,
    a_modelo_lineas,
    a_modelo_partida,
    a_modelo_rendimiento,
    a_modelo_rendimiento_estimado,
    a_rendimiento,
    lineas_de,
)
from core.contracts.apu import ComposicionAPU, Rendimiento, TipoRendimiento
from core.contracts.dominio import Dominio

#: Sufijos de variante de insumo: el segundo homónimo es «-B», el tercero «-C»…
SUFIJOS_VARIANTE = string.ascii_uppercase[1:]


@dataclass(slots=True)
class ResumenCarga:
    """Qué produjo una carga: la partida y los insumos creados, separando las variantes.

    `variantes` son los insumos creados porque ya existía uno con la misma descripción y unidad
    pero con **otro precio** en la misma lista: el hallazgo de datos de docs/modelo_datos.md §6.
    """

    partida: models.Partida
    insumos_nuevos: list[models.Insumo] = field(default_factory=list)
    variantes: list[models.Insumo] = field(default_factory=list)


class Catalogo:
    """Operaciones de consulta y carga sobre una sesión abierta."""

    def __init__(self, sesion: Session) -> None:
        self._sesion = sesion

    # -- consulta ------------------------------------------------------------------------------

    def partidas(self, dominio: Dominio | str | None = None) -> list[models.Partida]:
        """Partidas del catálogo, ordenadas por código; filtradas por dominio si se indica."""
        consulta = select(models.Partida).order_by(models.Partida.codigo)
        if dominio is not None:
            consulta = consulta.where(models.Partida.dominio == str(dominio))
        return list(self._sesion.scalars(consulta))

    def partida(self, codigo: str) -> models.Partida:
        """La partida de ese código. `KeyError` si no está en el catálogo."""
        partida = self._buscar_partida(codigo)
        if partida is None:
            raise KeyError(f"no hay ninguna partida con código {codigo!r} en el catálogo")
        return partida

    def insumos(self, tipo: models.TipoInsumo | str | None = None) -> list[models.Insumo]:
        """Insumos del catálogo, ordenados por código; filtrados por tipo si se indica."""
        consulta = select(models.Insumo).order_by(models.Insumo.codigo)
        if tipo is not None:
            consulta = consulta.where(models.Insumo.tipo == str(tipo))
        return list(self._sesion.scalars(consulta))

    def rendimientos(self, codigo_partida: str) -> list[Rendimiento]:
        """Todos los rendimientos de una partida, del más antiguo al más reciente."""
        self.partida(codigo_partida)
        consulta = (
            select(models.Rendimiento)
            .join(models.Partida)
            .where(models.Partida.codigo == codigo_partida)
            .order_by(models.Rendimiento.fecha, models.Rendimiento.id)
        )
        return [a_rendimiento(modelo) for modelo in self._sesion.scalars(consulta)]

    def lista_vigente(self, fecha: date | None = None) -> models.ListaPrecios:
        """La lista de mayor `fecha_vigencia` menor o igual a `fecha`; hoy si `fecha` es None."""
        limite = fecha if fecha is not None else date.today()
        lista = self._sesion.scalars(
            select(models.ListaPrecios)
            .where(models.ListaPrecios.fecha_vigencia <= limite)
            .order_by(models.ListaPrecios.fecha_vigencia.desc(), models.ListaPrecios.id.desc())
            .limit(1)
        ).one_or_none()
        if lista is None:
            raise CatalogoIncompleto(f"no hay ninguna lista de precios vigente al {limite}")
        return lista

    def composicion(
        self,
        codigo_partida: str,
        fecha: date | None = None,
        lista: models.ListaPrecios | None = None,
    ) -> ComposicionAPU:
        """Reconstruye el APU de una partida a una fecha (docs/modelo_datos.md §5).

        Precios: los de `lista`, o los de la lista vigente a esa fecha.
        Rendimiento: el ESTIMADO más reciente con `fecha` menor o igual a la pedida.
        """
        limite = fecha if fecha is not None else date.today()
        partida = self.partida(codigo_partida)
        if lista is None:
            lista = self.lista_vigente(limite)
        return a_composicion(partida, lista, self._rendimiento_estimado(partida, limite))

    def composiciones(
        self, codigos: Iterable[str], fecha: date | None = None
    ) -> dict[str, ComposicionAPU]:
        """Reconstruye varios APU con una sola resolución de lista de precios."""
        limite = fecha if fecha is not None else date.today()
        lista = self.lista_vigente(limite)
        return {codigo: self.composicion(codigo, fecha=limite, lista=lista) for codigo in codigos}

    # -- carga ---------------------------------------------------------------------------------

    def cargar_composicion(
        self,
        composicion: ComposicionAPU,
        lista: models.ListaPrecios,
        dominio: Dominio,
        fecha_rendimiento: date,
        condiciones: str,
    ) -> ResumenCarga:
        """Persiste un APU del contrato: partida, insumos, precios, líneas y rendimiento estimado.

        Reutiliza los insumos que ya existen con el mismo (tipo, descripción, unidad) y el mismo
        precio en la lista; si el precio difiere, crea una variante (§6 del modelo de datos).

        **No es reentrante.** Si la partida ya tiene composición cargada, lanza `ValueError` en vez
        de añadir un segundo juego de líneas: duplicarlas dejaría un APU con insumos repetidos y un
        segundo rendimiento estimado de la misma fecha, y hacerlo en silencio sería peor que fallar.
        Reemplazar una composición existente es `reemplazar_composicion`, una operación distinta.

        RF‑33 (`docs/ERS.md`, UC‑10; spec §3.3): el sistema no persiste una composición cuyo
        rendimiento no haya sido declarado explícitamente junto con sus condiciones. Por eso
        `condiciones` es obligatorio (`ValueError` si viene vacío o solo espacios), igual que en
        `reemplazar_composicion`, y se rechaza antes de tocar la sesión: dejar la partida creada
        y fallar después habría dejado una partida huérfana, sin composición ni rendimiento.
        """
        if not condiciones.strip():
            raise ValueError(
                "cargar_composicion exige las condiciones del rendimiento (RF-33): el sistema no "
                "persiste una composición cuyo rendimiento no se declare junto con ellas"
            )
        partida = self._buscar_partida(composicion.codigo_partida)
        if partida is None:
            partida = a_modelo_partida(composicion, dominio)
            self._sesion.add(partida)
            self._sesion.flush()
        elif self._tiene_composicion(partida):
            raise ValueError(
                f"la partida {partida.codigo} ya tiene composición cargada; bórrela antes de "
                "volver a cargarla (reemplazarla en silencio duplicaría sus líneas)"
            )

        resumen = self._cargar_lineas(partida, composicion, lista)
        self._sesion.add(
            a_modelo_rendimiento_estimado(composicion, partida, fecha_rendimiento, condiciones)
        )
        self._sesion.flush()
        return resumen

    def reemplazar_composicion(
        self,
        composicion: ComposicionAPU,
        lista: models.ListaPrecios,
        dominio: Dominio,
        fecha_rendimiento: date,
        condiciones: str,
    ) -> ResumenCarga:
        """Sustituye el desglose de una partida y, si algo cambió, registra un rendimiento nuevo.

        RF‑33 (`docs/ERS.md`, UC‑11): el sistema no persiste una composición cuyo rendimiento no
        haya sido declarado explícitamente junto con sus condiciones. Por eso `condiciones` es
        obligatorio (`ValueError` si viene vacío o solo espacios) y nunca se delega en un valor
        por defecto silencioso como hacía `a_modelo_rendimiento_estimado` antes de este arreglo
        (revisión final del ramal, arreglo 1: cada edición de UC‑11 dejaba un `Rendimiento` con
        `condiciones=''`).

        El rendimiento nuevo se registra **solo si el valor o las condiciones cambiaron** respecto
        del último rendimiento de la partida (arreglo 2 de la misma revisión): registrar uno
        idéntico en cada edición no es evidencia, es ruido que contamina la dispersión de
        `core.catalog.rendimientos` (varianza cero tras la primera edición sin cambios) y dispara
        `advertencia_rendimiento` ante cualquier valor futuro. El rendimiento anterior, cuando sí
        cambia algo, NO se pisa: queda en el histórico, porque la serie de rendimientos de una
        partida es evidencia (UC‑11). No hace `commit`: eso es de la capa que llama, como en
        `cargar_composicion`.

        `dominio` se acepta por simetría de firma con `cargar_composicion` y no se usa: la
        partida ya existe y su dominio no cambia al corregir su desglose.

        `.clear()` fuerza la carga de la colección `partida.composicion` (hace falta para saber
        qué borrar). `_cargar_lineas` inserta las líneas nuevas con `partida_id` explícito
        (`a_modelo_lineas`), sin pasar por esa colección ORM, así que tras el `flush()` la
        colección en memoria queda vacía y obsoleta: una lectura posterior de `partida.composicion`
        (p. ej. `Catalogo.composicion()`, que la recorre para reconstruir el contrato) vería cero
        líneas aunque ya estén en la base. Se expira el atributo para que la próxima lectura
        dispare una consulta nueva en vez de servir la colección cacheada.
        """
        if not condiciones.strip():
            raise ValueError(
                "reemplazar_composicion exige las condiciones del rendimiento (RF-33): el "
                "sistema no persiste una composición cuyo rendimiento no se declare junto con "
                "ellas"
            )
        partida = self._buscar_partida(composicion.codigo_partida)
        if partida is None:
            raise LookupError(
                f"no se puede reemplazar la composición de {composicion.codigo_partida}: "
                "la partida no existe en el catálogo"
            )
        partida.composicion.clear()
        self._sesion.flush()
        self._sesion.expire(partida, ["composicion"])
        resumen = self._cargar_lineas(partida, composicion, lista)
        self._registrar_rendimiento_si_cambia(partida, composicion, fecha_rendimiento, condiciones)
        return resumen

    def registrar_rendimiento(self, rendimiento: Rendimiento) -> models.Rendimiento:
        """Persiste un rendimiento del contrato. Un MEDIDO exige una `Ejecucion` ya registrada."""
        partida = self.partida(rendimiento.codigo_partida)
        ejecucion = None
        if rendimiento.referencia_ejecucion:
            ejecucion = self._sesion.scalars(
                select(models.Ejecucion).where(
                    models.Ejecucion.referencia == rendimiento.referencia_ejecucion
                )
            ).one_or_none()
            if ejecucion is None:
                raise CatalogoIncompleto(
                    f"no hay ninguna ejecución con referencia {rendimiento.referencia_ejecucion!r}"
                )
        modelo = a_modelo_rendimiento(rendimiento, partida, ejecucion)
        self._sesion.add(modelo)
        self._sesion.flush()
        return modelo

    # -- interno -------------------------------------------------------------------------------

    def _rendimiento_estimado(self, partida: models.Partida, limite: date) -> models.Rendimiento:
        rendimiento = self._sesion.scalars(
            select(models.Rendimiento)
            .where(
                models.Rendimiento.partida_id == partida.id,
                models.Rendimiento.tipo == TipoRendimiento.ESTIMADO.value,
                models.Rendimiento.fecha <= limite,
            )
            .order_by(models.Rendimiento.fecha.desc(), models.Rendimiento.id.desc())
            .limit(1)
        ).one_or_none()
        if rendimiento is None:
            raise CatalogoIncompleto(
                f"la partida {partida.codigo} no tiene rendimiento estimado al {limite}"
            )
        return rendimiento

    def _buscar_partida(self, codigo: str) -> models.Partida | None:
        return self._sesion.scalars(
            select(models.Partida).where(models.Partida.codigo == codigo)
        ).one_or_none()

    def _tiene_composicion(self, partida: models.Partida) -> bool:
        return (
            self._sesion.scalar(
                select(models.ComposicionAPU.id)
                .where(models.ComposicionAPU.partida_id == partida.id)
                .limit(1)
            )
            is not None
        )

    def _cargar_lineas(
        self,
        partida: models.Partida,
        composicion: ComposicionAPU,
        lista: models.ListaPrecios,
    ) -> ResumenCarga:
        """Persiste líneas, insumos y precios de una partida ya creada.

        No toca el rendimiento: `cargar_composicion` y `reemplazar_composicion` lo registran cada
        uno a su manera (el primero, uno nuevo siempre; el segundo, RF‑33, solo si algo cambió).
        """
        resumen = ResumenCarga(partida=partida)
        lineas = lineas_de(composicion)
        insumos = [self._resolver_insumo(linea, lista, resumen) for linea in lineas]
        self._sesion.add_all(a_modelo_lineas(lineas, partida, insumos))
        self._sesion.flush()
        return resumen

    def _registrar_rendimiento_si_cambia(
        self,
        partida: models.Partida,
        composicion: ComposicionAPU,
        fecha: date,
        condiciones: str,
    ) -> None:
        """Añade un rendimiento ESTIMADO solo si el valor o las condiciones cambiaron (arreglo 2).

        Compara contra el último rendimiento ESTIMADO de la partida (el más reciente por fecha e
        id), no contra el último de cualquier tipo: el consumidor que importa es `composicion()`,
        que reconstruye el APU con `_rendimiento_estimado`, filtrado estrictamente por
        `tipo == ESTIMADO`. Comparar contra el último de cualquier tipo (incluido un MEDIDO
        registrado entre medio con `registrar_rendimiento`) podía concluir que «no cambió nada» y
        omitir el ESTIMADO nuevo aunque el MEDIDO no sea lo que `composicion()` lee: el rendimiento
        vigente quedaba obsoleto en silencio. Repetir un rendimiento idéntico tampoco es evidencia:
        es la misma patología que el ruling de la siembra (`scripts/seed.py`) evitó a propósito
        para la línea base, reintroducida aquí por cada edición de UC‑11 antes de este arreglo.
        """
        historico = self.rendimientos(composicion.codigo_partida)
        estimados = [r for r in historico if r.tipo is TipoRendimiento.ESTIMADO]
        anterior = estimados[-1] if estimados else None
        if (
            anterior is not None
            and anterior.valor == composicion.rendimiento
            and anterior.condiciones == condiciones
        ):
            return
        self._sesion.add(
            a_modelo_rendimiento_estimado(composicion, partida, fecha, condiciones)
        )
        self._sesion.flush()

    def _resolver_insumo(
        self, linea: LineaCatalogo, lista: models.ListaPrecios, resumen: ResumenCarga
    ) -> models.Insumo:
        """Reutiliza el insumo homónimo si su precio en la lista coincide; si no, crea variante."""
        candidatos = list(
            self._sesion.scalars(
                select(models.Insumo)
                .where(
                    models.Insumo.tipo == linea.tipo.value,
                    models.Insumo.descripcion == linea.descripcion,
                    models.Insumo.unidad == linea.unidad,
                )
                .order_by(models.Insumo.id)
            )
        )
        for candidato in candidatos:
            vigente = self._precio_en_lista(lista, candidato)
            if vigente is None:
                self._fijar_precio(lista, candidato, linea.precio)
                return candidato
            if vigente == linea.precio:
                return candidato

        codigo = (
            self._codigo_variante(candidatos[0].codigo)
            if candidatos
            else self._codigo_nuevo(linea.tipo)
        )
        insumo = a_modelo_insumo(linea, codigo)
        self._sesion.add(insumo)
        self._sesion.flush()
        self._fijar_precio(lista, insumo, linea.precio)
        destino = resumen.variantes if candidatos else resumen.insumos_nuevos
        destino.append(insumo)
        return insumo

    def _precio_en_lista(self, lista: models.ListaPrecios, insumo: models.Insumo) -> Decimal | None:
        return self._sesion.scalar(
            select(models.PrecioInsumo.precio).where(
                models.PrecioInsumo.lista_id == lista.id,
                models.PrecioInsumo.insumo_id == insumo.id,
            )
        )

    def _fijar_precio(
        self, lista: models.ListaPrecios, insumo: models.Insumo, precio: Decimal
    ) -> None:
        self._sesion.add(models.PrecioInsumo(lista_id=lista.id, insumo_id=insumo.id, precio=precio))
        self._sesion.flush()

    def _codigo_nuevo(self, tipo: models.TipoInsumo) -> str:
        prefijo = models.PREFIJO_CODIGO_INSUMO[tipo]
        numeros = [
            int(partes[1])
            for codigo in self._sesion.scalars(
                select(models.Insumo.codigo).where(models.Insumo.tipo == tipo.value)
            )
            if len(partes := codigo.split("-")) > 1 and partes[1].isdigit()
        ]
        return f"{prefijo}-{max(numeros, default=0) + 1:03d}"

    def _codigo_variante(self, codigo_base: str) -> str:
        raiz = "-".join(codigo_base.split("-")[:2])
        for sufijo in SUFIJOS_VARIANTE:
            candidato = f"{raiz}-{sufijo}"
            if not self._existe_codigo(candidato):
                return candidato
        raise CatalogoIncompleto(f"se agotaron los sufijos de variante para {raiz}")

    def _existe_codigo(self, codigo: str) -> bool:
        return (
            self._sesion.scalar(select(models.Insumo.id).where(models.Insumo.codigo == codigo))
            is not None
        )
