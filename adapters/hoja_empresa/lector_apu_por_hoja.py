"""Lector de un libro con un APU por hoja y solo valores (F5 vial, tarea 4; perfil hermano).

Diseño `docs/especificaciones/2026-11-03-presupuesto-vial-real-design.md` §7.3. Usa la **misma
guardia** (`guardia.verificar_archivo`) y la misma apertura en solo lectura que `lector.py`, y
produce el mismo `LibroLeido` / `ApuLeido` / `LineaApu` del modelo, con sus campos opcionales del
perfil `apu_por_hoja` (desperdicio, bono, coeficiente, número de renglón, prestaciones,
financiamiento, impuesto): una guardia, un modelo y las mismas celdas citables (`HOJA!CELDA`).

- Busca por **rótulos** (`PerfilApuPorHoja`), nunca por fila fija (causa C1 de `lector.py`). La
  cabecera se busca encima del primer bloque; su valor es la primera celda no vacía a la derecha.
- Lee **todos** los renglones de cada bloque, tengan o no número correlativo: un renglón es una
  línea si trae descripción y una cantidad numérica (un filtro por la columna del número perdería
  los renglones sin él y el precio unitario no cuadraría).
- Los porcentajes del pie (prestaciones, administración, utilidad, financiamiento, impuesto) son el
  primer número a la derecha de su rótulo o, si el perfil dice `lado_de_los_porcentajes:
  "izquierda"`, el más cercano a su izquierda (un libro de empresa escribe «p | Administración
  (%) | … | monto»: leer a la derecha tomaba el monto; prueba local del 2026-11-13), y se guardan
  como fracción (250 → 2,5). Faltar la
  administración, la utilidad, el rendimiento o el precio unitario hace la hoja no interpretable
  (`LibroNoInterpretable`, con la hoja y el rótulo); las prestaciones, el financiamiento y el
  impuesto que falten valen 0.
- Un valor que el núcleo no admite (arbitraje F5 vial, P3) también la hace no interpretable, con
  su `HOJA!CELDA`: un rendimiento que no es mayor que cero; una cantidad, un precio, un
  desperdicio o un porcentaje negativos; un coeficiente de depreciación fuera de (0; 1]; y
  (revisión de correcciones, N3) una cantidad, un precio, un desperdicio, un bono, un porcentaje,
  un rendimiento o un precio impreso que pasa de `TOPE_CIFRA` (antes daba un 500 al presentar el
  precio: `Decimal.quantize` pasaba de la precisión).
- Las unidades se leen tal como las escribe el libro: la traducción del perfil la aplica quien
  audita (`fusion`), y cada traducción usada queda dicha en el informe.
- `Decimal` desde texto siempre (NORMAS §2.3), y un `float` con 15 dígitos significativos, la
  precisión que Excel garantiza: el valor en caché de una fórmula llega como doble (0,1 + 0,2 =
  0.30000000000000004) y su ruido daba AH6 falsos (prueba local del 2026-11-13). Solo valores: no
  hay fórmulas que leer.
- **Entrada hostil** (arbitraje F5 vial, P1, y su revisión): solo se leen las hojas del prefijo del
  perfil (y, en el libro de presupuesto, la hoja del presupuesto); de cada una, a lo sumo
  `guardia.MAX_FILAS_HOJA` filas y `guardia.MAX_COLUMNAS_HOJA` columnas (las que justifica
  `MAX_AREA_HOJA`), y una fila o una celda escrita más allá (aunque solo tenga formato) rechaza el
  libro con `ArchivoRechazado`: la `<dimension>` que mira la guardia puede mentir. Cada fila se
  guarda solo hasta su último valor. `LibroLeido.hojas` nombra todas las hojas del libro; `valores`
  cubre solo las celdas de las hojas leídas.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Sequence
from decimal import Decimal
from typing import Any

from adapters.hoja_empresa.guardia import (
    MAX_CELDAS_LIBRO,
    ArchivoRechazado,
    verificar_archivo,
)
from adapters.hoja_empresa.lector import _abrir, filas_acotadas, letra
from adapters.hoja_empresa.modelo import (
    ApuLeido,
    Celda,
    LibroLeido,
    LibroNoInterpretable,
    LineaApu,
    ParametrosLibro,
    Portada,
    Rotulo,
    TipoInsumo,
    clave,
)
from adapters.hoja_empresa.perfil import coincide, normalizar
from adapters.hoja_empresa.perfil_apu_por_hoja import (
    BLOQUES,
    Bloque,
    PerfilApuPorHoja,
    cargar_perfil_apu_por_hoja,
)

__all__ = ["TOPE_CIFRA", "leer_hojas", "leer_libro_apu_por_hoja", "letra", "numero_de"]

_CERO = Decimal(0)
_CIEN = Decimal(100)
_TIPOS = {
    "materiales": TipoInsumo.MATERIAL,
    "equipos": TipoInsumo.EQUIPO,
    "mano_obra": TipoInsumo.MANO_OBRA,
}
Filas = list[list[Any]]
#: SUPUESTO_DECLARADO (revisión de correcciones de F5/F7/F8, N3): lo más que puede valer una cifra
#: del libro, un billón. Ninguna cantidad, precio, porcentaje ni rendimiento de un APU se le acerca,
#: y por debajo de él cada renglón cabe holgado en los 28 dígitos del `Decimal` de Python con dos
#: decimales. Lo que el tope no ataja (muchos renglones grandes, porcentajes enormes) lo ataja quien
#: recalcula (`fusion.apu_por_hoja`) diciendo la hoja.
TOPE_CIFRA = Decimal(10) ** 12


def numero_de(valor: Any) -> Decimal | None:
    """El `Decimal` de una celda numérica (no un booleano); `None` si no lo es. Un `float` se toma
    con 15 dígitos significativos, la precisión de Excel (sin el ruido binario del doble)."""
    if isinstance(valor, bool) or not isinstance(valor, (int, float, Decimal)):
        return None
    numero = Decimal(format(valor, ".15g") if isinstance(valor, float) else str(valor))
    return numero if numero.is_finite() else None


def _cifra(valor: Decimal) -> str:
    """Coma decimal y punto de miles, sin ceros de más: para los mensajes."""
    texto = format(valor.normalize(), ",f")
    return texto.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def _invalido(hoja: str, celda: str, que: str) -> LibroNoInterpretable:
    """Un valor que el núcleo no admite: la hoja no se recalcula y el mensaje dice la celda."""
    return LibroNoInterpretable(
        f"{clave(hoja, celda)}: {que}: Sílice no recalcula la hoja «{hoja}»."
    )


def _acotar(hoja: str, celda: str, que: str, valor: Decimal) -> None:
    """`LibroNoInterpretable` con la celda si `valor` pasa de `TOPE_CIFRA`."""
    if abs(valor) > TOPE_CIFRA:
        raise _invalido(hoja, celda, f"{que} pasa del tope de {_cifra(TOPE_CIFRA)}")


def _texto(valor: Any) -> str:
    if valor is None:
        return ""
    if isinstance(valor, float) and valor.is_integer():
        return str(int(valor))
    return str(valor).strip()


def _filas(hoja: Any, nombre: str, cuenta: list[int]) -> Filas:
    """Las filas de valores de una hoja de solo lectura, cada una solo hasta su último valor,
    dentro de los topes de la guardia (`lector.filas_acotadas`, la misma regla del lector del
    libro conocido): lo materializado nunca pasa de `MAX_AREA_HOJA` celdas y una fila."""
    filas: Filas = []
    for fila in filas_acotadas(hoja, nombre, cuenta, MAX_CELDAS_LIBRO, values_only=True):
        fin = len(fila)
        while fin and fila[fin - 1] is None:
            fin -= 1
        filas.append(list(fila[:fin]))
    return filas


def leer_hojas(
    datos: bytes, nombre: str, incluir: Callable[[str], bool] | None = None
) -> dict[str, Filas]:
    """Las hojas del libro, en su orden, cada una como lista de filas de valores, con la guardia de
    siempre. Solo se leen las hojas cuyo título acepta `incluir` (todas, sin él); las demás quedan
    con la lista vacía: se sabe que existen, pero sus celdas no se materializan."""
    verificar_archivo(datos, nombre)
    libro = _abrir(datos, nombre, data_only=True)
    cuenta = [0]  # celdas materializadas en el libro entero (`MAX_CELDAS_LIBRO`)
    try:
        return {
            hoja.title: (
                _filas(hoja, nombre, cuenta) if incluir is None or incluir(hoja.title) else []
            )
            for hoja in libro.worksheets
        }
    except ArchivoRechazado:
        raise
    except Exception as exc:  # un XML dañado aparece al recorrer la hoja en solo lectura
        raise ArchivoRechazado(
            f"No se pudo leer el libro «{nombre}»: alguna hoja está dañada."
        ) from exc
    finally:
        libro.close()


def _primera(fila: Sequence[Any]) -> tuple[int, Any] | None:
    for j, valor in enumerate(fila):
        if valor is not None and _texto(valor):
            return j, valor
    return None


def _rotulo(
    filas: Filas, variantes: Sequence[str], hasta: int | None = None
) -> tuple[int, int] | None:
    """(fila, columna) de la primera celda de texto que empieza por una de las variantes."""
    for i, fila in enumerate(filas[:hasta]):
        for j, valor in enumerate(fila):
            if isinstance(valor, str) and coincide(valor, variantes):
                return i, j
    return None


def _a_la_derecha(fila: Sequence[Any], desde: int, numerico: bool) -> tuple[int, Any] | None:
    for j in range(desde + 1, len(fila)):
        valor = fila[j]
        if numerico and numero_de(valor) is not None:
            return j, numero_de(valor)
        if not numerico and valor is not None and _texto(valor):
            return j, valor
    return None


def _a_la_izquierda(fila: Sequence[Any], hasta: int) -> tuple[int, Any] | None:
    """El número más cercano a la izquierda de la columna `hasta`."""
    for j in range(min(hasta, len(fila)) - 1, -1, -1):
        if numero_de(fila[j]) is not None:
            return j, numero_de(fila[j])
    return None


def _titulo(filas: Filas, bloque: Bloque) -> int | None:
    titulos = {normalizar(t) for t in bloque.titulo}
    for i, fila in enumerate(filas):
        primera = _primera(fila)
        if primera is not None and normalizar(_texto(primera[1])) in titulos:
            return i
    return None


def _columnas(fila: Sequence[Any], bloque: Bloque) -> dict[str, int]:
    columnas: dict[str, int] = {}
    for j, valor in enumerate(fila):
        for campo, variantes in bloque.columnas.items():
            if campo not in columnas and isinstance(valor, str) and coincide(valor, variantes):
                columnas[campo] = j
                break
    return columnas


def _lineas(hoja: str, filas: Filas, perfil: PerfilApuPorHoja) -> list[LineaApu]:
    titulos = {i for b in perfil.bloques.values() if (i := _titulo(filas, b)) is not None}
    lineas: list[LineaApu] = []
    for nombre_bloque in BLOQUES:
        bloque = perfil.bloques[nombre_bloque]
        inicio = _titulo(filas, bloque)
        if inicio is None or inicio + 1 >= len(filas):
            continue
        columnas = _columnas(filas[inicio + 1], bloque)
        faltan = [c for c in ("descripcion", "cantidad", "precio") if c not in columnas]
        if faltan:
            raise LibroNoInterpretable(
                f"La hoja «{hoja}»: el bloque «{bloque.titulo[0]}» no tiene las columnas "
                f"{', '.join(bloque.columnas[c][0] for c in faltan)} en la fila {inicio + 2}."
            )
        for i in range(inicio + 2, len(filas)):
            fila = filas[i]
            primera = _primera(fila)
            if i in titulos or (primera is not None and coincide(_texto(primera[1]), bloque.fin)):
                break
            linea = _linea(hoja, i, fila, columnas, _TIPOS[nombre_bloque])
            if linea is not None:
                lineas.append(linea)
    return lineas


def _celda_de(fila: Sequence[Any], columna: int | None) -> Any:
    return fila[columna] if columna is not None and columna < len(fila) else None


def _linea(
    hoja: str, i: int, fila: Sequence[Any], columnas: dict[str, int], tipo: TipoInsumo
) -> LineaApu | None:
    descripcion = _texto(_celda_de(fila, columnas["descripcion"]))
    cantidad = numero_de(_celda_de(fila, columnas["cantidad"]))
    if not descripcion or cantidad is None:
        return None
    precio = numero_de(_celda_de(fila, columnas["precio"])) or _CERO
    desperdicio = numero_de(_celda_de(fila, columnas.get("desperdicio"))) or _CERO
    depreciacion = numero_de(_celda_de(fila, columnas.get("depreciacion")))
    bono = numero_de(_celda_de(fila, columnas.get("bono"))) or _CERO

    def celda(campo: str) -> str:
        return f"{letra(columnas[campo])}{i + 1}"

    montos = (
        ("cantidad", cantidad, "la cantidad"),
        ("precio", precio, "el precio"),
        ("desperdicio", desperdicio, "el desperdicio"),
    )
    for campo, valor, nombre in (*montos, ("bono", bono, "el bono")):
        if campo in columnas:
            _acotar(hoja, celda(campo), f"{nombre} de «{descripcion}»", valor)
    for campo, valor, nombre in montos:
        if valor < 0:
            negativa = "negativa" if nombre.startswith("la ") else "negativo"
            raise _invalido(
                hoja,
                celda(campo),
                f"{nombre} de «{descripcion}» es {_cifra(valor)} y no puede ser {negativa}",
            )
    if depreciacion is not None and not _CERO < depreciacion <= 1:
        raise _invalido(
            hoja,
            celda("depreciacion"),
            f"el coeficiente de depreciación de «{descripcion}» es {_cifra(depreciacion)} y debe "
            "ser mayor que 0 y no pasar de 1",
        )
    numero = _celda_de(fila, columnas.get("numero"))
    col_codigo = columnas.get("numero", columnas["descripcion"])
    return LineaApu(
        tipo=tipo,
        codigo=_texto(numero),
        descripcion=descripcion,
        unidad=_texto(_celda_de(fila, columnas.get("unidad"))),
        cantidad=cantidad,
        precio=precio,
        celda_codigo=Celda(hoja, f"{letra(col_codigo)}{i + 1}"),
        celda_cantidad=Celda(hoja, f"{letra(columnas['cantidad'])}{i + 1}"),
        desperdicio=desperdicio,
        bono=bono,
        depreciacion=depreciacion,
        celdas={
            campo: Celda(hoja, f"{letra(columnas[campo])}{i + 1}")
            for campo in ("unidad", "desperdicio", "bono")
            if campo in columnas
        },
    )


def _leer_apu(hoja: str, filas: Filas, perfil: PerfilApuPorHoja) -> ApuLeido:
    primeros = [i for b in perfil.bloques.values() if (i := _titulo(filas, b)) is not None]
    tope = min(primeros) if primeros else None
    celdas: dict[str, Celda] = {}
    cabecera: dict[str, Any] = {}
    for campo, variantes in perfil.cabecera.items():
        donde = _rotulo(filas, variantes, tope)
        if donde is None:
            continue
        i, j = donde
        numerico = campo in ("numero", "cantidad", "rendimiento")
        valor = _a_la_derecha(filas[i], j, numerico)
        if valor is not None:
            cabecera[campo] = valor[1]
            celdas[campo] = Celda(hoja, f"{letra(valor[0])}{i + 1}")

    def exigir(campo: str, que: str, variantes: Sequence[str]) -> Any:
        if campo not in cabecera:
            raise LibroNoInterpretable(
                f"La hoja «{hoja}» no dice {que} (rótulo «{variantes[0]}»): Sílice no la adivina."
            )
        return cabecera[campo]

    descripcion = _texto(exigir("descripcion", "la descripción", perfil.cabecera["descripcion"]))
    unidad = _texto(exigir("unidad", "la unidad", perfil.cabecera["unidad"]))
    rendimiento = exigir("rendimiento", "el rendimiento", perfil.cabecera["rendimiento"])
    _acotar(hoja, celdas["rendimiento"].ref, "el rendimiento", rendimiento)
    if "cantidad" in cabecera:
        _acotar(hoja, celdas["cantidad"].ref, "la cantidad de la partida", cabecera["cantidad"])
    if rendimiento <= 0:
        raise _invalido(
            hoja,
            celdas["rendimiento"].ref,
            f"el rendimiento es {_cifra(rendimiento)} y debe ser mayor que cero",
        )
    porcentajes: dict[str, Decimal] = {}
    for campo, variantes in perfil.porcentajes.items():
        donde = _rotulo(filas, variantes)
        if donde is None:
            valor = None
        elif perfil.lado_de_los_porcentajes == "izquierda":
            valor = _a_la_izquierda(filas[donde[0]], donde[1])
        else:
            valor = _a_la_derecha(filas[donde[0]], donde[1], True)
        if valor is None:
            if campo in ("administracion", "utilidad"):
                raise LibroNoInterpretable(
                    f"La hoja «{hoja}» no dice el porcentaje de {variantes[0]}: sin él no se "
                    "recalcula el precio unitario."
                )
            porcentajes[campo] = _CERO
            continue
        assert donde is not None
        celdas[campo] = Celda(hoja, f"{letra(valor[0])}{donde[0] + 1}")
        _acotar(hoja, celdas[campo].ref, f"el porcentaje de {variantes[0]}", valor[1])
        if valor[1] < 0:
            raise _invalido(
                hoja,
                celdas[campo].ref,
                f"el porcentaje de {variantes[0]} es {_cifra(valor[1])} y no puede ser negativo",
            )
        porcentajes[campo] = valor[1] / _CIEN
    donde = _rotulo(filas, perfil.precio_unitario)
    pu = None if donde is None else _a_la_derecha(filas[donde[0]], donde[1], True)
    if pu is None or donde is None:
        raise LibroNoInterpretable(
            f"La hoja «{hoja}» no tiene el {perfil.precio_unitario[0]} impreso: sin él no hay con "
            "qué comparar el recálculo."
        )
    _acotar(hoja, f"{letra(pu[0])}{donde[0] + 1}", "el precio unitario impreso", pu[1])
    numero = cabecera.get("numero")
    return ApuLeido(
        hoja=hoja,
        titulo=descripcion,
        fila_presupuesto=None,
        codigo_partida=_texto(cabecera.get("codigo")),
        unidad=unidad,
        rendimiento=rendimiento,
        lineas=tuple(_lineas(hoja, filas, perfil)),
        escombro=_CERO,
        administracion=porcentajes["administracion"],
        utilidad=porcentajes["utilidad"],
        herramientas=_CERO,
        rotulos={Rotulo.PU: Celda(hoja, f"{letra(pu[0])}{donde[0] + 1}")},
        guardados={Rotulo.PU: pu[1]},
        numero=None if numero is None else int(numero),
        cantidad=cabecera.get("cantidad"),
        prestaciones=porcentajes["prestaciones"],
        financiamiento=porcentajes["financiamiento"],
        impuesto=porcentajes["impuesto"],
        celdas=celdas,
    )


def leer_libro_apu_por_hoja(
    datos: bytes, nombre: str, perfil: PerfilApuPorHoja | None = None
) -> LibroLeido:
    """El libro con un APU por hoja como `LibroLeido` (perfil `apu_por_hoja`).

    `ArchivoRechazado` si la guardia lo rechaza, si no se puede abrir o si no tiene ninguna hoja de
    APU; `LibroNoInterpretable` si una hoja de APU no trae lo que hace falta para recalcularla.
    """
    perfil = perfil or cargar_perfil_apu_por_hoja()
    prefijo = normalizar(perfil.prefijo_hoja)

    def es_apu(titulo: str) -> bool:
        return normalizar(titulo).startswith(prefijo)

    hojas = leer_hojas(datos, nombre, es_apu)
    apus = tuple(
        _leer_apu(titulo, filas, perfil) for titulo, filas in hojas.items() if es_apu(titulo)
    )
    if not apus:
        raise ArchivoRechazado(
            f"El libro «{nombre}» no tiene ninguna hoja de APU (hojas cuyo nombre empieza por "
            f"«{perfil.prefijo_hoja}»): no parece un libro con un APU por hoja."
        )
    valores = {
        clave(titulo, f"{letra(j)}{i + 1}"): valor if numero_de(valor) is None else numero_de(valor)
        for titulo, filas in hojas.items()
        for i, fila in enumerate(filas)
        for j, valor in enumerate(fila)
        if valor is not None
    }
    return LibroLeido(
        nombre=nombre,
        sha256=hashlib.sha256(datos).hexdigest(),
        hojas=tuple(hojas),
        portada=Portada(),
        parametros=ParametrosLibro(_CERO, _CERO, _CERO, _CERO, _CERO, _CERO, _CERO, _CERO),
        insumos=(),
        apus=apus,
        partidas=(),
        filas_especiales=(),
        totales={},
        nombres={},
        vinculos_externos=(),
        formulas={},
        valores=valores,
        perfil=perfil.nombre,
    )
