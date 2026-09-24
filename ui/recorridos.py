"""Los recorridos guiados de la interfaz (sprint de UI, RF-37 y RF-41).

Un recorrido es una secuencia de pasos con un proposito. Se declara aqui **una sola vez** y de esta
declaracion salen sus cuatro consumidores: la pantalla de Inicio que los ofrece, el marco de
`ui/app.py` que pinta en que paso esta el usuario y su boton «Siguiente», y el guion de prueba
manual CP-07 (`docs/guion_prueba_arenia.md`). Escribir el camino en cada pantalla seria repetirlo
cuatro veces (principio DRY, CLAUDE.md §2).

Sin Streamlit y sin base de datos: se prueba como funcion pura. La integridad de enlaces —que cada
`Paso.pagina` sea la ruta URL de una pagina registrada en `ui.app.PAGINAS`, y de una pagina de la
seccion Trabajo para que el modo entrega no la esconda— la vigila `tests/unit/test_ui_app.py`: este
modulo no importa `ui.app`, que si importa Streamlit.
"""

from __future__ import annotations

from dataclasses import dataclass

#: Ruta URL de la pantalla de Inicio (el nombre de su modulo, `ui/paginas/inicio.py`). El Inicio no
#: es un paso de ningun recorrido: es de donde salen todos.
RUTA_INICIO = "inicio"

NOMBRE_DEMOSTRACION = "Ver la demostracion auditada"
NOMBRE_PRESUPUESTO = "Armar un presupuesto"
NOMBRE_PRECIOS = "Actualizar precios"


@dataclass(frozen=True, slots=True)
class Paso:
    """Un paso: la pantalla donde ocurre, que hacer en ella y como se sabe que termino."""

    titulo: str
    pagina: str  # ruta URL de una pagina registrada en ui.app.PAGINAS
    que_hacer: str
    senal_de_exito: str


@dataclass(frozen=True, slots=True)
class Recorrido:
    """Una secuencia de pasos con un proposito, que no pasa dos veces por la misma pantalla."""

    nombre: str
    proposito: str
    pasos: tuple[Paso, ...]

    def __post_init__(self) -> None:
        if not self.pasos:
            raise ValueError(f"el recorrido {self.nombre!r} debe tener al menos un paso")
        paginas = [paso.pagina for paso in self.pasos]
        if RUTA_INICIO in paginas:
            raise ValueError(
                f"el recorrido {self.nombre!r} no puede tener un paso en el Inicio: sale de el"
            )
        if len(set(paginas)) != len(paginas):
            raise ValueError(
                f"el recorrido {self.nombre!r} pasa dos veces por la misma pantalla: el paso "
                "siguiente seria ambiguo"
            )

    def posicion(self, ruta: str) -> int | None:
        """Numero del paso (desde 1) que ocurre en la pantalla `ruta`.

        `None` si la pantalla no es del recorrido.
        """
        for numero, paso in enumerate(self.pasos, start=1):
            if paso.pagina == ruta:
                return numero
        return None


RECORRIDOS: tuple[Recorrido, ...] = (
    Recorrido(
        NOMBRE_DEMOSTRACION,
        "Para un primer contacto: recorre el caso de demostracion ya cargado hasta el informe de "
        "auditoria y el presupuesto en Excel.",
        (
            Paso(
                "Ver el catalogo del caso",
                "catalogo",
                "Revise las partidas DEMO-01-INST, DEMO-02-VALV y DEMO-03-PRUEBA y los precios "
                "vigentes de sus insumos.",
                "La tabla de partidas muestra las tres partidas DEMO.",
            ),
            Paso(
                "Elaborar, auditar y exportar",
                "componer",
                "Baje a «Cantidades de obra», agregue una fila por partida con su cantidad y su "
                "origen, pulse «Elaborar y auditar» y despues «Exportar a Excel».",
                "Se descarga presupuesto_<codigo>.xlsx y el informe de auditoria dice cuantos "
                "hallazgos tiene.",
            ),
        ),
    ),
    Recorrido(
        NOMBRE_PRESUPUESTO,
        "Para quien presupuesta: compone las partidas que falten y elabora su propio "
        "presupuesto auditado desde un computo.",
        (
            Paso(
                "Ver que partidas hay",
                "catalogo",
                "Compruebe que partidas e insumos ya existen en el caso abierto.",
                "Sabe que partidas tendra que componer.",
            ),
            Paso(
                "Componer las partidas que falten",
                "componer",
                "Declare la cabecera, las tres tablas de insumos y el rendimiento con sus "
                "condiciones; pulse «Guardar composicion».",
                "La partida guardada aparece en el catalogo con su precio unitario.",
            ),
            Paso(
                "Elaborar el presupuesto",
                "elaborar",
                "Elija el dominio, cargue su computo en CSV, pulse «Extraer computo» y despues "
                "«Elaborar presupuesto»; descargue el Excel.",
                "Se descarga el libro con su hoja de auditoria.",
            ),
        ),
    ),
    Recorrido(
        NOMBRE_PRECIOS,
        "Para quien mantiene el catalogo: carga una lista de precios nueva, revalora un "
        "presupuesto guardado y revisa el comparativo.",
        (
            Paso(
                "Ver los precios vigentes",
                "catalogo",
                "Revise los insumos y su precio vigente antes de cambiarlos.",
                "Sabe que precios va a reemplazar.",
            ),
            Paso(
                "Cargar la lista y revalorar",
                "actualizacion",
                "Cargue la lista nueva (CSV o XLSX con columnas tipo, insumo, unidad y precio) y "
                "pulse «Revalorar presupuesto».",
                "Aparecen el comparativo por partida y la auditoria de la version nueva.",
            ),
        ),
    ),
)


def recorrido_por_nombre(nombre: str | None) -> Recorrido | None:
    """El recorrido de ese nombre; `None` si no hay nombre o no corresponde a ninguno."""
    for recorrido in RECORRIDOS:
        if recorrido.nombre == nombre:
            return recorrido
    return None


def paso_siguiente(recorrido: Recorrido | None, ruta: str) -> Paso | None:
    """El paso que sigue a la pantalla `ruta` dentro de `recorrido`.

    Desde el Inicio, el primero. Desde el ultimo paso, o desde una pantalla que no es del
    recorrido, ninguno (RF-41): una pantalla ajena al recorrido no ofrece paso siguiente.
    """
    if recorrido is None:
        return None
    if ruta == RUTA_INICIO:
        return recorrido.pasos[0]
    posicion = recorrido.posicion(ruta)
    if posicion is None or posicion == len(recorrido.pasos):
        return None
    return recorrido.pasos[posicion]
