# Guion del día de la medición de la auditoría (Fase 3)

**Para qué sirve.** Son los comandos exactos, en orden, para medir la detección, los falsos positivos y el kappa de
Sílice sobre los libros nuevos. Se ensayó el 2026-11-25 de punta a punta con un libro **ficticio** (salió de
`tests/fixtures/libros_empresa.py`, sembrado con la taxonomía de plantilla y la semilla 7). Esas cifras **no** son de la
tesis. El guion se actualizó con las herramientas corregidas ese día y con las actas:
[cifra oficial](../bitacora/2026-11-25-cifra-oficial-de-deteccion.md) y
[kappa, SUS y textos](../bitacora/2026-11-25-acta-kappa-sus-y-textos.md).

**Reglas que no se negocian:**
- Los libros de la empresa, sus copias sembradas, las planillas marcadas y las salidas viven solo en el equipo de
  Eugenio, fuera del repositorio (NORMAS §1).
- Los scripts se niegan a escribir dentro de cualquier repositorio.
- Todo se corre desde la raíz del repositorio, con PowerShell.

## 0. Preparación

```powershell
$env:PYTHONIOENCODING = 'utf-8'
$D = 'C:\MedicionSilice\<carpeta-del-dia>'                    # FUERA del repositorio
New-Item -ItemType Directory -Force $D | Out-Null
Test-Path 'C:\Program Files\LibreOffice\program\soffice.exe'  # debe dar True
git diff --stat reglas-congeladas-2026-11-24 -- core/verification/reglas.py adapters/hoja_empresa adapters/vial aplicacion/causas_raiz.py docs/planes/2026-11-23-plan-auditoria-no-circular.md
# Sin salida: las reglas son las selladas. El manifiesto de cada corrida guarda además sus SHA-256 (LF).
```

Antes de este día, la taxonomía del tercero ya está sellada: su huella y la etiqueta `taxonomia-tercero-sellada`
quedan anotadas en la bitácora, según la [guía del tercero](2026-11-25-guia-taxonomia-tercero.md).

## 1. La revisión ciega del experto (antes de ver nada de Sílice)

Por cada libro nuevo, la planilla vacía de revisión por partida, que no trae nada de Sílice:

```powershell
$LIBRO = "$D\libro_original.xlsx"     # copia del libro nuevo
uv run --no-sync python scripts/medir_auditoria_libro.py revision $LIBRO --salida "$D\revision_experto.xlsx"
```

El experto marca para cada partida «¿Tiene error?» (Sí o No). Esa planilla alimenta el kappa experto–Sílice del
criterio de fracaso. Lo decidió el acta del 2026-11-25, punto 1: se calcula por partida e incluye las sanas.

## 2. Siembra (la corre quien siembra)

```powershell
$TAX = 'docs\tesis\taxonomia_tercero.toml'       # la del tercero, sellada
uv run --no-sync python scripts/inyector_fallas.py $LIBRO --taxonomia $TAX --n <N> --semilla <S> --salida "$D\siembra"
# Produce siembra\<libro>_inyectado.xlsx y siembra\<libro>_clave.xlsx.
# Si siembra menos de N fallas, termina con error: no se mide con una muestra más chica que la planeada.
```

## 3. Cifra automática de detección

```powershell
# OFICIAL: todas las fallas a la vez (acta de la cifra oficial)
uv run --no-sync python scripts/medir_inyeccion.py $LIBRO --taxonomia $TAX --n <N> --semilla <S> --salida "$D\medicion" --fecha <AAAA-MM-DD>
# SECUNDARIA: una falla por vez (tarda más; córrala con tiempo de espera largo)
uv run --no-sync python scripts/medir_inyeccion.py $LIBRO --taxonomia $TAX --n <N> --semilla <S> --salida "$D\medicion" --fecha <AAAA-MM-DD> --una-por-vez
```

Cada corrida:
- audita primero el libro sin sembrar y no acredita fallas a los hallazgos que ya estaban;
- imprime «Detectó X de N», el intervalo de Wilson al 95 % y el criterio de fracaso, aclarando que evaluó lo
  señalado por Sílice;
- guarda un JSON con el manifiesto (huellas de las reglas, versión de LibreOffice y semilla).

## 4. Planillas para los evaluadores

```powershell
$SEMBRADO = "$D\siembra\<libro>_inyectado.xlsx"
uv run --no-sync python scripts/medir_auditoria_libro.py exportar $SEMBRADO --salida "$D\p1.xlsx" --fecha <AAAA-MM-DD> --recalcular
uv run --no-sync python scripts/medir_auditoria_libro.py exportar $SEMBRADO --salida "$D\p2.xlsx" --fecha <AAAA-MM-DD> --recalcular
```

- **Por qué `--recalcular`:** un libro sembrado conserva sus valores viejos. Sin recalcular con LibreOffice, varias
  fallas no se verían.
- **Por qué `--fecha` fija:** algunas reglas dependen de la fecha, y `calcular` tiene que usar la misma.
- **Archivos que ya existen:** el comando se niega a sobrescribir una planilla. Es a propósito.
- **Qué marca cada evaluador:** solo su planilla. En «Veredicto» pone Verdadero o Falso, y llena «Se le escaparon».

## 5. Calcular

```powershell
uv run --no-sync python scripts/medir_auditoria_libro.py calcular `
  --planilla "$D\p1_marcada.xlsx" --otra "$D\p2_marcada.xlsx" `
  --clave "$D\siembra\<libro>_clave.xlsx" --libro $SEMBRADO --libro-base $LIBRO `
  --revision-experto "$D\revision_experto_marcada.xlsx" `
  --fecha <AAAA-MM-DD> --recalcular | Tee-Object "$D\calcular.txt"
```

Imprime estas cifras:
- la precisión y los falsos positivos por causa;
- la detección **confirmada** por el evaluador, que es la que decide (acta de la cifra oficial), y al lado la
  señalada;
- los hallazgos previos descontados;
- el kappa experto–Sílice por partida, que decide;
- el kappa entre los dos evaluadores, que mide la fiabilidad entre personas y no decide;
- los intervalos de Wilson.

Al final evalúa el criterio de fracaso sellado: detección menor del 50 %, falsos positivos por encima del 40 % y kappa
experto–Sílice menor de 0,4.

**Opciones iguales en `exportar` y en `calcular`:** `--fecha`, `--perfil`, `--recalcular` y `--sin-agrupar`. Si no
coinciden, la auditoría que repite `calcular` no reproduce la planilla y el script se detiene.

## 6. Lo que se guarda (solo en `$D`)

- el JSON de `medir_inyeccion`;
- las planillas marcadas, la clave, la revisión del experto y `calcular.txt`;
- la versión de LibreOffice y las semillas.

Nada de eso entra al repositorio. A la tesis van solo las cifras generales (Tablas 4.5a a 4.5d del
[capítulo IV](2026-11-23-esqueleto-capitulo-resultados.md)).
