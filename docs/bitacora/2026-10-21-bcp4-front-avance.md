# BCP-4 · front: bienvenida de primera vez y recuperar acceso (avance)

Fecha: 2026-10-21 · Rama `inc/ruta-s2-mig-adm-empresa` · Implementador front. Diseño:
`docs/especificaciones/2026-10-21-bienvenida-casos-proyectos-design.md` (§3.5, §3.6, §8, §9, §10.4 F1 a F4 y F16, §16).
Contrato real leído: `docs/bitacora/2026-10-21-bcp1-contrato-rutas.md` (coincide con §9; sin desviaciones).

## Qué se hizo
- `src/bienvenida/`: `usePrimerArranque` (GET /v1/primer-arranque; cualquier fallo es «Entrar»), `Bienvenida`, `RecuperarAcceso`,
  `FormularioDeReclamo` (formulario común), `bienvenida.scss`.
- `useSesion.reclamar` (POST /v1/primer-arranque/reclamo, 201 abre la sesión), `Entrar` con «Perdí el acceso de administrador»,
  `App` decide entre «Comprobando su instalación…», Bienvenida, Entrar y Recuperar (una sesión vencida no vuelve a preguntar).

## Decisiones de ingeniería
- Borrado de secretos: el código se borra tras cualquier error; con 401 y 423 se borran además las contraseñas (§3.5 línea de
  atributos); con 422, 429, 503, 403 y fallo de red se conservan las contraseñas para corregir (§3.5 «ninguno borra lo escrito
  salvo el código»). Tras el éxito se vacía todo el estado.
- El enlace «Perdí el acceso» es un botón `ghost`; `aria-describedby` de las contraseñas se completa con la política (Carbon
  reemplaza el que se le pasa).
- Los textos del producto instalado para recuperar (acceso directo «Sílice: recuperar acceso de administrador» y la orden
  `python -m operacion restablecer-administrador`) dependen de D-7 (pendiente de Eugenio).

## Ajustes tras ver verde (declarados)
- Defecto real que cazó la prueba: tras un error del servidor el código recién borrado se pintaba como «Escriba el código»
  (`intentado` seguía verdadero); se corrigió.
- Pruebas ajustadas: el filtro de px admite filetes y anillos de foco; el foco del resumen solo la primera vez (se comprueba con el
  botón enfocado); el App «sesión vencida» necesita una cuenta con `operar_arenera` para que el Inicio dé 401; «mientras pregunta»
  espera «Comprobando su instalación…».

## Medición en navegador (Chromium 1234 por DevTools, Node 22)
Servidor de prueba en 127.0.0.1:8030 que sirve `dist/` en `/app/` y **simula** P0/P1 (BCP-1 aún no estaba montado en
`api/main.py`: no se probó contra el servidor real). 12 combinaciones (bienvenida, bienvenida sin archivo, recuperar × 1366 y
1056 px × Normal y Muy grande): un `h1`, `scrollWidth <= clientWidth` en todas, resumen de errores con el foco al enviar vacío.
Alto de la bienvenida: 1667 px (Normal), 2500 (Muy grande 1366), 2910 (Muy grande 1056, una columna). El 8000 no se tocó.
