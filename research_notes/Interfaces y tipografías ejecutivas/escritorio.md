# Desktop application shells for Sílice (Windows, offline, proprietary, no Streamlit)

Research date: 2026-10-13. Scope: how to wrap a Python 3.12 FastAPI/SQLAlchemy/SQLite backend plus a new web-style UI into a sellable, offline-installable Windows 10/11 desktop product, optionally also served on a LAN. Note on method: 18 tool calls; primary docs fetched for Tauri 2 (installer, sidecar, updater), Microsoft WebView2 distribution, Microsoft code signing/SmartScreen (via search summary), pywebview, NiceGUI, Flet, Qt/Qt WebEngine licensing, PyInstaller, Nuitka, python-build-standalone. Electron, electron-builder and Wails docs were NOT fetched directly; claims about them are limited to what secondary sources say and are flagged.

## Q1. Options and how each hosts a Python backend (maturity, license, size, memory, WebView2, updates, signing, native features, security, dev complexity)

### Takeaway
Every web-UI shell on Windows except Electron and Qt WebEngine depends on the system WebView2 runtime; for a guaranteed-offline install the installer must embed the Evergreen Standalone Installer (~127 MB extra in Tauri) or ship a Fixed Version runtime (180–250+ MB, and you own its security patching). Tauri 2 + PyInstaller/Nuitka FastAPI sidecar is the best-documented "premium" path with a mandatory-signature updater and capability allow-lists; pywebview (or NiceGUI native mode, which uses pywebview) is the lowest-effort pure-Python path; Qt/PySide6 is viable but carries LGPLv3 plus Chromium LGPL-2.1 obligations.

### Cited Findings

