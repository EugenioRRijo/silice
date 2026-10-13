"""Fusión de Silice con los libros de la empresa (Silice 1.5): lector -> motor -> auditoría ->
alertas -> calcado.

Paquete de primer nivel fuera del núcleo, como `auditoria/` (spec 1.5, F-D2): importa `core`,
`adapters.hoja_empresa`
y `auditoria`; ni `core` ni `adapters` lo importan a él.
"""
