# Auditoría final de Sílice (2026-10-13)

Base: `main` 7555f21. Rama `inc/auditoria-final`. Pedida por Eugenio tras el método «sin pruebas» del 2026-10-12.

## Resultado de la corrida única

| Comprobación | Resultado |
|---|---|
| Suite completa (`pytest -W error`, todos los extras) | **6048 pasan, 0 fallan**, 2209 s (antes 3966) |
| Pruebas omitidas (`verificar_omitidas.py`) | 0 |
| `ruff check .` | limpio |
| `meta_datos.py` | 4/4 |
| Guardia del núcleo | OK; `git diff origin/main -- core` vacío |
| Meta 0.6.0 / S1-5 | 11/11 |
| Meta 0.7.0 / S2-2 | 15/15 |
| Meta 0.9.0 / S4-3 | 21/25: C3 FALLA (las pruebas se escribieron después del código por el método del 12/10), S3-M4 FALLA (la CI no mide `seguridad/` ni `paquete/`), C6 y S2-BASE-070 PENDIENTE |

Fusión 1.5: `scripts/fusion_verificar.py` se reprodujo en 120/125; las cinco restantes quedan PENDIENTE por falta del `expectativas.json` local (HEC-3).

## Pruebas escritas

Siete áreas, unos 90 archivos nuevos y 2 generadores/fixtures nuevos. No aplican por código no construido: T3 (clave del proyecto), T18 (meta S5b), T20 (publicar), `instalador.yml` (PR #79), S4.4 (experimento), S3-6 (atípicos, RF-100), contraste R16, sellado al abrir, bases v0.7.0 a v0.9.0.

## Defectos de código corregidos (ninguno en `core/`)

- SEG-1: el acceso con cuentas estaba apagado por defecto y el lanzador no lo encendía; ahora `operacion/lanzador.py` fuerza `SILICE_ACCESO=1` en el producto.
- Paquete: el anexo `reajuste.json` incluía cláusulas de todos los proyectos (fuga); exportar no comprobaba la relación 100:1; `abrir_zip` dejaba escapar `zlib.error`.
- `ui/paginas/visor.py`: inyección de `</script>` por el GlobalId de un `.ifc`.
- `operacion/config.py`: aceptaba 127.0.0.1 y enlace local como red local; puertos iguales.
- `ui/proyectos.py`/`barra.py`: moneda declarada a nombre de un responsable fijo (RF-82).
- `ui/app.py`: Administración como cuarta sección (RF-42); recorrido «Entregar y revisar» (RF-37).
- `ui/tablero.py`: tarjeta EAC con motivo ajeno. `ui/paginas/revisar.py`: fecha sin `texto_seguro`.
- `adapters/hoja_empresa/escritor/apu.py`: cabecera del APU leída en filas fijas (causa C1).
- `asistente/configuracion.py`: JSON no objeto tumbaba la hoja. `instalador/`: faltaba `[theme]`; `auditar.py` no validaba la fecha.

## Hallazgos abiertos (decide Eugenio o requieren expediente)

Bloqueantes de proceso: REQ-4 (RF-95, experimento del asistente, sin construir y sin declarar), REQ-1/PRU-5/PRU-6 (ERS, plan de pruebas y calidad desfasados), ARQ-7 (`meta_silice --version 1.0.0` se cae por `asistente.experimento.congelado`).
Mayores: SEG-2 (cinco lectores de .xlsx sin la guardia), ARQ-1 (`scripts.lista_maprex_bs` no viaja en el instalador), ARQ-2 (LGPL de ifcopenshell sin texto), ARQ-3/4 (arquitectura sin enmiendas 0.6-0.8, vista física vieja), PRU-3 (CI sin metas ni cobertura de las capas nuevas), PRU-4 (conjunto exacto de `fusion_verificar` circular), PRU-7 (sin bases v0.7-0.9), HEC-1 (PDF de ARENAZA aún llamados «ficticios»), HEC-2 (nombre de persona en los PDF reales), HEC-3, HEC-4 a HEC-9, HEC-13 (`restablecer_administrador.py` ignora `--help`), hueco de la contraseña del respaldo de la clave de IA tras reiniciar, REQ-5/6 (RF-100 y R16 sin construir ni declarar).
Menores: SEG-3 a SEG-9 (incl. urllib3 2.7.0 con 3 CVE), ARQ-5 a ARQ-10, `prof.out` versionado, `fecha_devolucion` ausente responde 422 con formato de FastAPI, `libros.py:155` con caché compartida entre sesiones, posible conexión SQLite sin cerrar en `test_api_clave.py` (una vez en ~12 corridas).

Método: pruebas escritas sin rojo previo salvo las regresiones de los defectos de arriba (se vieron en rojo antes de corregir).
