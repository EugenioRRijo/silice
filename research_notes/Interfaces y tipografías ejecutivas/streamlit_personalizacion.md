# Restyling a Streamlit app (1.62 to 1.65, 2026) into an executive interface: capabilities and limits

Context: "Sílice" is a Spanish-language Streamlit + FastAPI app (construction budgets and audit) installed locally on Windows with NO internet access. Research date: 2026-10-13. Latest Streamlit on PyPI is **1.65.0 (2026-10-02)**, Apache-2.0, requires Python >=3.10 ([PyPI JSON for streamlit](https://pypi.org/pypi/streamlit/json); [Release notes](https://docs.streamlit.io/develop/quick-reference/release-notes)). Release cadence in 2026: 1.53 (Jan 14), 1.54 (Feb 4), 1.55 (Mar 3), 1.56 (Mar 31), 1.57 (Apr 29), 1.58 (May 28), 1.59 (Jul 6), 1.60 (Jul 21), 1.61 (Aug 4), 1.62 (Aug 19), 1.63 (Sep 1), 1.64 (Sep 15), 1.65 (Oct 2) ([2026 release notes](https://docs.streamlit.io/develop/quick-reference/release-notes/2026)).

Method note: besides the docs, I downloaded the actual wheels of the eight third-party components from PyPI and grepped the bundled JavaScript/CSS for CDN hosts (fonts.googleapis.com, cdn.jsdelivr.net, unpkg, cdnjs, etc.), and queried the PyPI and GitHub APIs for license and last-activity data. Those results are cited as "wheel inspection" with the PyPI/GitHub URL of the package.

## 1. Theming in config.toml as of 2026: options, fonts, light/dark, and the version that introduced each

### Takeaway
Since 1.44 (Mar 2025), Streamlit has an "advanced theming" system that sets colors, fonts, radii, borders, the sidebar, dataframe headers, chart palettes and a 7-hue semantic palette without any CSS. Since 1.51 (Oct 2025) one app can carry its own custom light and dark themes. Custom fonts can be self-hosted from the app's `static/` folder via `[[theme.fontFaces]]` (OTF/TTF/WOFF/WOFF2). Streamlit's default fonts ship inside the package. A fully offline, branded executive theme is therefore achievable with config alone.

### Cited Findings
**Option inventory (current docs)**
- `base` ("light"/"dark", app-wide only; defaults to light if other options are set without it), `primaryColor` (accent for hover, focus and selection; it must be dark enough for white text because white is drawn on primary backgrounds), `backgroundColor`, `secondaryBackgroundColor` (widget input areas, `st.dataframe` headers, code blocks), `textColor`, `linkColor`, `linkUnderline`, `codeTextColor`, `codeBackgroundColor` — [Customize colors and borders](https://docs.streamlit.io/develop/concepts/configuration/theming-customize-colors-and-borders)
- Shape and borders: `baseRadius` (e.g. "none" = 0rem, "full" = 1rem; applies to buttons, inputs, containers, dataframes and images, but interactive charts and videos always keep square corners), `buttonRadius` (overrides it for buttons and `st.segmented_control`), `borderColor`, `dataframeBorderColor`, `showWidgetBorder` (off by default except for buttons), `showSidebarBorder` — [Customize colors and borders](https://docs.streamlit.io/develop/concepts/configuration/theming-customize-colors-and-borders)
- Dataframe: `dataframeHeaderBackgroundColor`, `dataframeHeaderTextColor` — [Customize colors and borders](https://docs.streamlit.io/develop/concepts/configuration/theming-customize-colors-and-borders)
- Charts: `chartCategoricalColors`, `chartSequentialColors`, `chartDivergingColors`, settable in `[theme]`, `[theme.sidebar]`, `[theme.light]` and `[theme.dark]` — [Customize colors and borders](https://docs.streamlit.io/develop/concepts/configuration/theming-customize-colors-and-borders)
- Semantic palette: `red|orange|yellow|green|blue|violet|gray` each with `...Color`, `...BackgroundColor` and `...TextColor` (derived automatically if only the base is set). It styles colored Markdown text, `st.badge`, `st.metric` deltas, dataframe chart columns, chat avatars and alerts. Values accept named CSS colors, HEX, RGB and HSL — [Customize colors and borders](https://docs.streamlit.io/develop/concepts/configuration/theming-customize-colors-and-borders)
- Typography: `font` (default Source Sans; "sans-serif"/"serif"/"monospace" or a custom family; also covers widget labels, tooltips and dataframe cells), `headingFont` (falls back to `font`), `codeFont` (default Source Code), `baseFontSize` (int px, default 16, NOT separately settable for the sidebar), `baseFontWeight` (multiples of 50 from 100 to 600) — [Customize fonts](https://docs.streamlit.io/develop/concepts/configuration/theming-customize-fonts)
- `[theme.sidebar]` overrides almost every option for the sidebar only. When unset, the sidebar swaps the main background colors — [Customize colors and borders](https://docs.streamlit.io/develop/concepts/configuration/theming-customize-colors-and-borders); [Theming overview](https://docs.streamlit.io/develop/concepts/configuration/theming)

**Version introduced (from release notes)**
- 1.44.0 (2025-03-25): advanced theming ("change fonts, colors, and roundness without CSS"), `st.badge`, and `st.context` exposes the user's locale — [2025 release notes](https://docs.streamlit.io/develop/quick-reference/release-notes/2025)
- 1.45.0 (2025-04-29): `theme.fontFaces` supports font style (bug fix); `st.html` inserts CSS file contents as `<style>` — [2025 notes](https://docs.streamlit.io/develop/quick-reference/release-notes/2025)
- 1.46.0 (2025-06-18): `theme.dataframeBorderColor`, `theme.buttonRadius`, `theme.codeFontSize`; font faces support weight and unicode ranges; `st.context.theme` (light/dark); top navigation; fix for localized number formats in locales that use commas — [2025 notes](https://docs.streamlit.io/develop/quick-reference/release-notes/2025)
- 1.47.0 (2025-07-16): `baseFontWeight`, `chartCategoricalColors`, `chartSequentialColors`, `codeFontWeight`, `dataframeHeaderBackgroundColor`, `headingFontSizes`, `headingFontWeights`, `linkUnderline`; print fix that removes extra top padding — [2025 notes](https://docs.streamlit.io/develop/quick-reference/release-notes/2025)
- 1.48.0 (2025-08-05): `codeFontWeight` per sidebar — [2025 notes](https://docs.streamlit.io/develop/quick-reference/release-notes/2025)
- 1.50.0 (2025-09-23): color palette options (red…grey); `font`, `headingFont` and `codeFont` accept URLs to externally hosted font CSS — [2025 notes](https://docs.streamlit.io/develop/quick-reference/release-notes/2025)
- 1.51.0 (2025-10-29): custom light AND dark themes in one app, reusable themes via shared files; `codeTextColor`, `linkColor`; Custom Components v2 — [2025 notes](https://docs.streamlit.io/develop/quick-reference/release-notes/2025)
- 1.53.0 (2026-01-14): CSS custom properties for individual heading sizes and weights; theme preference persists into new sessions — [2026 notes](https://docs.streamlit.io/develop/quick-reference/release-notes/2026)
- 1.54.0 (2026-02-04): chart palette configurable through theming, `chartDivergingColors` (Plotly, Altair, Vega-Lite) — [2026 notes](https://docs.streamlit.io/develop/quick-reference/release-notes/2026)
- 1.55 (2026-03-03): `metricValueFontSize`, `metricValueFontWeight` — [2026 notes](https://docs.streamlit.io/develop/quick-reference/release-notes/2026)
- 1.62.0 (2026-08-19): chart colors settable separately for light, dark and sidebar; font-weight settings accept increments of 50; derived code and dataframe-header colors respect custom backgrounds — [2026 notes](https://docs.streamlit.io/develop/quick-reference/release-notes/2026)
- 1.65.0 (2026-10-02): `dataframeHeaderTextColor`; a custom `borderColor` no longer fills the `st.toggle` off track; stronger `showSidebarBorder` hover — [Release notes](https://docs.streamlit.io/develop/quick-reference/release-notes)

**Fonts offline**
- `[[theme.fontFaces]]` tables take `family`, `url` (e.g. `url="app/static/Tuffy-Regular.ttf"`), and optional `weight`, `style` and `unicodeRange`. They need `[server] enableStaticServing = true`. Self-hosted formats are OTF, TTF, WOFF and WOFF2 — [Customize fonts](https://docs.streamlit.io/develop/concepts/configuration/theming-customize-fonts)
- Streamlit's built-in fonts ship with the library, so clients don't download them from a third party. Google or Adobe fonts load only if you configure a `"Name:https://fonts.googleapis.com/..."` string, and the docs warn this can send user data such as IP addresses to external servers — [Customize fonts](https://docs.streamlit.io/develop/concepts/configuration/theming-customize-fonts)
- Static file serving supports common font extensions since 1.43.0 (2025-03-04) — [2025 notes](https://docs.streamlit.io/develop/quick-reference/release-notes/2025)
- Changing `[[theme.fontFace]]` requires a server restart, while most other theme changes apply on rerun — [Theming overview](https://docs.streamlit.io/develop/concepts/configuration/theming)

**Light/dark**
- Users switch themes in the settings menu. `[theme.light]` and `[theme.dark]` (and their sidebar subsections) can set colors, fonts and borders separately. Base scheme, base font, metric value font and sidebar border are global only. The base can inherit from Streamlit light/dark or an external theme TOML file — [Theming overview](https://docs.streamlit.io/develop/concepts/configuration/theming)
- `st.context.theme` reports light or dark (1.46.0) — [2025 notes](https://docs.streamlit.io/develop/quick-reference/release-notes/2025)

### Inferences
- An executive look (one neutral background, a single dark accent, a fine border, small radius, a serious sans for text plus a tabular-figure font for numbers, and branded chart palettes) can be expressed entirely in `config.toml`, with no fragile CSS. Bundling WOFF2 files in `static/` and pointing `fontFaces` at `app/static/...` keeps the app fully offline.
- `primaryColor` must be dark enough for white text, which constrains brand palettes. A pale accent will fail contrast.
- Pin the Streamlit version in requirements. Many of these options are 1.44 to 1.62, and option names changed over 2025 (e.g. palette, chart diverging colors).

### Gaps
- The docs give no per-option "added in" annotations. Version mapping comes from release notes, and some options (e.g. `showWidgetBorder`, `baseRadius`, `borderColor`, `fontFaces`) presumably arrived in the 1.44 "advanced theming" batch, but the notes I read do not list them individually.
- The docs do not say whether `font = "Name:<url>"` can point at a local static CSS file. Self-hosting is documented only through `fontFaces`.
- No documented way to enable OpenType features (e.g. `font-feature-settings: "tnum"`) through config. That would need CSS.

## 2. Layout and navigation primitives (st.navigation top, columns, containers, metric, dataframe/data_editor column config, st.html, CSS injection, st.context)

### Takeaway
2025 to 2026 releases added most of the layout primitives a dashboard needs: top navigation, flex/horizontal containers with gap, alignment and wrap, `width`/`height` on nearly every element, `st.space`, a pinned `st.bottom`, side-drawer dialogs, column alignment and pinning in dataframes, and metric sparklines, icons and font controls. The weak spots for a Spanish construction app are number localization and CSS. `NumberColumn` has no documented way to force a decimal comma (only browser-locale "localized" and printf with comma thousands). CSS injection via `st.html` works, but only the `st-key-<key>` classes and `--st-*` variables are documented hooks. Other internal classes are not a supported API.

### Cited Findings
**Navigation**
- `st.navigation(position="top")` arrived in 1.46.0 (2025-06-18) — [2025 notes](https://docs.streamlit.io/develop/quick-reference/release-notes/2025)
- 1.53: sidebar nav is hidden when top nav is used, `st.logo` works with top nav, and `st.set_page_config` sets the default sidebar width. 1.55: Markdown in page titles and section labels, and `st.Page(visibility=...)` hides pages while keeping them routable. 1.56: `st.navigation(expanded=...)` and external URLs in `st.Page` — [2026 notes](https://docs.streamlit.io/develop/quick-reference/release-notes/2026)

**Layout**
- 1.46: most elements gained `width`. 1.48 (2025-08-05): horizontal flex containers with alignment, direction and gap. 1.51: `st.space`. 1.52: `width="content"` for containers and dataframes, and `text_alignment` for markdown, titles and captions — [2025 notes](https://docs.streamlit.io/develop/quick-reference/release-notes/2025)
- 1.56: tabs, expanders and popovers keep state across reruns; `st.container(autoscroll=...)`. 1.57: `st.bottom` pinned container. 1.60: `st.tabs(height=...)`, `st.columns(gap=<px int>)`. 1.62: `wrap` on columns and horizontal containers. 1.63: `icon=` on title, header and subheader. 1.65: `st.dialog(position="left"|"right")` side drawer; tabs and expanders `bind="query-params"` — [2026 notes](https://docs.streamlit.io/develop/quick-reference/release-notes/2026); [Release notes](https://docs.streamlit.io/develop/quick-reference/release-notes)

**st.metric**
- 1.47: `height`, and a background color on deltas. 1.49: sparklines. 1.50: `decimal.Decimal` support. 1.52: `delta_arrow` — [2025 notes](https://docs.streamlit.io/develop/quick-reference/release-notes/2025)
- 1.55: `metricValueFontSize`/`metricValueFontWeight` and delta descriptions. 1.60: zero deltas shown in neutral grey. 1.61: `icon` parameter — [2026 notes](https://docs.streamlit.io/develop/quick-reference/release-notes/2026)

**st.dataframe / st.data_editor**
- `NumberColumn(label, *, width, help, disabled, required, pinned, alignment, default, format, min_value, max_value, step)`. Predefined formats: plain, localized, percent, dollar, euro, yen, accounting, bytes, compact, scientific, engineering. Printf-style strings such as `"£ %.2f"` are allowed, and `"%,d"` gives a comma thousands separator. `alignment` takes left, center or right (numbers default to right). `pinned=True` keeps the column visible on the left — [NumberColumn docs](https://docs.streamlit.io/develop/api-reference/data/st.column_config/st.column_config.numbercolumn)
- The docs only say "localized" means "default locale format". They do not say how the locale is chosen, and they document no way to force a decimal comma or a custom thousands separator — [NumberColumn docs](https://docs.streamlit.io/develop/api-reference/data/st.column_config/st.column_config.numbercolumn)
- 1.42: column menus for sorting and pinning, plus drag-reorder. 1.43: preconfigured formats, row height, column hiding, and end users can change formats. 1.46: localized formats fixed for locales with commas. 1.52: `placeholder` for nulls — [2025 notes](https://docs.streamlit.io/develop/quick-reference/release-notes/2025)
- 1.55: sprintf comma thousands in Number and Progress columns. 1.56: `alignment` parameter for columns. 1.59: `ButtonColumn`, `MarkdownColumn`, column statistics. 1.61: lazy loading for large frames. 1.65: leading decimals kept (`.07` commits 0.07); configurable header text color — [2026 notes](https://docs.streamlit.io/develop/quick-reference/release-notes/2026); [Release notes](https://docs.streamlit.io/develop/quick-reference/release-notes)

**st.html and CSS**
- 1.45: `st.html` inserts CSS file contents as `<style>` tags and renders at 100% width. 1.52: `st.html(unsafe_allow_javascript=...)` — [2025 notes](https://docs.streamlit.io/develop/quick-reference/release-notes/2025)
- 1.61: string paths to `st.html`/`st.iframe` are deprecated (use `pathlib.Path`) — [2026 notes](https://docs.streamlit.io/develop/quick-reference/release-notes/2026)
- Elements with a `key` get the CSS class `st-key-<slugified key>`. Containers accept keys since 1.39.0. One forum user reported the class missing on 1.41.1 — [Forum: key in st.container](https://discuss.streamlit.io/t/key-used-in-st-container-not-visible-in-html/91902); [st.container docs](https://docs.streamlit.io/library/api-reference/layout/st.container); [Forum: different CSS per button](https://discuss.streamlit.io/t/differenet-css-to-different-button/93898)
- Custom Components v2 get `--st-*` CSS custom properties derived from the current theme (primary, background, text, border, fonts, radii, font sizes and weights, dataframe header, the 7-hue palette, metric font, chart palettes). They follow light/dark and inherit `theme.sidebar` inside the sidebar. Components are Shadow-DOM isolated by default (`isolate_styles=True`). The docs say nothing about the stability of Streamlit's internal class names — [Components v2 theming](https://docs.streamlit.io/develop/concepts/custom-components/components-v2/theming)

**st.context**
- `st.context.locale` (1.44), `url`/`ip_address`/`is_embedded` (1.45), `st.context.theme` (1.46), key notation `st.context["timezone"]` (1.63) — [2025 notes](https://docs.streamlit.io/develop/quick-reference/release-notes/2025); [2026 notes](https://docs.streamlit.io/develop/quick-reference/release-notes/2026)

### Inferences
- For "Bs 1.234.567,89"-style figures, the documented paths are (a) `format="localized"`, which presumably follows the browser locale (the 1.46 fix for comma locales and `st.context.locale` suggest this, but it is unconfirmed), or (b) pre-formatted string columns, which lose numeric sorting and editing. On a locked-down Windows machine, the browser locale (es-VE vs en-US) would decide the output. This needs an empirical test.
- The safe CSS strategy is: theme in config, then `st-key-*` classes on keyed containers, then `--st-*` variables. Selectors on `data-testid` or emotion-generated classes are undocumented and should be treated as breakable on each upgrade, so pin the Streamlit version and re-check on upgrade.
- `st.dialog(position="right")` (1.65) plus `st.bottom` (1.57) give drawer and footer-bar patterns that previously needed hacks.

### Gaps
- No official statement found on the stability of internal CSS class names (`st-emotion-cache-*`, `data-testid`). It is widely assumed in the community that they change, but I did not fetch a primary source confirming specific breakages.
- I did not find the exact version of `st.metric(border=True)` or the `st.container(border=True)` option in the notes I read.
- The behaviour of `NumberColumn(format="localized")` with an es-VE/es-ES browser locale is undocumented. It needs a manual test.

## 3. Third-party components: license, maintenance and offline (CDN) status

### Takeaway
All eight components are permissively licensed (MIT or Apache-2.0) at the wrapper level. Maintenance is split. shadcn-ui, extras, aggrid and echarts are active in 2026, while option-menu, antd-components, elements and the original lightweight-charts are dormant (last code in 2022 to 2024). Wheel inspection shows most bundle their JS and icon fonts locally. The offline risks are streamlit-elements (Monaco editor and media players from jsdelivr/cdnjs, Google Fonts), some streamlit-extras modules (Google Material Symbols, the stlite sandbox from jsdelivr), and streamlit-aggrid's AG Grid theming font loader. streamlit-aggrid also bundles AG Grid Enterprise code that needs a commercial license if enterprise features are enabled.

### Cited Findings
| Package | Latest (date) | License | Repo last push / stars | CDN refs found in wheel |
|---|---|---|---|---|
| streamlit-shadcn-ui | 1.4.0 (2026-09-08) | MIT | 2026-09-08 / 1,156 | none (only W3C/redux doc URLs) |
| streamlit-extras | 1.6.0 (2026-05-15) | Apache-2.0 | 2026-08-31 / 973 | fonts.googleapis.com Material Symbols; cdn.jsdelivr.net @stlite/mountable |
| streamlit-option-menu | 0.4.0 (2024-10-09) | MIT (GitHub) | 2024-10-09 / 705, 28 open issues | none; bootstrap-icons WOFF/WOFF2 bundled |
| streamlit-elements (MUI) | 0.1.0 (2022-04-25) | MIT | 2023-09-01 / 922 | fonts.googleapis.com; jsdelivr monaco-editor@0.28.1; cdnjs dash.js; jsdelivr hls.js/flv.js; cdn.embed.ly |
| streamlit-antd-components | 0.3.2 (2024-01-19) | MIT (GitHub) | 2024-08-05 / 558, 62 open issues | none; bootstrap-icons fonts bundled |
| streamlit-aggrid | 1.2.1.post2 (2025-12-29); 2.0.0rc1 (2026-08-18) | MIT (wrapper) | 2026-08-18 / 1,297, 105 open issues | fonts.googleapis.com/css2 template (AG Grid theming font loader) |
| streamlit-echarts | 0.7.0 (2026-06-08) | MIT | 2026-10-07 / 637 | none (only doc URLs) |
| streamlit-lightweight-charts | 0.7.20 (2023-05-22) | MIT | 2023-07-24 / 225 | none |
| streamlit-lightweight-charts-v5 (fork) | 0.2.0 (2026-07-09) | MIT on PyPI, NOASSERTION on GitHub | 2026-09-03 / 26 | not inspected |

Sources: PyPI JSON for each ([shadcn-ui](https://pypi.org/project/streamlit-shadcn-ui/), [extras](https://pypi.org/project/streamlit-extras/), [option-menu](https://pypi.org/project/streamlit-option-menu/), [elements](https://pypi.org/project/streamlit-elements/), [antd-components](https://pypi.org/project/streamlit-antd-components/), [aggrid](https://pypi.org/project/streamlit-aggrid/), [echarts](https://pypi.org/project/streamlit-echarts/), [lightweight-charts](https://pypi.org/project/streamlit-lightweight-charts/), [lightweight-charts-v5](https://pypi.org/project/streamlit-lightweight-charts-v5/)); GitHub API repo metadata ([ObservedObserver/streamlit-shadcn-ui](https://github.com/ObservedObserver/streamlit-shadcn-ui), [arnaudmiribel/streamlit-extras](https://github.com/arnaudmiribel/streamlit-extras), [victoryhb/streamlit-option-menu](https://github.com/victoryhb/streamlit-option-menu), [okld/streamlit-elements](https://github.com/okld/streamlit-elements), [nicedouble/StreamlitAntdComponents](https://github.com/nicedouble/StreamlitAntdComponents), [PablocFonseca/streamlit-aggrid](https://github.com/PablocFonseca/streamlit-aggrid), [andfanilo/streamlit-echarts](https://github.com/andfanilo/streamlit-echarts), [freyastreamlit/streamlit-lightweight-charts](https://github.com/freyastreamlit/streamlit-lightweight-charts), [locupleto/streamlit-lightweight-charts-v5](https://github.com/locupleto/streamlit-lightweight-charts-v5)); CDN column from my own wheel inspection on 2026-10-13.

- streamlit-aggrid README: "Consider purchasing a license from Ag-Grid if you are going to use enterprise features!". `enable_enterprise_modules` was added in 0.1.3 and `license_key` in 0.1.7. 1.1.3 "fixes enterprise modules being enabled by default". The bundled AG Grid is 34.3.1. Theming has "partial support", and `theme='streamlit'` mimics the Streamlit look — [streamlit-aggrid README](https://github.com/PablocFonseca/streamlit-aggrid)
- Wheel inspection of streamlit-aggrid 1.2.1.post2 finds `ag-grid-enterprise` code (about 610 references), `LicenseManager`, `licenseKey` and `watermark` strings, so enterprise code ships in the wheel — [streamlit-aggrid on PyPI](https://pypi.org/project/streamlit-aggrid/) (my inspection)

### Inferences
- Safe offline set for Sílice: native `st.dataframe`/`st.data_editor` (preferred), streamlit-echarts (active, MIT, no CDN), streamlit-shadcn-ui (active, MIT, no CDN; it gives cards, badges and tabs in shadcn style), and option-menu/antd-components only if their dormancy is acceptable (they bundle their icons, but no updates since 2024 raises compatibility risk with Streamlit 1.6x).
- Avoid streamlit-elements: abandoned since 2022 and loads several CDN assets. Use streamlit-extras module by module and audit any module that pulls Material Symbols or stlite.
- streamlit-aggrid: keep `enable_enterprise_modules=False`. Enterprise features (row grouping, pivot, Excel export, etc.) would require an AG Grid commercial license, and its theming font loader could reach Google Fonts if a Google font is configured. The 2.0 line is still a release candidate.
- Wrapper licenses are permissive, but each bundles third-party JS (MUI, Ant Design, ECharts Apache-2.0, AG Grid, TradingView lightweight-charts Apache-2.0 with attribution requirements). A license audit of bundled JS notices is still needed for a "propietaria" (proprietary) distribution.

### Gaps
- I did not verify each component's compatibility with Streamlit 1.65 empirically (no install or run, per the project's no-new-tests constraint), and I did not check the CDN status of the lightweight-charts-v5 fork.
- AG Grid's current Community/Enterprise feature split and watermark behaviour were not fetched from ag-grid.com.
- The CDN grep only covers literal URLs. Runtime-constructed URLs or the default MUI Roboto font in streamlit-elements may add further network calls.

## 4. Known limitations for executive polish: rerun latency, fixed widgets, theming gaps, printing/PDF, accessibility

### Takeaway
The biggest remaining limits are structural, not cosmetic. The whole-script rerun model (now much mitigated by fragments, parallel and event-scoped fragment reruns, background cache refresh and async), widget internals that can only be restyled through undocumented CSS, and unreliable browser printing/PDF of multi-page or wide layouts. Accessibility improved substantially through 2026 (alt text, keyboard navigation, reduced motion).

### Cited Findings
- Rerun mitigation: 1.58 `@st.fragment(parallel=True)`. 1.59: fragments can write to outside containers. 1.61: `refresh_mode="background"` cache refresh and lazy dataframes. 1.63: event-scoped fragment reruns (`@st.fragment(key=...)` with targeted `st.rerun`), plus `on_change="ignore"` for slider and text_input. 1.64: async/await in app code, async cached functions, `st.text_input(live=True)`, coalesced reruns. 1.65: `on_change="ignore"` on most widgets — [2026 notes](https://docs.streamlit.io/develop/quick-reference/release-notes/2026); [Release notes](https://docs.streamlit.io/develop/quick-reference/release-notes)
- Server: 1.57 replaced Tornado with Starlette/Uvicorn and exposed `st.App`. 1.59 added `App.run()` for `python app.py` — [2026 notes](https://docs.streamlit.io/develop/quick-reference/release-notes/2026)
- Theming gaps documented: `baseFontSize` and `baseFontWeight` can't be set per sidebar; interactive charts and videos always have square corners; `primaryColor` must suit white text — [Customize fonts](https://docs.streamlit.io/develop/concepts/configuration/theming-customize-fonts); [Customize colors and borders](https://docs.streamlit.io/develop/concepts/configuration/theming-customize-colors-and-borders)
- Offline flag in core: `st.pydeck_chart` and `st.map` default to Carto tiles (1.46), which need internet — [2025 notes](https://docs.streamlit.io/develop/quick-reference/release-notes/2025)
- Printing: users report wide layouts cut off randomly when printing, the sidebar printing or leaving empty space, output stopping around page 5, and `@media print` page-break CSS not helping. No official fix found — [Forum: printing wide layout](https://discuss.streamlit.io/t/printing-page-with-page-layout-wide/94605); [Forum: print to separate pages](https://discuss.streamlit.io/t/how-can-i-formate-my-streamlit-printing-output-to-print-each-section-in-different-pages/60791); [Forum: Save as PDF blank pages](https://discuss.streamlit.io/t/print-save-as-pdf-produce-blank-pages/50497); [Forum: download whole page as PDF](https://discuss.streamlit.io/t/download-whole-streamlit-page-as-pdf/45566). The only official print change I found is the 1.47 removal of extra top padding — [2025 notes](https://docs.streamlit.io/develop/quick-reference/release-notes/2025). A common workaround is generating the report separately as HTML/CSS templates, with a slightly different layout from the app — [Medium: workaround to PDF report](https://medium.com/@gerardsho/a-workaround-to-pdf-report-in-python-streamlit-bc86089f2329)
- Related building blocks: `st.pdf` viewer (1.49), and `st.download_button` accepts a callable for on-demand generation (1.52) — [2025 notes](https://docs.streamlit.io/develop/quick-reference/release-notes/2025)
- Accessibility 2026: tooltips and anchors keyboard-focusable (1.53); tab overflow arrows and an accessible app menu (1.55); multiselect keyboard nav and WAI-ARIA dropdown focus (1.61); accessible segmented date fields (1.62); reduced-motion spinner (1.63); `alt` on images, charts, maps and dataframes, and 24px toolbar targets (1.65) — [2026 notes](https://docs.streamlit.io/develop/quick-reference/release-notes/2026); [Release notes](https://docs.streamlit.io/develop/quick-reference/release-notes)

### Inferences
- For audit and budget documents that must be printed or signed, the deliverable should be a server-generated PDF/DOCX (FastAPI side) offered via `st.download_button(callable)` and previewed with `st.pdf`. Don't rely on browser printing of the Streamlit page.
- Perceived latency can be made acceptable with fragments around editors and tables, plus `on_change="ignore"`. Full-page reruns still make the app feel less "native" than a SPA on heavy pages.

### Gaps
- I found no authoritative write-ups (Streamlit blog or case studies) describing specific polished executive Streamlit apps and their techniques. The "your streamlit apps don't have to suck" article surfaced in search but was not fetched or verified.
- No measured latency benchmarks for Streamlit 1.6x reruns.

## 5. Effort signals: restyle vs. rewrite

### Takeaway
No source gives quantified effort figures. The evidence supports a staged restyle: config-only theme, then layout refactor with native primitives, then a minimal keyed CSS layer, then reports generated outside the UI. That is far smaller in scope than a rewrite, because the 2025 to 2026 features cover most former CSS hacks. A rewrite (e.g. React SPA on the existing FastAPI) is justified only if pixel-exact control, flawless printing or a non-rerun interaction model is a hard requirement.

### Cited Findings
- Advanced theming in 1.44 explicitly lets you change "fonts, colors, and roundness without CSS" — [2025 notes](https://docs.streamlit.io/develop/quick-reference/release-notes/2025)
- Most former layout hacks now have native APIs: top nav (1.46), flex containers (1.48), `st.space` (1.51), `st.bottom` (1.57), side dialogs (1.65), column wrap (1.62) — [2025 notes](https://docs.streamlit.io/develop/quick-reference/release-notes/2025); [2026 notes](https://docs.streamlit.io/develop/quick-reference/release-notes/2026); [Release notes](https://docs.streamlit.io/develop/quick-reference/release-notes)
- Custom Components v2 (1.51; style isolation and optional html/js/css in 1.53) let a team write small bespoke widgets that inherit `--st-*` theme variables, an intermediate path between a restyle and a rewrite — [2025 notes](https://docs.streamlit.io/develop/quick-reference/release-notes/2025); [2026 notes](https://docs.streamlit.io/develop/quick-reference/release-notes/2026); [Components v2 theming](https://docs.streamlit.io/develop/concepts/custom-components/components-v2/theming)
- Breaking removals continue release to release (e.g. `use_column_width` removed in 1.61, `st.cache` in 1.62, `use_container_width` on plotly/vega in 1.57). This is a maintenance cost to budget for on any Streamlit path — [2026 notes](https://docs.streamlit.io/develop/quick-reference/release-notes/2026)

### Inferences
- Typical restyle work items: (1) `config.toml` with light and dark themes, `fontFaces` and palettes; (2) `static/` with WOFF2 fonts and logo; (3) replacing sidebar nav with `position="top"` and grouping pages; (4) KPI rows with `st.metric` (border, sparkline, icon) inside keyed horizontal containers; (5) a `column_config` pass on every dataframe (formats, alignment, pinning, widths); (6) a small `st.html` CSS file limited to `st-key-*` selectors; (7) report export through FastAPI. Each item is local to the UI layer and does not touch the core or the API.
- Main risk is the Spanish number format (decimal comma). If `format="localized"` doesn't render es-VE correctly offline, it needs string-formatted display columns or a custom component, which is the one place where effort could grow.
- Pin `streamlit==1.65.x` (or 1.62 as requested) and treat any CSS beyond documented hooks as version-coupled.

### Gaps
- No published effort estimates or case studies comparing a Streamlit restyle with a rewrite were found.