**Tauri 2 (Rust shell + WebView2, Python as sidecar)**
- Tauri's sidecar feature exists precisely to bundle external binaries "so users don't need to install dependencies like Node.js or Python"; the docs name "Python CLI apps or API servers bundled using pyinstaller" as a common use case. Sidecars are declared in `bundle.externalBin` in `tauri.conf.json`, and each binary must exist as `<name>-<TARGET_TRIPLE>` (e.g. `-x86_64-pc-windows-msvc`) — [Tauri 2 sidecar docs](https://v2.tauri.app/develop/sidecar/)
- Security model: to launch a sidecar you must grant `shell:allow-execute` or `shell:allow-spawn` in `src-tauri/capabilities/default.json`, naming the sidecar with `"sidecar": true`; arguments can be restricted to a static list or regex `validator`s (`true` = any args, `false` = none). From JS, the argument array must match the capability definition exactly — [Tauri 2 sidecar docs](https://v2.tauri.app/develop/sidecar/)
- Communication options documented: spawn from Rust (`app.shell().sidecar("name").spawn()`), read `CommandEvent::Stdout`, write to stdin; or from JS via `Command.sidecar(...)` in `@tauri-apps/plugin-shell` — [Tauri 2 sidecar docs](https://v2.tauri.app/develop/sidecar/)
- Windows installers: MSI (WiX v3, Windows-only build, requires the VBSCRIPT optional feature) or NSIS `-setup.exe` (cross-compiling from Linux/macOS possible but "less tested") — [Tauri Windows installer docs](https://v2.tauri.app/distribute/windows-installer/)
- WebView2 install modes and offline behaviour: `downloadBootstrapper` (default, needs internet, +0 MB); `embedBootstrapper` (needs internet, +~1.8 MB); `offlineInstaller` (no internet, +~127 MB); `fixedVersion` (no internet, +~180 MB, you manage its security patches); `skip` (not recommended; app won't run without WebView2). `minimumWebview2Version` makes the installer run the bootstrapper if the installed runtime is older than a set value — [Tauri Windows installer docs](https://v2.tauri.app/distribute/windows-installer/)
- Updater: signatures are mandatory ("This cannot be disabled"); public key in `tauri.conf.json`, private key supplied at build via `TAURI_SIGNING_PRIVATE_KEY`; losing the private key means you can no longer ship updates to existing installs. Endpoints can be a static JSON file or a dynamic server (204 = no update); TLS enforced in production; plain HTTP requires `dangerousInsecureTransportProtocol`. Windows `installMode`: `passive` (default/recommended), `basicUi`, `quiet` (only for per-user installs or already-elevated apps). The app exits automatically when the Windows installer runs. No built-in channel setting: channels are done via endpoint URLs (e.g. `?channel=stable`) — [Tauri updater plugin](https://v2.tauri.app/plugin/updater/)
- Real-world lesson (Tauri v2 + PyInstaller sidecar, ~71 MB exe): the NSIS installer did not overwrite the installed sidecar on a same-version reinstall, and if the sidecar process is still running the file copy silently fails; workaround was NSIS pre-install hooks that kill the sidecar first — [tauri-apps/tauri issue #15134](https://github.com/tauri-apps/tauri/issues/15134)
- Real-world example: Voicebox ships a React + Rust (Tauri) app with a FastAPI backend bundled by PyInstaller `--onefile` as a sidecar, needing `--hidden-import`/`--collect-all` for packages PyInstaller misses; its CPU server is ~410 MB versus ~2.43 GB for the CUDA build (size driven by backend dependencies, not by Tauri) — [Voicebox build docs](https://docs.voicebox.sh/developer/building) (via search summary)
- Size: Tabularis (Tauri) Windows installer 12 MB vs Beekeeper Studio (Electron) 201 MB (different apps, not a controlled benchmark) — [Tabularis blog](https://tabularis.dev/blog/why-tabularis-runs-on-tauri); another blog reports 8.6 MB vs 244 MB — [levminer blog](https://www.levminer.com/blog/tauri-vs-electron)
- Memory: reported figures disagree — one blog 172 MB (Tauri) vs 409 MB (Electron) across six windows; a hobbyist Windows 11 test ~80 MB vs ~120 MB idle, gap "smaller than expected" — [search summary of levminer / hackernoon / pkgpulse posts](https://hackernoon.com/six-months-with-tauri-the-benefits-and-the-bill); no rigorous controlled benchmark found.

**Microsoft WebView2 runtime (affects Tauri, Wails, pywebview, NiceGUI native)**
- "The vast majority of Windows 10 devices have the WebView2 Runtime installed already… A small number of Windows 10 devices don't"; Microsoft recommends detecting it and deploying it with your app — [Microsoft WebView2 distribution](https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/distribution). CONFLICT: Tauri's docs state flatly that Windows 10 (April 2018+) and Windows 11 "include the WebView2 runtime" — [Tauri Windows installer docs](https://v2.tauri.app/distribute/windows-installer/). Microsoft's own wording is the authoritative, more cautious one.
- Evergreen Bootstrapper is ~2 MB and downloads the runtime from Microsoft servers (online only). For offline clients Microsoft provides the Evergreen Standalone Installer, run silently with `MicrosoftEdgeWebView2RuntimeInstaller{X64/X86/ARM64}.exe /silent /install`; elevated = per-machine, non-elevated = per-user. Detection via registry key `pv` under `...\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}` (HKLM WOW6432Node and HKCU) — [Microsoft WebView2 distribution](https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/distribution)
- Evergreen runtime updates automatically, but if the client is offline or IT disables updates the runtime may be old, so apps must feature-detect newer APIs — [Microsoft WebView2 distribution](https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/distribution)
- Fixed Version: "binaries are over 250 MB"; not auto-updated (you redistribute patches); only the latest and second-latest major versions are downloadable (archive what you need); cannot run from a network location/UNC path; on Windows 10, since Fixed Version 120, unpackaged Win32 apps must run `icacls <path> /grant *S-1-15-2-2:(OI)(CI)(RX)` and `*S-1-15-2-1` on the runtime folder — [Microsoft WebView2 distribution](https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/distribution)
- Enterprises can service the WebView2 runtime through WSUS — [Microsoft WebView2 distribution](https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/distribution)

**pywebview (Python-native window around a local web UI)**
- Lightweight native webview wrapper; Windows backend via WinForms; features: window management/events, built-in HTTP server, DOM access from Python, native application menu and dialogs, two-way JS–Python bridge; freezing does not bundle a heavy GUI toolkit or renderer, keeping executables small — [pywebview guide](https://pywebview.flowrl.com/guide/)
- On Windows it tries `edgechromium` (WebView2) first, then falls back to deprecated `mshtml` (IE11); EdgeChromium needs .NET Framework 4.6.2 and the WebView2 ("Edge") runtime; CEF must be selected explicitly and is Chrome 66-era — [pywebview web engine](https://pywebview.flowrl.com/guide/web_engine.html)
- License: BSD (BSD-3-Clause per AlternativeTo) — [pywebview on PyPI](https://pypi.org/project/pywebview/2.2.1); [AlternativeTo](https://alternativeto.net/software/pywebview/about)
- No named commercial pywebview app was found in search results — [search summary](https://alternativeto.net/software/pywebview/about)

**NiceGUI native mode (uses pywebview)**
- `ui.run(native=True)` opens a pywebview window; options pass through `app.native.window_args` / `start_args`; requires a browser engine with ES modules/import maps ("Chrome 89+"); native app runs in a separate process — [NiceGUI configuration & deployment](https://nicegui.io/documentation/section_configuration_deployment)
- Windows: needs .NET Framework for the EdgeChromium backend ("may be missing on minimal systems"); a known `WebView2Loader.dll` path issue — [NiceGUI configuration & deployment](https://nicegui.io/documentation/section_configuration_deployment)
- Packaging: `nicegui-pack --onefile --name myapp main.py` (PyInstaller-based); `--onefile` starts slower (unpacks to temp each launch), `--onedir` faster; must set `reload=False`; call `freeze_support()` first in the main guard for native apps — [NiceGUI configuration & deployment](https://nicegui.io/documentation/section_configuration_deployment)
- NiceGUI 3.x is current (parameters noted as added in 3.0.0 and 3.18.0) — [NiceGUI configuration & deployment](https://nicegui.io/documentation/section_configuration_deployment)

**Flet desktop (Flutter UI driven from Python)**
- `flet build windows` runs only on Windows, uses Flet's bundled x64 Flutter SDK, requires Visual Studio 2022/2026 with the "Desktop development with C++" workload, and Developer Mode if plugins are used; ARM64 PCs get an x64 build under emulation — [Flet Windows publishing](https://flet.dev/docs/publish/windows)
- Closing the window terminates the app immediately, skipping Python `atexit` handlers and unflushed writes (relevant for SQLite integrity and audit logs) — [Flet Windows publishing](https://flet.dev/docs/publish/windows)
- Alternative `flet pack` is PyInstaller-based and needs neither Visual Studio nor Flutter — [Flet Windows publishing](https://flet.dev/docs/publish/windows)
- Flet does not use WebView2 (Flutter renders natively) — inferred from the docs describing a Flutter build; not stated explicitly on the fetched page.

**PySide6 / Qt with Qt WebEngine**
- LGPLv3 obligations for a proprietary app: deliver Qt's complete corresponding source (or written offer) even if unmodified; dynamic linking generally lets your code stay proprietary, static linking may not; users must be able to modify and re-link the library and run the result (including via reverse engineering); provide "installation information" (anti-tivoization); include LGPL text and a prominent notice; you may not impose terms restricting LGPL freedoms. Some Qt parts are GPL-only — [Qt LGPL obligations](https://www.qt.io/licensing/open-source-lgpl-obligations)
- Qt WebEngine: the Qt-specific parts are available under commercial, LGPLv3, GPLv3 or GPLv2; the bundled Chromium part's most restrictive license is LGPL 2.1; distributors must comply with both sets — [Qt WebEngine licensing (Qt for Python docs)](https://doc.qt.io/qtforpython-6/overviews/qtwebengine-licensing.html)

**Electron (+ Python sidecar)**
- Electron bundles Chromium, whereas Tauri uses the OS WebView2, so Electron installers are much larger (e.g. 201 MB Beekeeper Studio, 244 MB in another report) — [Tabularis blog](https://tabularis.dev/blog/why-tabularis-runs-on-tauri); [levminer blog](https://www.levminer.com/blog/tauri-vs-electron)
- Electron/electron-builder official docs were not fetched (see Gaps).

**Wails (Go)**
- Only a community, self-described "not scientific" table was found (Wails ~162 MB release); its numbers conflict with other sources and should not be relied on — [web-to-desktop framework comparison](https://git.tdem.in/Elanis/web-to-desktop-framework-comparison)

**Code signing and SmartScreen (applies to all options)**
- EV certificates no longer bypass SmartScreen (change in 2024); OV and EV are treated the same for new files; reputation is tracked per file hash so each new build starts at zero; EV still has value for enterprise procurement because of stricter identity validation — [Microsoft code signing options](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/code-signing-options); [ToDesktop PSA](https://www.todesktop.com/blog/posts/windows-apps-psa-ev-certs-do-not-grant-immediate-reputation-anymore)
- Azure Artifact Signing (formerly Trusted Signing) does not give instant SmartScreen trust; availability: organizations in USA, Canada, EU, UK; individuals in USA and Canada only — [Microsoft code signing options](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/code-signing-options)
- Microsoft Store apps are re-signed by Microsoft and avoid the warning — [Microsoft code signing options](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/code-signing-options) (via search summary)

### Inferences
- For Sílice's "fully offline after install" requirement, the installer must include the WebView2 Evergreen Standalone Installer and run it only if the `pv` registry key is missing (Tauri `offlineInstaller` mode does this; with Inno Setup + pywebview it must be scripted). Default Tauri `downloadBootstrapper` would silently violate the offline requirement on the minority of Windows 10 machines without WebView2.
- Fixed Version WebView2 is a poor fit for a 1–2 person team: +180–250 MB, manual security patching, and the Windows 10 icacls quirk.
- Tauri's capability allow-lists plus a FastAPI bound to 127.0.0.1 with a per-launch random token give a clear security story; pywebview's `js_api` bridge exposes Python methods to page JS (security page not fetched), so keeping all logic behind the REST API is the safer pattern.
- Dev complexity ranking for a Python-only team (lowest to highest): NiceGUI native ≈ pywebview + static React build < Flet < Tauri (needs Rust toolchain, though very little Rust code) < Electron (Node toolchain + bigger artifacts) < PySide6 (Qt idioms + LGPL compliance work). Wails adds Go with no benefit when the backend is Python.
- Because Venezuela is not among Azure Artifact Signing's eligible regions, Sílice would need a conventional OV certificate (cloud HSM/token) from a public CA; expect SmartScreen warnings on every new build until reputation accrues. EV is not worth the premium for SmartScreen purposes.
- Flet's hard-kill on window close is a real risk for an audit product that writes signed records to SQLite; it would need explicit flush/commit-per-transaction discipline.

### Gaps
- Electron and electron-builder: license, current major version, NSIS/auto-update (electron-updater) behaviour and code-signing specifics were not fetched from primary docs.
- Wails v2/v3 status in 2026, license and Windows sizes: no reliable source found.
- Flet license and output size: not stated on the fetched page.
- PySide6's own license text (LGPLv3/GPL/commercial) was not fetched directly; GPL-only Qt modules were not enumerated.
- pywebview current version (5.x/6.x?) and its security page (js_api exposure, built-in server) were not fetched.
- No rigorous, controlled memory benchmark across Tauri/Electron/pywebview on Windows was found; numbers above are anecdotal.
- Multi-window/menu/tray/native-notification feature parity was not verified per framework from primary docs beyond pywebview's menu/dialog list and Tauri's general plugin model.

## Q2. Packaging the Python backend: PyInstaller vs Nuitka vs uv-bundled Python (python-build-standalone)

### Takeaway
All three are license-compatible with a proprietary product (PyInstaller GPL2 + bootloader exception, Nuitka Apache 2.0 with output unrestricted, python-build-standalone MPL-2.0). PyInstaller one-file builds are the most prone to antivirus false positives and slow cold start; Nuitka compiles to C and is commonly reported to trigger fewer detections (anecdotal); the current uv/python-build-standalone + Inno Setup approach avoids both bootloaders entirely but ships readable `.py` files.

### Cited Findings
- PyInstaller: "You may use PyInstaller to bundle commercial applications out of your source code"; output may ship under any license compatible with your dependencies; no need to include PyInstaller's license or credit; only modifications to PyInstaller itself must be GPL — [PyInstaller license](https://pyinstaller.org/en/stable/license.html)
- PyInstaller AV false positives: one guide claims fresh PyInstaller executables hit 5–15 of 70+ VirusTotal engines (vendor blog, not independent) — [beatsyncpro guide](https://beatsyncpro.ai/blog/nuitka-vs-pyinstaller); a developer attributes it to the bootloader resembling malware and to self-extraction to temp — [DEV Community](https://dev.to/weisshufer/from-pyinstaller-to-nuitka-convert-python-to-exe-without-false-positives-19jf); a Microsoft repo issue about a Defender-flagged PyInstaller build lists missing version info, no code signing and UPX compression as contributors — [microsoft/apm issue #487](https://github.com/microsoft/apm/issues/487)
- One-file vs one-dir: `--onefile` unpacks to a temp dir on every launch (slower start); `--onedir` starts faster — [NiceGUI packaging docs](https://nicegui.io/documentation/section_configuration_deployment)
- Nuitka: base project is Apache-licensed; the FAQ says the license "does not impact your software at all, nor how you use compiled binaries"; Nuitka Commercial (paid, non-redistributable) adds embedding/protection of data files; a third-party handbook claiming AGPL conflicts with the official pages and quotes ~€250/yr (verify on nuitka.net) — [Nuitka commercial license](https://nuitka.net/doc/commercial-license.html); [Nuitka commercial](https://nuitka.net/commercial.html); [pydevtools handbook](https://pydevtools.com/handbook/reference/nuitka/)
- Nuitka onefile also extracts to a temp folder; files are only protected with the commercial Themida/VM options — [Nuitka bundles](https://nuitka.net/doc/bundles.html)
- python-build-standalone: maintained by Astral (uv/ruff), "redistributable builds of Python", portable to any install path, Python 3.10–3.15 incl. free-threaded, Windows supported; license MPL-2.0; most users should use `install_only` archives — [python-build-standalone repo](https://github.com/astral-sh/python-build-standalone)

### Inferences
- For Sílice's Tauri sidecar, a Nuitka `--standalone` (one-dir) FastAPI build signed with the same certificate is likely the best compromise: faster start than PyInstaller onefile, fewer AV flags, some code obfuscation. PyInstaller `--onedir` without UPX, with version resources, and code-signed is the cheaper, more battle-tested fallback.
- If the shell is pywebview/NiceGUI, the existing uv + python-build-standalone + Inno Setup pipeline can be kept as-is (no bootloader → fewer AV issues), at the cost of shipping `.pyc`/`.py` source; Nuitka could be applied later to sensitive modules (licensing check, signing).
- MPL-2.0 for python-build-standalone is file-level copyleft only; it imposes notice/source-availability for modified MPL files, not on Sílice's own code (standard MPL reading; confirm with counsel).
- Always sign every `.exe`/`.dll` you produce (sidecar included) — unsigned helper executables are a common AV/SmartScreen trigger.

### Gaps
- No independent, measured comparison of Defender detection rates for PyInstaller vs Nuitka vs plain embedded Python was found.
- No measured startup times for a FastAPI+SQLAlchemy app across the three methods were found.
- Exact text of PyInstaller's bootloader exception (in COPYING.txt) was not fetched.

## Q3. LAN mode: can the same desktop build also serve other users' browsers?

### Takeaway
Yes architecturally — the FastAPI sidecar is just an HTTP server — but binding to 0.0.0.0 turns a single-user desktop app into a multi-user server, requiring authentication, TLS or a trusted-LAN decision, firewall handling, and SQLite concurrency care. NiceGUI explicitly binds 127.0.0.1 in native mode and 0.0.0.0 otherwise, which shows the two modes are distinct configurations.

### Cited Findings
- NiceGUI defaults `host` to `'0.0.0.0'` outside native mode and `'127.0.0.1'` in native mode; supports HTTPS via `ssl_certfile`/`ssl_keyfile` and reverse proxies — [NiceGUI configuration & deployment](https://nicegui.io/documentation/section_configuration_deployment)
- NiceGUI native mode auto-selects an open port (8000–8999) unless `port` is given; browser mode defaults to 8080 and does not scan — [NiceGUI configuration & deployment](https://nicegui.io/documentation/section_configuration_deployment)
- Tauri updater enforces TLS in production; serving updates from a LAN host over plain HTTP requires `dangerousInsecureTransportProtocol` — [Tauri updater plugin](https://v2.tauri.app/plugin/updater/)

### Inferences
- Recommended design: one binary, two explicit modes. "Desktop" mode: sidecar on 127.0.0.1, random port, per-launch secret token injected into the webview. "Server" mode (opt-in, admin-only, licensed as a separate SKU/seat count): bind 0.0.0.0 on a fixed port, require user login, serve the same React build as static files from FastAPI, optionally self-signed or customer-provided TLS.
- Windows Defender Firewall will prompt on first listen on 0.0.0.0; the Inno/NSIS installer should add a scoped inbound rule only when server mode is chosen.
- SQLite over a LAN is fine only when a single server process owns the file (never place the DB on a network share); WAL mode and short transactions are needed for concurrent browser users.
- Because the UI is a web build, LAN clients need nothing installed — a strong reason to choose a web-stack UI (React or NiceGUI) over Flet/Qt for Sílice.
- If the UI is a pure web build served by FastAPI, the Tauri/pywebview window is just a "browser" pointed at localhost, so the LAN and desktop UIs are literally identical.

### Gaps
- No primary source was found on multi-user SQLite limits for FastAPI specifically, or on Windows firewall behaviour for Tauri sidecars.

## Q4. Commercial-product aspects: licensing/activation, offline crash reporting, telemetry, update channels

### Takeaway
None of the shells provides licensing/activation; it must be built in the app. Sílice already has Ed25519 signing, which is the standard building block for offline-verifiable license files. Update channels must be implemented via endpoint URLs (Tauri) or by the installer pipeline (Inno Setup).

### Cited Findings
- Tauri's updater has no built-in channels; implement via endpoint URL (query parameter or separate subdomains chosen at runtime) — [Tauri updater plugin](https://v2.tauri.app/plugin/updater/)
- Tauri update artifacts must be signed with a key pair whose private key, if lost, prevents further updates to existing installs — [Tauri updater plugin](https://v2.tauri.app/plugin/updater/)
- Nuitka Commercial can embed and protect data files inside the binary (e.g. to make tampering with a public key or license logic harder) — [Nuitka commercial](https://nuitka.net/commercial.html)

### Inferences
- Offline license scheme: vendor signs a JSON license (customer, seats, edition, expiry, optional machine fingerprint, server-mode flag) with an Ed25519 private key held only by the vendor; the app embeds the public key and verifies at startup. Hardware binding via a hash of stable identifiers (e.g. Windows MachineGuid + volume serial) with a tolerance/re-issue process; offline activation via a request code the customer emails and a signed response file.
- Embedding the public key in a Nuitka-compiled module (rather than a readable `.py`) raises the bar against key swapping; no scheme is crack-proof — focus on keeping honest customers honest.
- Offline crash reporting: write local crash dumps/log bundles (Python `faulthandler` + structured logs) and a "Export diagnostic package" button; telemetry strictly opt-in and off by default, given offline enterprise customers. For a Tauri shell, sentry-style SDKs can be pointed at a self-hosted endpoint only if the customer allows network access.
- Update channels for offline customers: ship signed full installers (stable/beta) that IT applies manually or from an internal file share/LAN server; Tauri's updater can target an HTTPS LAN endpoint configured per customer.

### Gaps
- No primary sources were fetched on licensing services (Keygen, Cryptlex, LicenseSpring), offline crash-reporting SDKs, or Windows hardware-fingerprint stability; recommendations above are engineering inference.

## Q5. Real examples of commercial apps with Tauri + Python sidecar or pywebview, and lessons learned

### Takeaway
Concrete public examples of Tauri + FastAPI/PyInstaller sidecars exist (Voicebox) along with documented Windows pitfalls; no named commercial pywebview product was found.

### Cited Findings
- Voicebox: React UI + Tauri shell + FastAPI backend frozen with PyInstaller `--onefile` as a sidecar; needs hidden-import/collect-all flags; backend size dominates (~410 MB CPU, ~2.43 GB CUDA) — [Voicebox build docs](https://docs.voicebox.sh/developer/building)
- Tauri v2 NSIS reinstall did not replace a running/unchanged PyInstaller sidecar (~71 MB); fix: NSIS pre-install hook that kills the sidecar — [tauri issue #15134](https://github.com/tauri-apps/tauri/issues/15134)
- Windows sidecar executables must be built on Windows and carry `.exe` — [Japanese write-up via search summary](https://zenn.dev/karugamo/scraps/5e5f17070020e9)
- No named commercial pywebview app found; README only invites showcase submissions — [search summary](https://alternativeto.net/software/pywebview/about)

### Inferences
- Lessons to adopt: (1) sidecar lifecycle — kill on app exit and before install/update; (2) health-check the FastAPI port before showing the UI (splash screen); (3) dynamic port + token; (4) build sidecar and shell in Windows CI; (5) sign both the shell and sidecar; (6) keep the Python payload lean (exclude test/dev deps) since backend size dominates.

### Gaps
- No published post-mortems from commercial vendors on Tauri+Python sidecar at scale; no FastAPI-specific production write-up on port selection/shutdown found.

## Q6. Ranked recommendation for Sílice

### Takeaway
1) Tauri 2 + React/shadcn UI + FastAPI sidecar (Nuitka or PyInstaller one-dir), NSIS installer with WebView2 `offlineInstaller` — best premium feel, small shell, signed updater, capability allow-lists, LAN mode for free. 2) pywebview (or NiceGUI native) window + same React build served by FastAPI, keeping the current uv + Inno Setup pipeline — lowest effort and risk for a 1–2 person Python team. 3) Electron only if Tauri/WebView2 blockers appear. Not recommended: Flet (no LAN browser reuse, hard-kill on close), PySide6/Qt WebEngine (LGPLv3 + Chromium LGPL-2.1 compliance burden), Wails (Go adds nothing).

### Cited Findings
- Tauri offline WebView2 embedding (+~127 MB) and mandatory signed updater — [Tauri Windows installer docs](https://v2.tauri.app/distribute/windows-installer/); [Tauri updater](https://v2.tauri.app/plugin/updater/)
- pywebview uses WebView2 on Windows with MSHTML fallback, needs .NET 4.6.2 — [pywebview web engine](https://pywebview.flowrl.com/guide/web_engine.html)
- Flet closes without running `atexit`/flushes — [Flet Windows publishing](https://flet.dev/docs/publish/windows)
- Qt LGPL relink/source/installation-information obligations and WebEngine's Chromium LGPL-2.1 — [Qt LGPL obligations](https://www.qt.io/licensing/open-source-lgpl-obligations); [Qt WebEngine licensing](https://doc.qt.io/qtforpython-6/overviews/qtwebengine-licensing.html)
- SmartScreen warnings for every new build regardless of OV/EV — [Microsoft code signing options](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/code-signing-options)

### Inferences
- Pragmatic path: build the new UI as a static React (shadcn/ui, Tremor) bundle served by FastAPI. Ship v1 inside pywebview with the existing Inno Setup + uv-built Python (adding the WebView2 Standalone Installer as a conditional prerequisite). Because the UI and API are shell-agnostic, migrate later to Tauri 2 when auto-update and a more polished native shell justify adding Rust tooling. This de-risks the shell decision.
- Risks across options: WebView2 absent on some Windows 10 machines (mitigated by bundled standalone installer, +~127 MB download size); SmartScreen warnings for an unknown publisher (mitigated by OV signing, consistent publisher name, and time); AV false positives on frozen Python (mitigated by one-dir builds, no UPX, version resources, signing, submitting samples to Microsoft); sidecar lifecycle bugs (kill-before-install hooks); LAN mode security (auth + firewall + single-owner SQLite).
- Installer size estimates (inference): pywebview + embedded Python ≈ current Sílice installer + ~127 MB if bundling WebView2 standalone; Tauri ≈ 10–15 MB shell + Python sidecar (tens to low hundreds of MB depending on dependencies) + ~127 MB WebView2 offline installer.

### Gaps
- No primary measurements of Sílice-like (FastAPI + SQLAlchemy + openpyxl) frozen backends' size/startup were found; must be measured in a spike.
- Whether Venezuelan companies can obtain OV code-signing certificates from major CAs without obstacles was not researched.
