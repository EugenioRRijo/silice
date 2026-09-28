"""Esquemas Pydantic, espejo de los contratos del nucleo.

Los montos (`Decimal`) viajan siempre como texto (`str`), nunca como `float` (CLAUDE.md §2.3): la
conversion a `Decimal` ocurre en la frontera, construyendo siempre desde el mismo texto que
persiste `core.models.tipos.DecimalExacto`.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation

from pydantic import BaseModel, ConfigDict, Field


def decimal_desde_texto(texto: str, campo: str) -> Decimal:
    """`Decimal` construido desde el texto de la peticion, o `ValueError` con el campo culpable.

    `Decimal("12,50")` lanza `InvalidOperation`, que NO hereda de `ValueError` y llegaria al
    cliente como 500 crudo; y `Decimal("NaN")`/`Decimal("Infinity")` parsean pero no son montos
    (la primera comparacion del nucleo lanzaria `InvalidOperation`). Ambos casos se declaran aqui,
    en la frontera, como `ValueError` -> 422 (`api.main.manejar_value_error`).
    """
    try:
        valor = Decimal(texto)
    except InvalidOperation as exc:
        raise ValueError(f"{campo}: {texto!r} no es un monto decimal valido") from exc
    if not valor.is_finite():
        raise ValueError(f"{campo}: {texto!r} no es un monto finito")
    return valor


class PartidaRespuesta(BaseModel):
    """Cabecera de una partida del catalogo."""

    model_config = ConfigDict(from_attributes=True)

    codigo: str
    descripcion: str
    unidad: str
    dominio: str


class InsumoRespuesta(BaseModel):
    """Un insumo del catalogo, con su precio en la lista vigente si la hay."""

    model_config = ConfigDict(from_attributes=True)

    codigo: str
    descripcion: str
    tipo: str
    unidad: str | None
    precio_vigente: str | None


class ListaRespuesta(BaseModel):
    """Cabecera de una lista de precios registrada."""

    model_config = ConfigDict(from_attributes=True)

    nombre: str
    moneda: str
    fecha_vigencia: date
    origen: str


class CargaListaRespuesta(BaseModel):
    """Lo que produjo cargar un archivo de precios: la lista creada y los insumos desconocidos."""

    lista: ListaRespuesta
    desconocidos: list[str]


class CambioRespuesta(BaseModel):
    """Un cambio de precio del historial (UC-02)."""

    insumo: str
    precio_anterior: str
    precio_nuevo: str
    variacion: str
    fecha: date


class ItemComputoPeticion(BaseModel):
    """Un `ItemComputo` tal como lo envía el cliente: cantidad y parámetros como texto."""

    codigo_partida: str
    descripcion: str
    unidad: str
    cantidad: str
    origen_id: str
    origen_tipo: str
    dominio: str
    regla: str | None = None
    parametros: dict[str, str] = {}
    especificaciones: dict[str, str] = {}


class ItemComputoRespuesta(BaseModel):
    """Un `ItemComputo` extraído por un adaptador (UC-01), con cantidad y parámetros exactos."""

    codigo_partida: str
    descripcion: str
    unidad: str
    cantidad: str
    origen_id: str
    origen_tipo: str
    dominio: str
    regla: str | None
    parametros: dict[str, str]
    especificaciones: dict[str, str]


class PresupuestoPeticion(BaseModel):
    """Lo que hace falta para elaborar un presupuesto (UC-01/05): items ya extraídos por un
    adaptador o construidos a mano, y los cuatro parámetros de costo, opcionales (por defecto los
    de `ParametrosCosto`, la línea base de CLAUDE.md §4).
    """

    codigo: str
    fecha: date
    moneda: str = "USD"
    proyecto: str
    items: list[ItemComputoPeticion]
    fcas: str | None = None
    bono_alimentacion: str | None = None
    administracion: str | None = None
    utilidad: str | None = None


class PropuestaPartidaRespuesta(BaseModel):
    """Una partida del catálogo parecida a la de un ítem pendiente (UC‑03, RF‑15).

    El puntaje es una similitud adimensional del coseno, no un monto: viaja como número
    (`ml/normalization/normalizador.py`, la excepción declarada a la regla `Decimal`).
    """

    codigo: str
    descripcion: str
    puntaje: float


class ItemPendienteRespuesta(BaseModel):
    """Un ítem sin partida en el catálogo (UC‑01, flujo 3a): no suma al total y el informe lo
    declara. Para aceptar una propuesta se vuelve a enviar el ítem con ese código. `propuestas`
    queda vacía sin el extra `ml` o sin el modelo de similitud en la caché local."""

    codigo_partida: str
    descripcion: str
    unidad: str
    cantidad: str
    origen_id: str
    propuestas: list[PropuestaPartidaRespuesta]


class PresupuestoCreadoRespuesta(BaseModel):
    """Lo que confirma la elaboración: el total (dos decimales), cuántos hallazgos audita y los
    ítems que quedaron pendientes por no tener partida en el catálogo (UC‑01, flujo 3a)."""

    codigo: str
    total: str
    hallazgos: int
    pendientes: list[ItemPendienteRespuesta] = Field(default_factory=list)


class PartidaPresupuestadaRespuesta(BaseModel):
    """Un renglón del presupuesto, tal como se presenta (dos decimales, CLAUDE.md §2.3)."""

    codigo_partida: str
    descripcion: str
    unidad: str
    cantidad: str
    precio_unitario: str
    total: str


class PresupuestoDetalleRespuesta(BaseModel):
    """El presupuesto completo, reconstruido desde el catálogo (`cargar_presupuesto`)."""

    codigo: str
    fecha: date
    moneda: str
    total: str
    partidas: list[PartidaPresupuestadaRespuesta]


class PresupuestoResumenRespuesta(BaseModel):
    """Cabecera de un presupuesto guardado: código y total, para el listado."""

    codigo: str
    total: str


class ActualizacionPeticion(BaseModel):
    """UC-02 sobre un presupuesto guardado: la lista nueva y el código de la versión que produce."""

    lista: str
    codigo_nuevo: str


class FilaComparativoRespuesta(BaseModel):
    """Una fila de `core.budget.Comparativo`, con todos sus montos presentados a dos decimales."""

    codigo_partida: str
    descripcion: str
    cantidad: str
    pu_anterior: str
    pu_nuevo: str
    variacion_pct: str
    total_anterior: str
    total_nuevo: str
    incidencia_pct: str


class ComparativoRespuesta(BaseModel):
    """El comparativo completo de UC-02: totales antes y después, y una fila por renglón."""

    total_anterior: str
    total_nuevo: str
    insumos_afectados: int
    filas: list[FilaComparativoRespuesta]


# ---------------------------------------------------------------------------------------------
# Escenarios de sensibilidad (UC-08)
# ---------------------------------------------------------------------------------------------


class EscenarioPeticion(BaseModel):
    """Un escenario de UC-08: parámetros de costo opcionales y precios nuevos por insumo.

    Los parámetros que la petición no trae heredan los del presupuesto **base** (los congelados
    en su fila), no los valores por defecto del contrato: un escenario pregunta «¿y si cambiara
    esto?» sobre lo que el presupuesto realmente usa. `precios` mapea descripción de insumo a su
    precio de ensayo, como texto decimal.
    """

    nombre: str
    fcas: str | None = None
    bono_alimentacion: str | None = None
    administracion: str | None = None
    utilidad: str | None = None
    precios: dict[str, str] = Field(default_factory=dict)


class EscenariosPeticion(BaseModel):
    """UC-08 sobre un presupuesto guardado: uno o más escenarios a comparar contra el base."""

    escenarios: list[EscenarioPeticion] = Field(min_length=1)


class EscenarioRespuesta(BaseModel):
    """Una fila de la tabla de RF-31 con su detalle: total, variación contra el base, hallazgos
    de su auditoría (que se genera siempre) y el diferencial por partida (paso 3 del flujo).
    """

    nombre: str
    total: str
    variacion: str
    variacion_pct: str
    hallazgos: int
    insumos_variados: int
    partidas: list[FilaComparativoRespuesta]


class PendienteBaseRespuesta(BaseModel):
    """Un ítem pendiente del presupuesto base (UC‑01, flujo 3a): sin partida en el catálogo, no
    suma al total del base ni al de ningún escenario (INV‑083)."""

    origen_id: str
    codigo_partida: str
    descripcion: str


class EscenariosRespuesta(BaseModel):
    """La comparación completa de UC-08. Nada de esto queda persistido (RF-30).

    `pendientes_base` declara los ítems pendientes del base (INV‑083): `generar_escenario` solo
    recalcula los renglones valorados, así que ningún escenario los ve. Vacía si el base no tiene
    pendientes o si se guardó antes de que se persistieran (INV‑080). El informe propio de cada
    escenario no los declara (ruling C4‑3, a limitaciones).
    """

    codigo_base: str
    total_base: str
    pendientes_base: list[PendienteBaseRespuesta] = Field(default_factory=list)
    escenarios: list[EscenarioRespuesta]


# ---------------------------------------------------------------------------------------------
# Rendimientos y ejecuciones (UC-06, Sesion I6.2)
# ---------------------------------------------------------------------------------------------


class EjecucionPeticion(BaseModel):
    """La obra ejecutada de la que se mediran rendimientos (registro, RF-25)."""

    referencia: str
    fecha_inicio: date
    fecha_fin: date | None = None
    descripcion: str = ""


class EjecucionRespuesta(BaseModel):
    """Una obra ejecutada registrada."""

    model_config = ConfigDict(from_attributes=True)

    referencia: str
    fecha_inicio: date
    fecha_fin: date | None
    descripcion: str


class RendimientoPeticion(BaseModel):
    """Registro de un rendimiento sobre una partida. `valor` viaja como texto decimal."""

    valor: str
    tipo: str
    fecha: date
    condiciones: str = ""
    referencia_ejecucion: str | None = None


class RendimientoRespuesta(BaseModel):
    """Un rendimiento del historico: estimado o medido, siempre declarado."""

    valor: str
    tipo: str
    fecha: date
    condiciones: str
    referencia_ejecucion: str | None


class DispersionRespuesta(BaseModel):
    """RF-26: el comportamiento observado de la partida, con montos como texto exacto."""

    observaciones: int
    media: str
    minimo: str
    maximo: str
    medidos: int
    estimados: int


class PropuestaRendimientoRespuesta(BaseModel):
    """La propuesta al componer un APU: rendimiento elegido mas su dispersion."""

    rendimiento: RendimientoRespuesta
    dispersion: DispersionRespuesta


class RendimientosRespuesta(BaseModel):
    """El historico completo de una partida, con dispersion y propuesta (RF-26)."""

    historico: list[RendimientoRespuesta]
    dispersion: DispersionRespuesta | None
    propuesta: PropuestaRendimientoRespuesta | None


class RegistroRendimientoRespuesta(BaseModel):
    """Lo registrado y la advertencia de RF-27 (o null): advertir nunca es impedir."""

    rendimiento: RendimientoRespuesta
    advertencia: str | None
