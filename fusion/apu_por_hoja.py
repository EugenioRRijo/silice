"""Auditar un libro con un APU por hoja y, si viene, su libro de presupuesto (F5 vial, tarea 5).

Diseño `docs/especificaciones/2026-11-03-presupuesto-vial-real-design.md` §7.3 y §8.3. Como el
resto de `fusion`: en memoria, sin guardar nada, y **sin creer los precios escritos**: cada hoja se
recalcula con el motor del núcleo (`fusion.mapeo.composicion_de_apu_por_hoja`) y lo impreso solo
se compara. El libro es prueba documental y nunca se modifica.

Hallazgos (`FilaHallazgo`, con su `HOJA!CELDA`; la acción es siempre «informado»):

- **AH1** precio unitario impreso frente al recalculado. Hasta un centavo (V-15, la tolerancia de
  CV1) no hay hallazgo. Si se pasa, Sílice rehace la cuenta como la hace el programa que exporta
  estos libros (cada renglón y cada subtotal redondeados a dos decimales, `_pu_por_renglon`): si
  así da el impreso, la diferencia es solo de redondeo y el hallazgo es INFO y lo explica
  (decisión provisional 6 del 2026-11-06); si no, ERROR.
- **AH2** un bono por renglón distinto de cero: no evaluable (INFO). El bono de Sílice es un monto
  por obrero y día, no por renglón.
- **AH3** un financiamiento distinto de cero: no evaluable (INFO). Sílice no tiene ese parámetro y
  reproducirlo exigiría tocar el núcleo.
- **AH4** un impuesto dentro del APU distinto de cero: ADVERTENCIA (el IVA va sobre el total). El
  precio de esa hoja no se compara: el impreso ya lo incluye.
- **AH5** el precio unitario del presupuesto frente al impreso en su APU (ERROR).
- **AH6** la cantidad del presupuesto frente a la de la cabecera de su APU (ADVERTENCIA).
- **AH7** un renglón del presupuesto sin hoja de APU, o una hoja sin renglón (ADVERTENCIA).
- **AH8** una unidad del libro traducida por el perfil («lt» → «l», «t-km» → «t»), una vez por
  hoja y por unidad (INFO): la traducción queda dicha, nunca escondida.
- **AH9** la banda de distancia del transporte leída de la descripción con el patrón del perfil
  (INFO), con la coma decimal y el punto de miles de `aplicacion.cifras`; si la descripción no
  sigue el patrón, no hay hallazgo, y si una cifra no sigue la regla, el AH9 dice que no se adivina.
- **AH10** dos hojas con el mismo número de renglón (ADVERTENCIA, en la celda del número de la
  segunda): el presupuesto se enlaza con la primera y la otra no se compara con ningún renglón.
- **AH11** la hoja del presupuesto parece de otra obra (ADVERTENCIA, en el encabezado de su
  cantidad): de los renglones enlazados con cantidad en los dos lados (dos o más), menos de la
  mitad tienen la misma que su APU. Pasa cuando el perfil lee la hoja de otro frente (prueba de
  punta a punta del 2026-11-13, E2E-2; umbral simulado en `docs/bitacora/2026-11-13-e2e-front.md`):
  cada renglón da su AH6 y este hallazgo dice la causa probable y qué hoja leyó el perfil.
- **AH12** las hojas del libro de APU que no empiezan por el prefijo del perfil (INFO, en la A1 de
  la primera): se nombran sin leerlas (a lo sumo `MAX_NOMBRADAS`), para que una hoja de APU mal
  nombrada no se salte en silencio (libro por frentes, D3).

**Varias hojas de presupuesto** (libro por frentes, ola 2, línea 3, 2026-11-13; decisiones
simuladas en `docs/bitacora/2026-11-13-ola2-libro-por-frentes.md`): el perfil puede declarar una
hoja por frente (`presupuesto.hojas`) y quien llama puede elegir otras (`hojas=`, D4). Con varias
hojas, el precio unitario se compara renglón por renglón en cada hoja (AH5) y la cantidad del APU,
una vez, con la **suma** de las hojas que traen ese renglón (AH6 y AH11, D1): un libro de APU que
sirve a varios frentes lleva en su cabecera la cantidad de la obra entera. Con una hoja, todo es
como antes. `ResultadoApuPorHoja.renglones` guarda cada renglón con su hoja (su frente) para quien
lleva el libro a la Hoja.

El enlace presupuesto ↔ APU es el número de renglón (la cabecera «Partida N°» de la hoja). Un
libro de solo valores no trae fórmulas: las reglas L del libro conocido no aplican y la evidencia es
el recálculo.

Cifras enormes (revisión de correcciones de F5/F7/F8, N3): el lector ataja cada cifra que pasa de
`TOPE_CIFRA` con su celda, y aquí se atajan con la suya el P.U. y la cantidad del presupuesto. Si
cada cifra cabe pero el recálculo de una hoja no cabe en la precisión del `Decimal` (muchos
renglones grandes, porcentajes enormes), la hoja no se recalcula (`LibroNoInterpretable` con la
hoja): antes era un 500.

El perfil se busca primero en la carpeta de perfiles locales que pasa quien llama
(`carpeta_perfiles`; la API pasa `<carpeta de datos>/perfiles_libros/`,
`operacion.config.carpeta_perfiles_libros()`), o en la de `SILICE_PERFILES_LIBROS` si está, y
después en el paquete. Este módulo no importa `operacion.config` (revisión de correcciones de
F5/F7/F8, N5): dónde viven los datos lo decide la instalación.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation, Overflow
from pathlib import Path
from typing import Any

from adapters.hoja_empresa.guardia import ArchivoRechazado
from adapters.hoja_empresa.lector_apu_por_hoja import (
    TOPE_CIFRA,
    es_hoja_de_apu,
    leer_hojas,
    leer_libro_apu_por_hoja,
    letra,
    numero_de,
)
from adapters.hoja_empresa.modelo import (
    ApuLeido,
    Celda,
    FilaHallazgo,
    LibroLeido,
    LibroNoInterpretable,
    Rotulo,
    TipoInsumo,
)
from adapters.hoja_empresa.perfil import coincide, normalizar
from adapters.hoja_empresa.perfil_apu_por_hoja import (
    PerfilApuPorHoja,
    cargar_perfil_apu_por_hoja,
    carpetas_locales,
)
from adapters.vial.constantes import TOLERANCIA_PRECIO
from aplicacion.cifras import BandaIlegible, leer_banda
from aplicacion.regla_desperdicio import TrazaDesperdicio, cantidad_con_desperdicio
from core.contracts.apu import ComposicionAPU, ParametrosCosto
from core.costing.motor import calcular_apu
from fusion.mapeo import composicion_de_apu_por_hoja

__all__ = [
    "MAX_NOMBRADAS",
    "ApuRecalculado",
    "RenglonPresupuesto",
    "ResultadoApuPorHoja",
    "auditar_apu_por_hoja",
]

#: Cuántas hojas nombra a lo sumo un mensaje (AH12, una hoja pedida que no está): «… y n más».
MAX_NOMBRADAS = 10
_CERO = Decimal(0)
_CIEN = Decimal(100)
_CENTAVO = Decimal("0.01")
_INFORMADO = "informado"


@dataclass(frozen=True, slots=True)
class ApuRecalculado:
    """Una hoja de APU: lo impreso y lo que recalcula Sílice (`None` si no es evaluable).

    Libro por frentes (2026-11-13): también la composición del núcleo y sus parámetros (los mismos
    con que se recalculó), la cantidad de la cabecera con su celda y la celda del precio de cada
    línea en el orden canónico (materiales, equipos y mano de obra): lo que necesita quien lleva el
    libro a la Hoja, sin volver a leerlo."""

    hoja: str
    numero: int | None
    codigo: str
    descripcion: str
    unidad: str
    precio_impreso: Decimal
    precio_silice: Decimal | None
    celda_precio: str
    composicion: ComposicionAPU | None = None
    parametros: ParametrosCosto | None = None
    cantidad: Decimal | None = None
    celda_cantidad: str | None = None
    celdas_precio: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ResultadoApuPorHoja:
    """El informe: las hojas recalculadas, los hallazgos y la traza del desperdicio."""

    libro: LibroLeido
    perfil: str
    origen_perfil: str
    apus: tuple[ApuRecalculado, ...]
    hallazgos: tuple[FilaHallazgo, ...]
    trazas: tuple[TrazaDesperdicio, ...]
    presupuesto: str | None = None
    #: La primera hoja del libro de presupuesto que se leyó, `None` sin presupuesto.
    hoja_presupuesto: str | None = None
    #: Todas las hojas leídas del presupuesto (una por frente), en su orden; vacía sin presupuesto.
    hojas_presupuesto: tuple[str, ...] = ()
    #: Los renglones del presupuesto, hoja por hoja; vacía sin presupuesto.
    renglones: tuple[RenglonPresupuesto, ...] = ()


def _es(valor: Decimal, decimales: int | None = None) -> str:
    """Coma decimal y punto de miles; con `decimales`, redondeado ROUND_HALF_UP al presentar."""
    if decimales is not None:
        valor = valor.quantize(Decimal(1).scaleb(-decimales), rounding=ROUND_HALF_UP)
    else:
        valor = valor.normalize()
    texto = format(valor, ",f")
    return texto.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def _r(valor: Decimal) -> Decimal:
    return valor.quantize(_CENTAVO, rounding=ROUND_HALF_UP)


def _hallazgo(
    codigo: str, severidad: str, celda: Celda | str, texto: str, impacto: Decimal | None = None
) -> FilaHallazgo:
    return FilaHallazgo(codigo, severidad, texto, str(celda), impacto, _INFORMADO)


def _pu_por_renglon(apu: ApuLeido) -> Decimal:
    """El precio unitario como lo calcula el programa que exporta estos libros: cada renglón, cada
    subtotal por unidad, la administración y la utilidad redondeados a dos decimales."""
    materiales = equipos = base = _CERO
    for linea in apu.lineas:
        if linea.tipo is TipoInsumo.MATERIAL:
            cantidad = cantidad_con_desperdicio(linea.cantidad, linea.desperdicio)
            materiales += _r(cantidad * linea.precio)
        elif linea.tipo is TipoInsumo.EQUIPO:
            coeficiente = Decimal(1) if linea.depreciacion is None else linea.depreciacion
            equipos += _r(linea.cantidad * linea.precio * coeficiente)
        else:
            base += _r(linea.cantidad * linea.precio)
    mano_obra = _r(base * (1 + (apu.prestaciones or _CERO)))
    directo = materiales + _r(equipos / apu.rendimiento) + _r(mano_obra / apu.rendimiento)
    subtotal = directo + _r(directo * apu.administracion)
    return subtotal + _r(subtotal * apu.utilidad)


def _ident(apu: ApuLeido) -> str:
    return f"{apu.hoja} ({apu.codigo_partida})" if apu.codigo_partida else apu.hoja


def _pct(fraccion: Decimal) -> str:
    return _es(fraccion * _CIEN)


def _unidades(apu: ApuLeido, perfil: PerfilApuPorHoja) -> list[FilaHallazgo]:
    vistas: dict[str, Celda] = {}
    usadas = [(apu.unidad, apu.celdas.get("unidad"))] + [
        (linea.unidad, linea.celdas.get("unidad")) for linea in apu.lineas
    ]
    for escrita, celda in usadas:
        if escrita in perfil.unidades and escrita not in vistas and celda is not None:
            vistas[escrita] = celda
    return [
        _hallazgo(
            "AH8",
            "INFO",
            celda,
            f"{apu.hoja}: la unidad «{escrita}» del libro se lee como «{perfil.unidades[escrita]}» "
            f"(traducción del perfil {perfil.nombre}).",
        )
        for escrita, celda in vistas.items()
    ]


def _banda(apu: ApuLeido, perfil: PerfilApuPorHoja) -> list[FilaHallazgo]:
    """AH9: la banda leída de la descripción con el patrón del perfil. Sus cifras se leen con la
    regla del proyecto (`aplicacion.cifras`: coma decimal, punto de miles; arbitraje F5 vial, P9):
    «1.000» es mil, y una cifra que no sigue la regla («1.5») no se adivina."""
    if perfil.patron_banda is None or "descripcion" not in apu.celdas:
        return []
    try:  # la misma lectura que VR4 de la Hoja (prueba de punta a punta del 2026-11-13)
        banda = leer_banda(perfil.patron_banda, apu.titulo)
    except BandaIlegible as error:
        return [
            _hallazgo(
                "AH9",
                "INFO",
                apu.celdas["descripcion"],
                f"{apu.hoja}: la descripción sigue el patrón de la banda de distancia, pero "
                f"{error}.",
            )
        ]
    if banda is None:
        return []
    minimo, maximo = banda
    en_t = perfil.unidades.get(apu.unidad, apu.unidad) == "t"
    return [
        _hallazgo(
            "AH9",
            "INFO",
            apu.celdas["descripcion"],
            f"{apu.hoja}: transporte por banda de distancia, de más de {_es(minimo)} km y hasta "
            f"{_es(maximo)} km (leída de la descripción con el patrón del perfil)"
            + ("; la cantidad va en toneladas." if en_t else "."),
        )
    ]


def _evaluar(
    apu: ApuLeido, perfil: PerfilApuPorHoja
) -> tuple[ApuRecalculado, list[FilaHallazgo], list[TrazaDesperdicio]]:
    hallazgos = [*_unidades(apu, perfil), *_banda(apu, perfil)]
    impreso = apu.guardados[Rotulo.PU]
    celda_pu = apu.rotulos[Rotulo.PU]
    composicion, parametros, trazas = composicion_de_apu_por_hoja(apu, perfil.unidades)
    evaluable = True
    if apu.financiamiento:
        evaluable = False
        hallazgos.append(
            _hallazgo(
                "AH3",
                "INFO",
                apu.celdas.get("financiamiento", celda_pu),
                f"{_ident(apu)} no evaluable: tiene un financiamiento del "
                f"{_pct(apu.financiamiento)} % y Sílice no tiene ese parámetro (reproducirlo "
                "exigiría tocar el núcleo).",
            )
        )
    con_bono = next((x for x in apu.lineas if x.tipo is TipoInsumo.MANO_OBRA and x.bono), None)
    if con_bono is not None:
        evaluable = False
        hallazgos.append(
            _hallazgo(
                "AH2",
                "INFO",
                con_bono.celdas.get("bono", con_bono.celda_cantidad),
                f"{_ident(apu)} no evaluable: la mano de obra trae un bono de {_es(con_bono.bono)} "
                "por renglón y el bono de Sílice es un monto por obrero y día.",
            )
        )
    if apu.impuesto:
        partes = (
            f" ({_pct(apu.impuesto - apu.otros_impuestos)} % y otros impuestos del "
            f"{_pct(apu.otros_impuestos)} %)"
            if apu.otros_impuestos and apu.impuesto != apu.otros_impuestos
            else ""
        )
        hallazgos.append(
            _hallazgo(
                "AH4",
                "ADVERTENCIA",
                apu.celdas.get("impuesto", apu.celdas.get("otros_impuestos", celda_pu)),
                f"{_ident(apu)}: el APU suma un impuesto del {_pct(apu.impuesto)} %{partes}; el "
                "IVA va sobre el total del presupuesto y contarlo también aquí lo cobraría dos "
                "veces.",
            )
        )
    silice = calcular_apu(composicion, parametros).precio_unitario if evaluable else None
    if silice is not None:
        _r(
            silice
        )  # se presenta a dos decimales: si no cabe en la precisión, la hoja no se recalcula
    if silice is not None and not apu.impuesto:
        diferencia = impreso - silice
        tolerancia = Decimal(TOLERANCIA_PRECIO.valor)
        if abs(diferencia) > tolerancia:
            base = (
                f"{_ident(apu)}: el precio unitario impreso es {_es(impreso, 2)} y Sílice lo "
                f"recalcula en {_es(silice, 2)}"
            )
            if abs(impreso - _pu_por_renglon(apu)) <= tolerancia:
                hallazgos.append(
                    _hallazgo(
                        "AH1",
                        "INFO",
                        celda_pu,
                        f"{base}: la diferencia de {_es(abs(diferencia), 2)} se explica por el "
                        "redondeo de cada renglón a dos decimales que hace el programa que exportó "
                        "el libro (Sílice redondea solo al final).",
                        diferencia,
                    )
                )
            else:
                hallazgos.append(
                    _hallazgo(
                        "AH1",
                        "ERROR",
                        celda_pu,
                        f"{base} (diferencia {_es(abs(diferencia), 2)}; tolerancia "
                        f"{_es(tolerancia, 2)}).",
                        diferencia,
                    )
                )
    orden = (TipoInsumo.MATERIAL, TipoInsumo.EQUIPO, TipoInsumo.MANO_OBRA)
    recalculado = ApuRecalculado(
        apu.hoja,
        apu.numero,
        apu.codigo_partida,
        apu.titulo,
        composicion.unidad,
        impreso,
        silice,
        str(celda_pu),
        composicion=composicion,
        parametros=parametros,
        cantidad=apu.cantidad,
        celda_cantidad=str(apu.celdas["cantidad"]) if "cantidad" in apu.celdas else None,
        celdas_precio=tuple(
            str(linea.celdas["precio"])
            for tipo in orden
            for linea in apu.lineas
            if linea.tipo is tipo and "precio" in linea.celdas
        ),
    )
    return recalculado, hallazgos, trazas


# --- el libro de presupuesto ---------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RenglonPresupuesto:
    """Un renglón del libro de presupuesto: su hoja (el frente), su fila (1-base), el número que lo
    enlaza con su APU, el código, la cantidad y el precio unitario escritos (`None` si la celda no
    trae un número). Lo usa también quien lleva el libro a la Hoja."""

    hoja: str
    fila: int
    numero: int
    codigo: str
    cantidad: Decimal | None
    precio: Decimal | None
    columnas: Mapping[str, int]
    encabezado: int  # la fila (1-base) de los encabezados de la hoja

    def celda(self, campo: str) -> str:
        return f"{self.hoja}!{letra(self.columnas[campo])}{self.fila}"

    @property
    def celda_cantidad(self) -> str:
        return self.celda("cantidad")


def _encabezado(filas: Sequence[Sequence[Any]], perfil: PerfilApuPorHoja):
    """(índice, columnas) de la primera fila con los encabezados del número, la cantidad y el
    precio unitario; `None` si no la hay."""
    for i, fila in enumerate(filas):
        columnas: dict[str, int] = {}
        for j, valor in enumerate(fila):
            for campo, variantes in perfil.encabezado_presupuesto.items():
                if campo not in columnas and isinstance(valor, str) and coincide(valor, variantes):
                    columnas[campo] = j
                    break
        if {"numero", "cantidad", "precio_unitario"} <= set(columnas):
            return i, columnas
    return None


def _y(nombres: Sequence[str]) -> str:
    """«A», «A y B», «A, B y C»."""
    return nombres[0] if len(nombres) == 1 else f"{', '.join(nombres[:-1])} y {nombres[-1]}"


def _enumerar(nombres: Sequence[str]) -> str:
    """Los nombres con `_y`, a lo sumo `MAX_NOMBRADAS` y «y n más»."""
    if len(nombres) <= MAX_NOMBRADAS:
        return _y(nombres)
    return f"{', '.join(nombres[:MAX_NOMBRADAS])} y {len(nombres) - MAX_NOMBRADAS} más"


def _faltan(nombre: str, faltan: Sequence[str], hay: Sequence[str]) -> ArchivoRechazado:
    """El libro de presupuesto no tiene las hojas pedidas: dice cuáles faltan y cuáles hay."""
    cuales = f"la hoja {faltan[0]}" if len(faltan) == 1 else f"las hojas {_y(faltan)}"
    if not hay:
        tiene = "no tiene ninguna hoja"
    elif len(hay) == 1:
        tiene = f"su hoja es {hay[0]}"
    else:
        tiene = f"sus hojas son {_enumerar(hay)}"
    return ArchivoRechazado(f"El libro «{nombre}» no tiene {cuales}: {tiene}.")


def _renglones_de_hoja(
    titulo: str, filas: Sequence[Sequence[Any]], nombre: str, perfil: PerfilApuPorHoja
) -> list[RenglonPresupuesto]:
    encabezado = _encabezado(filas, perfil)
    if encabezado is None:
        raise ArchivoRechazado(
            f"El libro «{nombre}», hoja {titulo}: no se encontró la fila de encabezados del "
            "presupuesto (número, cantidad y precio unitario)."
        )
    i, columnas = encabezado

    def celda(fila: Sequence[Any], campo: str) -> Any:
        j = columnas.get(campo)
        return fila[j] if j is not None and j < len(fila) else None

    renglones = []
    for k, fila in enumerate(filas[i + 1 :], start=i + 2):
        numero = numero_de(celda(fila, "numero"))
        if numero is None or numero != numero.to_integral_value():
            continue
        codigo = celda(fila, "codigo")
        cantidad = numero_de(celda(fila, "cantidad"))
        precio = numero_de(celda(fila, "precio_unitario"))
        for campo, valor, que in (
            ("cantidad", cantidad, "la cantidad"),
            ("precio_unitario", precio, "el precio unitario"),
        ):
            if valor is not None and abs(valor) > TOPE_CIFRA:
                raise LibroNoInterpretable(
                    f"{titulo}!{letra(columnas[campo])}{k}: {que} del renglón {int(numero)} pasa "
                    f"del tope de {_es(TOPE_CIFRA)}: Sílice no enlaza el presupuesto con sus APU."
                )
        renglones.append(
            RenglonPresupuesto(
                titulo,
                k,
                int(numero),
                "" if codigo is None else str(codigo).strip(),
                cantidad,
                precio,
                columnas,
                i + 1,
            )
        )
    return renglones


def _renglones(
    datos: bytes, nombre: str, perfil: PerfilApuPorHoja, hojas: Sequence[str]
) -> tuple[tuple[str, ...], list[RenglonPresupuesto]]:
    """Las hojas leídas (con su nombre en el libro, en el orden pedido) y sus renglones. Solo se
    leen esas hojas; si falta alguna, `ArchivoRechazado` dice cuáles faltan y cuáles hay."""
    buscadas = list(dict.fromkeys(normalizar(h) for h in hojas))
    leidas = leer_hojas(datos, nombre, lambda titulo: normalizar(titulo) in buscadas)
    por_nombre = {normalizar(t): t for t in leidas}
    faltan = [h for h in dict.fromkeys(hojas) if normalizar(h) not in por_nombre]
    if faltan:
        raise _faltan(nombre, faltan, list(leidas))
    titulos = tuple(por_nombre[b] for b in buscadas)
    renglones = [r for t in titulos for r in _renglones_de_hoja(t, leidas[t], nombre, perfil)]
    return titulos, renglones


def _primeras(apus: Sequence[ApuLeido]) -> dict[int, ApuLeido]:
    """La primera hoja de cada número de renglón (la que enlaza con el presupuesto)."""
    primeras: dict[int, ApuLeido] = {}
    for apu in apus:
        if apu.numero is not None:
            primeras.setdefault(apu.numero, apu)
    return primeras


def _repetidos(apus: Sequence[ApuLeido]) -> list[FilaHallazgo]:
    primeras = _primeras(apus)
    return [
        _hallazgo(
            "AH10",
            "ADVERTENCIA",
            apu.celdas.get("numero", apu.rotulos[Rotulo.PU]),
            f"{_ident(apu)}: el número de renglón {apu.numero} ya es el de la hoja "
            f"{primeras[apu.numero].hoja}; el presupuesto se enlaza con la primera y esta hoja no "
            "se compara con ningún renglón.",
        )
        for apu in apus
        if apu.numero is not None and primeras[apu.numero] is not apu
    ]


def _sin_prefijo(libro: LibroLeido, perfil: PerfilApuPorHoja) -> list[FilaHallazgo]:
    """AH12: las hojas del libro de APU que no siguen el prefijo del perfil, por su nombre y sin
    leerlas (libro por frentes, D3): un solo hallazgo que las nombra (a lo sumo `MAX_NOMBRADAS`)."""
    otras = [t for t in libro.hojas if not es_hoja_de_apu(perfil, t)]
    if not otras:
        return []
    prefijo = perfil.prefijo_hoja
    if len(otras) == 1:
        texto = (
            f"La hoja {otras[0]} del libro no empieza por «{prefijo}» y no se leyó como APU. Si "
            "es un APU, revise el prefijo del perfil."
        )
    else:
        texto = (
            f"{len(otras)} hojas del libro no empiezan por «{prefijo}» y no se leyeron como APU: "
            f"{_enumerar(otras)}. Si alguna es un APU, revise el prefijo del perfil."
        )
    return [_hallazgo("AH12", "INFO", f"{otras[0]}!A1", texto)]


def _sumas(renglones: Sequence[RenglonPresupuesto]) -> dict[int, tuple[Decimal, list[str]]]:
    """Por número de renglón, la cantidad que suman las hojas que lo traen con cantidad y esas
    hojas, en su orden (libro por frentes, D1)."""
    sumas: dict[int, tuple[Decimal, list[str]]] = {}
    for r in renglones:
        if r.cantidad is None:
            continue
        total, hojas = sumas.get(r.numero, (_CERO, []))
        sumas[r.numero] = (total + r.cantidad, hojas if r.hoja in hojas else [*hojas, r.hoja])
    return sumas


def _otra_obra(
    titulos: Sequence[str],
    renglones: Sequence[RenglonPresupuesto],
    apus: Sequence[ApuLeido],
    perfil: str,
) -> list[FilaHallazgo]:
    """AH11: de los renglones enlazados con cantidad en los dos lados (dos o más), menos de la
    mitad tienen la misma que su APU (ver la cabecera del módulo). Con varias hojas se juzga la
    suma de las hojas."""
    por_numero = _primeras(apus)
    enlazados = [
        r
        for r in renglones
        if r.numero in por_numero
        and r.cantidad is not None
        and por_numero[r.numero].cantidad is not None
    ]
    if len(titulos) == 1:  # cada renglón con su APU, como antes del libro por frentes
        pares = [(r.cantidad, por_numero[r.numero]) for r in enlazados]
    else:
        sumas = _sumas(enlazados)
        pares = [(total, por_numero[n]) for n, (total, _hojas) in sumas.items()]
    casan = sum(1 for total, apu in pares if total == apu.cantidad)
    if len(pares) < 2 or casan * 2 >= len(pares):
        return []
    primero = next((r for r in enlazados if r.hoja == titulos[0]), enlazados[0])
    celda = f"{primero.hoja}!{letra(primero.columnas['cantidad'])}{primero.encabezado}"
    if len(titulos) == 1:
        cuantos = (
            "ninguno tiene" if casan == 0 else f"solo {casan} tiene{'' if casan == 1 else 'n'}"
        )
        texto = (
            f"La hoja {titulos[0]} del presupuesto parece de otra obra: de {len(pares)} renglones "
            f"enlazados con su APU, {cuantos} la misma cantidad. Revise el perfil: {perfil} lee "
            f"la hoja {titulos[0]}."
        )
    else:
        cuantos = "ninguno suma" if casan == 0 else f"solo {casan} suma{'' if casan == 1 else 'n'}"
        texto = (
            f"Las hojas {_y(titulos)} del presupuesto parecen de otra obra: de {len(pares)} "
            f"renglones enlazados con su APU, {cuantos} la misma cantidad. Revise el perfil o las "
            f"hojas elegidas: se leyeron {_y(titulos)}."
        )
    return [_hallazgo("AH11", "ADVERTENCIA", celda, texto)]


def _enlace(
    titulos: Sequence[str], renglones: Sequence[RenglonPresupuesto], apus: Sequence[ApuLeido]
) -> list[FilaHallazgo]:
    por_numero = _primeras(apus)
    tolerancia = Decimal(TOLERANCIA_PRECIO.valor)
    varias = len(titulos) > 1
    sumas = _sumas(renglones)
    hallazgos = []
    vistos: set[int] = set()
    cantidad_vista: set[int] = set()
    for r in renglones:
        quien = f"Renglón {r.numero}" + (f" ({r.codigo})" if r.codigo else "")
        donde = f"{quien}, hoja {r.hoja}" if varias else quien
        apu = por_numero.get(r.numero)
        if apu is None:
            hallazgos.append(
                _hallazgo(
                    "AH7",
                    "ADVERTENCIA",
                    r.celda("numero"),
                    f"{donde}: el presupuesto no tiene hoja de APU con ese número.",
                )
            )
            continue
        vistos.add(r.numero)
        if r.cantidad is not None and apu.cantidad is not None and r.numero not in cantidad_vista:
            # Con una hoja, cada renglón con su APU; con varias, la suma de las hojas, una vez.
            total, hojas = sumas[r.numero] if varias else (r.cantidad, [r.hoja])
            if varias:
                cantidad_vista.add(r.numero)
            if total != apu.cantidad:
                if not varias:
                    lado = f"el presupuesto dice una cantidad de {_es(total)}"
                elif len(hojas) > 1:
                    lado = (
                        f"las hojas {_y(hojas)} del presupuesto suman una cantidad de {_es(total)}"
                    )
                else:
                    lado = f"la hoja {hojas[0]} del presupuesto dice una cantidad de {_es(total)}"
                hallazgos.append(
                    _hallazgo(
                        "AH6",
                        "ADVERTENCIA",
                        r.celda("cantidad"),
                        f"{quien}: {lado} y su APU ({apu.celdas.get('cantidad', apu.hoja)}) dice "
                        f"{_es(apu.cantidad)}.",
                    )
                )
        impreso = apu.guardados[Rotulo.PU]
        if r.precio is not None and abs(r.precio - impreso) > tolerancia:
            hallazgos.append(
                _hallazgo(
                    "AH5",
                    "ERROR",
                    r.celda("precio_unitario"),
                    f"{donde}: el presupuesto dice un precio unitario de {_es(r.precio, 2)} y su "
                    f"APU ({apu.rotulos[Rotulo.PU]}) imprime {_es(impreso, 2)}.",
                    r.precio - impreso,
                )
            )
    for apu in apus:
        if apu.numero is not None and apu.numero not in vistos:
            hallazgos.append(
                _hallazgo(
                    "AH7",
                    "ADVERTENCIA",
                    apu.celdas.get("numero", apu.rotulos[Rotulo.PU]),
                    f"{_ident(apu)}: ninguna línea del presupuesto tiene el renglón {apu.numero}.",
                )
            )
    return hallazgos


def auditar_apu_por_hoja(
    datos: bytes,
    nombre: str,
    *,
    presupuesto: bytes | None = None,
    presupuesto_nombre: str = "",
    perfil: str = "apu_por_hoja",
    carpeta_perfiles: Path | None = None,
    hojas: Sequence[str] | None = None,
) -> ResultadoApuPorHoja:
    """Lee, recalcula e informa el libro de APU `datos` y, si viene, lo enlaza con su libro de
    presupuesto. `perfil` es el nombre del perfil, local o del paquete; `carpeta_perfiles`, la
    carpeta de los perfiles locales de la instalación (ver la cabecera del módulo). `hojas`, si
    viene y no está vacía, son las hojas del presupuesto que se leen en vez de las del perfil
    (libro por frentes, D4), sin distinguir mayúsculas ni espacios de más.

    Deja pasar `ArchivoRechazado` y `LibroNoInterpretable` (el mensaje es para el usuario) y
    `PerfilInvalido` si el perfil no existe o está mal escrito.
    """
    elegido = cargar_perfil_apu_por_hoja(perfil, carpetas_locales(carpeta_perfiles))
    libro = leer_libro_apu_por_hoja(datos, nombre, elegido)
    apus, hallazgos, trazas = [], [*_sin_prefijo(libro, elegido)], []
    for apu in libro.apus:
        try:
            recalculado, propios, suyas = _evaluar(apu, elegido)
        except (InvalidOperation, Overflow) as exc:  # el recálculo no cabe en la precisión
            raise LibroNoInterpretable(
                f"La hoja «{apu.hoja}» da un precio unitario demasiado grande para recalcularlo "
                "con exactitud: revise sus cantidades, sus precios y sus porcentajes."
            ) from exc
        apus.append(recalculado)
        hallazgos.extend(propios)
        trazas.extend(suyas)
    hallazgos.extend(_repetidos(libro.apus))
    titulos: tuple[str, ...] = ()
    renglones: list[RenglonPresupuesto] = []
    if presupuesto is not None:
        pedidas = tuple(h for h in hojas or () if h.strip()) or elegido.hojas_presupuesto
        titulos, renglones = _renglones(
            presupuesto, presupuesto_nombre or "presupuesto", elegido, pedidas
        )
        hallazgos.extend(_otra_obra(titulos, renglones, libro.apus, elegido.nombre))
        hallazgos.extend(_enlace(titulos, renglones, libro.apus))
    return ResultadoApuPorHoja(
        libro=libro,
        perfil=elegido.nombre,
        origen_perfil=elegido.origen,
        apus=tuple(apus),
        hallazgos=tuple(hallazgos),
        trazas=tuple(trazas),
        presupuesto=presupuesto_nombre or None if presupuesto is not None else None,
        hoja_presupuesto=titulos[0] if titulos else None,
        hojas_presupuesto=titulos,
        renglones=tuple(renglones),
    )
