"""Asistente de IA verificada (Silice S4, version 0.9.0).

La IA nunca escribe un numero final: invoca herramientas que PROPONEN datos de entrada en el
borrador de la hoja; el sistema deriva, valora y audita, y una persona confirma y guarda. Este
paquete no es del nucleo ni un adaptador (S4 §5.1): `core/` no lo conoce y los unicos modulos de
`ui` que lo importan son `ui.paginas.hoja`, `ui.paginas.administracion` y `ui.entrega`.
"""
