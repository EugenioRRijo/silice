"""Fusión de Silice con los libros de la empresa (Silice 1.5): lector -> motor -> auditoría ->
alertas -> calcado.

Paquete de primer nivel fuera del núcleo, como `auditoria/` (spec 1.5, F-D2): importa `core`,
`adapters` (`hoja_empresa` y las constantes de `vial`) y `auditoria`; ni `core` ni `adapters` lo
importan a él. De `operacion` solo toma la versión del producto (`operacion.version`), nunca la
configuración de la instalación: la carpeta de los perfiles locales se la pasa quien llama.

De `aplicacion` solo importa reglas puras, que solo usan la biblioteca estándar
(`aplicacion.cifras`, la coma decimal y el punto de miles; `aplicacion.regla_desperdicio`, el
desperdicio dentro de la cantidad), y `aplicacion` no importa `fusion`: así no hay ciclo entre los
dos paquetes (revisión de correcciones de F5/F7/F8, N5). Lo vigila
`tests/unit/test_arquitectura.py`.
"""
