# Licencias de `ifctester` y de `bcf-client` (RP-6, S3-0)

Sílice es propietaria con todos los derechos reservados (P9). `ifctester` (la validación de IDS
del IFC, S3 §11.2) arrastra una dependencia con copyleft fuerte. Este documento fija qué se
sabe, qué se decide y qué prueba lo vigila. **No es asesoría legal**: la decisión de incluir el
extra `ifc` en el instalador queda a Eugenio, con el dictamen que él consiga.

## Lo verificado (2026-10-11, entorno bloqueado por `uv.lock`)

| Distribución | Versión | Licencia declarada en sus metadatos | Quién la pide |
|---|---|---|---|
| ifctester 0.8.5 | 0.8.5 | LGPLv3+ (`GNU Lesser General Public License v3 or later`) | el extra `ifc` |
| bcf-client 0.9.0 | 0.9.0 | GPLv3 (`GNU General Public License v3 (GPLv3)`) | `ifctester` (dependencia dura) |
| xmlschema | 4.3.2 | MIT | `ifctester`; también lo usa `esquema_sin_red` |
| shapely | 2.1.2 | BSD 3-Clause | extra `planos` (R15) |
| ezdxf | 1.4.4 | MIT | extra `planos` (auditoría del archivo DXF) |

`ifctester/reporter.py` importa `bcf.v2.bcfxml` **solo dentro de `Bcf.report`** (la salida de
informes en formato BCF); `ifctester.ids` (abrir un IDS y validar un modelo) no la importa. Aun
así `pip` instala `bcf-client` junto con `ifctester`, así que **instalar el extra `ifc` deja un
paquete GPLv3 en el entorno**.

## Decisión (RP8-1)

1. `ifctester` vive **solo** en el extra `ifc`, fuera de `civil`, de `ml` y de las dependencias
   base, y el instalador de S5 **no** lo incluye. La CI instala todos los extras (cero
   omitidas) porque no distribuye nada.
2. El producto importa de `ifctester` únicamente `ifctester.ids`, dentro de una función
   (`adapters/espacio/planos/ids.py`). Nunca importa `bcf` ni `ifctester.reporter`. La prueba
   `tests/unit/test_licencia_ifc.py` lo vigila por AST sobre todo el código del producto.
3. Sin el extra, la importación de un IFC sigue funcionando y el informe lo dice («IDS no
   comprobado: falta el módulo IFC (extra `ifc`)»); lo prueba
   `test_sin_el_modulo_ifc_el_informe_lo_dice_y_no_falla`.
4. Para que el extra entre al instalador hace falta, antes: (a) que Eugenio obtenga un dictamen
   sobre el efecto de empaquetar `bcf-client` (GPLv3) con un producto propietario, o (b) que
   `ifctester` deje de pedirla, o (c) reemplazar la validación IDS por código propio. Mientras
   tanto el IDS lo audita quien instala el extra en su equipo de desarrollo o de tesis.
5. Si una versión nueva cambia la licencia de cualquiera de las dos, falla la prueba que
   compara este documento con las distribuciones instaladas, y se vuelve a decidir.

## Qué no cubre

La tesis y el prototipo no se distribuyen con `bcf-client`. Este documento no cubre la
distribución comercial; esa pregunta queda para antes de S5-2 (instalador).
