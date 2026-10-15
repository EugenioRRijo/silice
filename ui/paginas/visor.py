"""Pagina del visor 3D: modelo IFC teselado junto a la tabla elemento <-> partida (Sesion F.1, T7).

Carga un archivo `.ifc` (por defecto ofrece `data/samples/tanquilla.ifc`, la muestra de T5), lo
tesela con `ui.visor3d.mallas` y renderiza el resultado con three.js dentro de un
`st.components.v1.html` (three.js va incrustado desde `ui/estaticos/`, version fija: cdnjs dejo
de publicar el build UMD `three.min.js` despues de r147 aproximadamente, por eso se fija
`r128`, la ultima etiqueta `rNNN` que si trae ese archivo). `OrbitControls` no viene en
`three.min.js` y no esta publicado por separado en cdnjs para esta version: en vez de
reimplementar un control de orbita completo, el visor gira el modelo automaticamente sobre su
propio centro (alcance que el brief permite explicitamente).

Al lado se muestra la misma tabla GlobalId <-> codigo_partida <-> cantidad que produce
`AdaptadorCivilIFC` sobre el mismo archivo (adapters/civil/ifc.py, T6): el visor no reemplaza la
trazabilidad de la regla R1, la ilustra.

`ifcopenshell` (y, por lo tanto, `adapters.civil.ifc`, que lo importa a nivel de modulo) se cargan
de forma perezosa en `_cargar_dependencias_civiles()`, no al importar este modulo: antes de esta
pagina ninguna de las cinco pantallas registradas en `ui/app.py` requeria el extra `civil`, y un
import incondicional aqui rompería `ui.app` (y las cinco pantallas sin relacion con IFC) en
cualquier entorno instalado solo con `uv sync --extra ui --extra api`. Si el extra no esta
instalado, `render()` lo detecta y muestra un mensaje con `st.error`, mismo criterio que usa
`api/rutas/computos.py` para `ImportError` (400 con mensaje claro) en vez de una traza cruda.

Pruebas: la teselacion y el aislamiento del import perezoso, en `tests/unit/test_visor3d.py`; que
la pagina se importa sin efectos, en `tests/unit/test_ui_importable.py`. La pagina misma, en
`tests/unit/test_ui_visor_orden.py` (fase C5, O-1): con dobles, que el adaptador extrae antes de
que `mallas` tesele, y que si el adaptador rechaza el archivo `mallas` nunca lo abre; y de punta a
punta, un IFC ilegible real en `tmp_path` (binario o con la cabecera STEP danada) con el adaptador
y `mallas` reales, que se muestra como un `st.error` y no deja excepciones no atrapables.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING

import streamlit as st
from pandas import DataFrame

from core.contracts import ItemComputo
from core.verification.informe import DECIMALES_PRESENTACION
from core.verification.texto import formatear_decimal
from seguridad.permisos import Accion
from ui import sesion as ui_sesion
from ui.subidas import guardar_subida
from ui.visor3d import mallas

if TYPE_CHECKING:
    from adapters.civil.ifc import AdaptadorCivilIFC

RUTA_POR_DEFECTO = "data/samples/tanquilla.ifc"
ALTURA_VISOR = 480
RUTA_THREE_JS = Path(__file__).resolve().parents[1] / "estaticos" / "three.min.js"
VERSION_THREE_JS = "r128"
TAMANO_THREE_JS = 603_445
SHA256_THREE_JS = "9274bbcec8d96168626c732b5d31c775aa8cfb7eaa0599bec0c175908a2c1ce2"
_MENSAJE_SIN_EXTRA_CIVIL = (
    "El visor 3D necesita el extra 'civil' (ifcopenshell): instala con "
    "'uv sync --extra civil' y vuelve a intentar."
)


def _cargar_dependencias_civiles() -> tuple[ModuleType, type[AdaptadorCivilIFC]]:
    """Importa `ifcopenshell` y `AdaptadorCivilIFC` solo cuando el visor se usa de verdad.

    Perezoso a proposito (NORMAS.md §9, seccion "import perezoso" de este modulo): asi `ui.app` y
    esta pagina siguen siendo importables sin el extra `civil`. Relanza `ImportError` tal cual si
    ifcopenshell no esta instalado; `render()` decide como mostrarlo (`st.error`).
    """
    import ifcopenshell

    from adapters.civil.ifc import AdaptadorCivilIFC

    return ifcopenshell, AdaptadorCivilIFC


def render() -> None:
    """Selector de archivo IFC; visor three.js y tabla de cómputo lado a lado."""
    ui_sesion.exigir(Accion.EDITAR_HOJA)
    st.caption(
        "Carga un modelo IFC y compara su geometria con el cómputo que extrae el adaptador civil: "
        "cada malla del visor corresponde a una fila de la tabla, unidas por el GlobalId (regla R1 "
        "de verificacion, NORMAS.md §7)."
    )

    archivo = st.file_uploader("Modelo IFC (.ifc)", type=["ifc"])
    if archivo is None:
        st.caption(f"Sin archivo cargado: se muestra la muestra por defecto ({RUTA_POR_DEFECTO}).")
        _render_desde_ruta(Path(RUTA_POR_DEFECTO))
        return

    with tempfile.TemporaryDirectory() as carpeta:
        try:
            ruta_temporal = guardar_subida(carpeta, archivo)
        except ValueError as error:
            st.error(f"{str(error).rstrip('.')}. Renombre el archivo y vuelva a subirlo.")
            return
        _render_desde_ruta(ruta_temporal)


def _render_desde_ruta(ruta: Path) -> None:
    try:
        ifcopenshell, adaptador_civil_ifc = _cargar_dependencias_civiles()
    except ImportError:
        st.error(_MENSAJE_SIN_EXTRA_CIVIL)
        return

    if not ruta.exists():
        st.error(f"No se encontro el archivo {ruta}.")
        return

    # Errores esperados al abrir o leer el `.ifc`: sin permisos (`OSError`), contenido que no es
    # un IFC valido (`ifcopenshell.Error`, por ejemplo una cabecera SPF corrupta) y los que ya usan
    # las demas paginas para un archivo mal formado o incompleto (`LookupError`, `ValueError`,
    # `ArithmeticError`; ver `ui/paginas/elaborar.py`).
    errores_lectura_ifc = (OSError, ifcopenshell.Error, LookupError, ValueError, ArithmeticError)
    try:
        # Primero el adaptador: rechaza un archivo ilegible con `ValueError` sin llegar a
        # `ifcopenshell.open`, que `mallas` llama y que ante un archivo que no es STEP deja una
        # excepcion no atrapable (O-1 de la revision de la pista P de C5).
        items = adaptador_civil_ifc().extraer(ruta)
        mallas_encontradas = mallas(ruta)
    except errores_lectura_ifc as error:
        st.error(str(error))
        return

    columna_visor, columna_tabla = st.columns([2, 1])
    with columna_visor:
        if mallas_encontradas:
            st.components.v1.html(_html_visor(mallas_encontradas), height=ALTURA_VISOR)
        else:
            st.info("El modelo no tiene elementos con geometria propia para renderizar.")
    with columna_tabla:
        _mostrar_tabla(items)


def _mostrar_tabla(items: list[ItemComputo]) -> None:
    st.subheader("Elemento <-> partida <-> cantidad")
    if not items:
        st.info("El modelo no tiene elementos con Pset_APU: no hay cómputo civil que extraer.")
        return

    tabla = DataFrame(
        [
            {
                "global_id": item.origen_id,
                "codigo_partida": item.codigo_partida,
                "descripcion": item.descripcion,
                "unidad": item.unidad,
                "cantidad": formatear_decimal(item.cantidad, DECIMALES_PRESENTACION),
            }
            for item in items
        ]
    )
    st.dataframe(tabla, hide_index=True)


def _html_visor(mallas_encontradas: list[dict]) -> str:
    """Incrusta el visor three.js con las mallas ya teseladas. three.js va dentro del HTML
    (RP10-5): el visor no pide nada fuera del equipo (RNF-08)."""
    # El `GlobalId` sale del `.ifc` subido: un `</script>` en él cerraría el bloque de datos
    # (auditoría final). `<\/` es el mismo texto para JavaScript y para JSON.
    datos = json.dumps(mallas_encontradas).replace("</", "<\\/")
    return (
        _PLANTILLA_HTML.replace("__DATOS__", datos)
        .replace("__ALTURA__", str(ALTURA_VISOR))
        .replace("__THREE__", RUTA_THREE_JS.read_text(encoding="utf-8"))
    )


_PLANTILLA_HTML = """
<div id="contenedor-visor" style="width:100%;height:__ALTURA__px;"></div>
<script>__THREE__</script>
<script>
(function () {
  var datos = __DATOS__;
  var contenedor = document.getElementById("contenedor-visor");
  var ancho = contenedor.clientWidth || 800;
  var alto = __ALTURA__;

  var escena = new THREE.Scene();
  escena.background = new THREE.Color(0xf2f2f2);

  var camara = new THREE.PerspectiveCamera(45, ancho / alto, 0.001, 1000);
  var renderizador = new THREE.WebGLRenderer({ antialias: true });
  renderizador.setSize(ancho, alto);
  contenedor.appendChild(renderizador.domElement);

  escena.add(new THREE.AmbientLight(0xffffff, 0.6));
  var luz = new THREE.DirectionalLight(0xffffff, 0.8);
  luz.position.set(2, 3, 2);
  escena.add(luz);

  var minimo = [Infinity, Infinity, Infinity];
  var maximo = [-Infinity, -Infinity, -Infinity];
  var colores = [0x3d7ea6, 0xa63d5c, 0x5ca63d, 0xa6863d, 0x7a3da6];
  var grupo = new THREE.Group();

  datos.forEach(function (malla, indice) {
    var geometria = new THREE.BufferGeometry();
    geometria.setAttribute("position", new THREE.Float32BufferAttribute(malla.vertices, 3));
    geometria.setIndex(malla.caras);
    geometria.computeVertexNormals();
    var material = new THREE.MeshStandardMaterial({
      color: colores[indice % colores.length],
      side: THREE.DoubleSide,
    });
    var malla3d = new THREE.Mesh(geometria, material);
    malla3d.name = malla.global_id;
    grupo.add(malla3d);

    for (var i = 0; i < malla.vertices.length; i += 3) {
      for (var k = 0; k < 3; k++) {
        var v = malla.vertices[i + k];
        if (v < minimo[k]) minimo[k] = v;
        if (v > maximo[k]) maximo[k] = v;
      }
    }
  });

  var centro = new THREE.Vector3(
    (minimo[0] + maximo[0]) / 2,
    (minimo[1] + maximo[1]) / 2,
    (minimo[2] + maximo[2]) / 2
  );
  var radio = Math.max(
    maximo[0] - minimo[0],
    maximo[1] - minimo[1],
    maximo[2] - minimo[2],
    0.1
  );

  var pivote = new THREE.Group();
  grupo.position.set(-centro.x, -centro.y, -centro.z);
  pivote.position.set(centro.x, centro.y, centro.z);
  pivote.add(grupo);
  escena.add(pivote);

  camara.position.set(
    centro.x + radio * 1.6,
    centro.y + radio * 1.3,
    centro.z + radio * 1.6
  );
  camara.lookAt(centro);

  window.addEventListener("resize", function () {
    var nuevoAncho = contenedor.clientWidth || ancho;
    camara.aspect = nuevoAncho / alto;
    camara.updateProjectionMatrix();
    renderizador.setSize(nuevoAncho, alto);
  });

  (function animar() {
    requestAnimationFrame(animar);
    pivote.rotation.y += 0.006;
    renderizador.render(escena, camara);
  })();
})();
</script>
"""
