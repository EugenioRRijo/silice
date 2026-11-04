# Enterprise design systems and executive-dashboard references for Sílice (data-dense budgeting and audit UI)

Research date: 2026-10-13. Scope: which mature design systems and executive product UIs a small team building "Sílice" (Spanish-language, desktop-style web app for APU / construction budgets and their audit; estimator + administrator/manager; USD and bolívares; price alerts; spreadsheet-like editable sheet; KPI summaries; findings tables with severity; an Excel workbook replica) could adopt as its visual model. Context note: per the repository's own agent roles, Sílice's UI layer is Streamlit (Python), so React-only component libraries cannot be dropped in directly; tokens, CSS and documented patterns are what transfer.

## 1. Which mature enterprise design systems fit a data-dense financial/audit UI (principles, tables, density, severity tokens, accessibility, license, non-React assets)?

### Takeaway
IBM Carbon and SAP Fiori are the best-documented references for dense financial/audit tables and status semantics (Carbon: five explicit row heights, a full status-indicator pattern with 3:1 contrast and "never color alone"; Fiori: cozy/compact density and negative/critical/positive/neutral semantics applied to numbers and KPIs). Carbon is the most adoptable for a small non-React team (Apache-2.0, vanilla CSS/JS and Web Components). Fluent 2 (MIT, Web Components) and Ant Design (MIT) are viable secondaries. GOV.UK is the clarity benchmark for numeric tables. Atlassian has licensing restrictions, and Material 3 lacks a data table on the web.

### Cited Findings

**IBM Carbon**
- Data-table density has five sizes: xs 24px, sm 32px, md 40px (the default), lg 48px and xl 64px. The header row "should always match the row size of the table". xl is only for two-line rows. — [Carbon Data table usage](https://carbondesignsystem.com/components/data-table/usage/)
- Toolbar and batch-action bar heights match the row height. The toolbar takes at most five global actions (settings, complex filters, export, edit) and anything beyond goes in an overflow. A batch action bar appears once rows are selected, and row-level actions are disabled while it is active. — [Carbon Data table usage](https://carbondesignsystem.com/components/data-table/usage/)
- Zebra striping is an optional modifier. Row hover "should always be enabled, even on non-interactive rows" to help scanning. Sorting cycles through three states, and the unsorted icon appears only on hover. Skeleton states are preferred over spinners for loading. — [Carbon Data table usage](https://carbondesignsystem.com/components/data-table/usage/)
- The Carbon data-table usage page does NOT cover right-aligning numbers, sticky or frozen columns, empty states or inline editing. — [Carbon Data table usage](https://carbondesignsystem.com/components/data-table/usage/)
- Status pattern: there are three attention levels (high: errors, exceptions and destructive confirmations; medium: acknowledgements and progress; low: something ready or changed). Product teams define their own severity levels. When statuses are consolidated, the highest-attention color wins. — [Carbon Status indicators](https://carbondesignsystem.com/patterns/status-indicator-pattern/)
- Status colors:
  - Red 60 #da1e28: danger or error
  - Orange 40 #ff832b (outline Orange 60 #ba4e00): serious warning
  - Yellow 30 #f1c21b (outline Yellow 60 #8e6a00): regular warning
  - Green 50 #24a148: success
  - Blue 70 #0043ce: information
  - Gray 60 #6f6f6f: draft or not started
  - Purple 60 #8a3ffc: outlier or undefined

  — [Carbon Status indicators](https://carbondesignsystem.com/patterns/status-indicator-pattern/)
- Accessibility rules for status:
  - Use at least two of color, shape or symbol.
  - Keep 3:1 non-text contrast between indicator colors, and between the indicator and the background.
  - Shape-only indicators need outlines and text labels.

  — [Carbon Status indicators](https://carbondesignsystem.com/patterns/status-indicator-pattern/)
- Indicator types: icon indicators (20px icon with 16pt type, or 16px with 14pt) and shape indicators (16px, "best for … scanning large data sets"). Badges show counts. The **differential indicator** is a +/−, caret or arrow, "used for showing changes in statistics or financial deltas"; color is optional when a sign or arrow is present. — [Carbon Status indicators](https://carbondesignsystem.com/patterns/status-indicator-pattern/)
- License: Apache-2.0. Carbon offers a vanilla CSS/JS implementation (`carbon-components`) and Web Components built on Custom Elements v1 and Shadow DOM v1 (`@carbon/web-components`, Apache-2.0), in addition to React. — [Wikipedia: Carbon Design System](https://en.wikipedia.org/wiki/Carbon_Design_System); [carbon-web-components README (jsDelivr)](https://cdn.jsdelivr.net/npm/carbon-web-components@1.21.0/README.md); [@carbon/web-components](https://mcp.depscope.dev/pkg/npm/%40carbon/web-components)

**SAP Fiori**
- Content density: SAPUI5 has cozy and compact modes. In compact mode the font size stays the same but components and spacing shrink. The cozy touch target is 2.75rem (44px), and compact rows and toolbars can be 2rem (32px). Compact is enabled with the `sapUiSizeCompact` class, and density should be set explicitly per device. — [SAP Fiori: Content Density (Cozy and Compact)](https://www.sap.com/design-system/fiori-design-web/v1-139/foundations/visual/cozy-compact)
- Numbers (Object Number) take the same semantic states as Object Status: negative (error), critical (warning), positive (success) and neutral (none), plus an optional unit property. When a number is the row's key attribute it is shown emphasized; numbers meant for comparison are non-emphasized. Object numbers do not wrap or truncate, so large numbers need appropriate formatting. — [SAP Fiori: Object Display Elements (v1.139)](https://www.sap.com/design-system/fiori-design-web/v1-139/ui-elements/object-display-elements/usage); [Object Number (v1.28)](https://experience.sap.com/fiori-design-web/v1-28/object-number)
- KPI tile: KPI values appear as "large, easy-to-recognize digits". Tiles can show deviation arrows, negative values and scaling factors, and support semantic colors. No icons are allowed on KPI tiles. The monitoring tile shows status or counts and can apply semantic colors to a status bar. — [SAP Fiori: Tile (v1.71)](https://www.sap.com/design-system/fiori-design-web/v1-71/ui-elements/tile/usage); [Tile (v1.38)](https://experience.sap.com/fiori-design-web/v1-38/tile/)
- Analytical card: a KPI header with the KPI value (mandatory, semantic colors), an optional trend arrow, and **target and deviation as mandatory fields**, either relative or absolute. Older guidance colors the KPI red, green or gray. For trends it recommends line charts with no more than four lines per card. This guidance is older (2017-era versions). — [SAP Fiori: Analytical Card (v1.44)](https://experience.sap.com/fiori-design-web/v1-44/analytical-card)
- The current Fiori "Formatting numbers" page (sap.com/design-system/…/formatting-numbers) returned HTTP 403 to automated fetch, so its locale and alignment rules could not be quoted here. — [redirect target](https://www.sap.com/design-system/fiori-design-web/foundations/best-practices/ui-elements/formatting/formatting-numbers)

**Microsoft Fluent 2**
- Spacing uses a 4px base unit, with tokens from `sizeNone` (0) to `size560` (56px); 2, 6 and 10 exist for icon padding. Minimum targets are 44x44 on web. The guidance warns that "too much dense information can also be disorienting" and offers no explicit density modes on the layout page. — [Fluent 2: Layout](https://fluent2.microsoft.design/layout)
- License: MIT for all files in the repository. Fonts and icons fall under a separate assets license (aka.ms/fluentui-assets-license). Packages: `@fluentui/react-components` (v9), `@fluentui/react` (v8) and `@fluentui/web-components`. — [microsoft/fluentui on GitHub](https://github.com/microsoft/fluentui)

**Salesforce Lightning (SLDS)**
- SLDS 2 arrived in Spring '25. It separates structure from visual design through "styling hooks", which are CSS custom properties: global `--slds-g-*` is supported, while component-level `--slds-c-*` is not yet supported in SLDS 2. — [Salesforce: Compare SLDS versions](https://developer.salesforce.com/docs/platform/lwc/guide/create-components-css-slds1-slds2.html); [Styling hooks](https://developer.salesforce.com/docs/platform/lwc/guide/create-components-css-custom-properties)
- Compact and Comfy density are user-facing settings powered by SLDS design tokens and classes (2018 blog, older). — [Salesforce dev blog: density settings (2018)](https://developer.salesforce.com/blogs/2018/08/new-density-settings-for-the-lightning-experience-ui-in-winter-19)

**Atlassian Design System**
- The official ADS license (last updated 2025-03-13) grants use only for work that interoperates or integrates with Atlassian products. OSS licenses may grant extra rights to the code itself. Community and staff replies say the component code is Apache-2.0 but logos, icons and branding are ADG-licensed and restricted. Which packages fall under ADG is not clearly documented. — [atlassian.design/license](https://atlassian.design/license); [Atlassian dev community: Atlaskit licensing](https://community.developer.atlassian.com/t/atlaskit-licensing/59672); [Usage of Atlaskit in non-Atlassian apps](https://community.developer.atlassian.com/t/usage-of-atlaskit-in-non-atlassian-apps/26944)

**Material 3**
- Material Web Components (MWC) is "currently in maintenance mode" with "no current work planned for new features or components". The **Data table was never built**: it is still listed as a "new component … we have not built yet". — [material-web roadmap](https://github.com/material-components/material-web/blob/main/docs/roadmap.md)

**Ant Design / Ant Design Pro**
- License: MIT, "Copyright (c) 2015-present Ant UED". The project advertises i18n "for dozens of languages" and CSS-in-JS theme customization, and links Ant Design Pro (pro.ant.design) and ProComponents. — [ant-design LICENSE](https://raw.githubusercontent.com/ant-design/ant-design/master/LICENSE); [ant-design on GitHub](https://github.com/ant-design/ant-design)

**GOV.UK Design System (clarity reference)**
- "Align the numbers to the right in table cells" when comparing numeric columns. Use the classes `govuk-table__header--numeric` and `govuk-table__cell--numeric` (or `format: "numeric"` in the Nunjucks macro). Use `<caption>` as the table's heading. Do not use tables for layout. Split very large tables across tables or pages. — [GOV.UK: Table](https://design-system.service.gov.uk/components/table/)
- License: Open Government Licence v3.0 (Crown copyright). — [GOV.UK: Table](https://design-system.service.gov.uk/components/table/)

### Inferences
- Primary model: **Carbon**. It is the only system here that combines all of these:
  - explicit numeric row-height tokens matching an "Excel-like" density (24/32px)
  - a written status-severity pattern that maps directly to audit findings (high/medium/low, plus purple for "outlier", which suits price-alert outliers)
  - a "differential indicator" made for financial deltas
  - a permissive license
  - assets usable outside React (plain CSS, Web Components)

  For Streamlit, the practical route is to copy Carbon's color and spacing values into CSS custom properties rather than import components.
- Secondary model: **Fiori**, for the *semantics* of numbers. Negative/critical/positive/neutral applied to the number itself, "target + deviation mandatory" on KPI headers, and emphasized vs non-emphasized numbers are all directly reusable for budget totals and variance KPIs. Its components (SAPUI5/UI5 Web Components) are a heavy dependency for a small team. Its license was not verified in this session (see Gaps).
- **GOV.UK** is the best plain-language reference for numeric tables (right alignment, captions, splitting large tables) and suits a thesis prototype that values clarity over branding.
- **Avoid as a visual base:** Atlassian (license restricted to the Atlassian ecosystem for branding and icons) and Material 3 (no web data table, MWC in maintenance mode).
- Ant Design (MIT) has the richest ready-made "admin" patterns (Pro), but it is React-only and its visual identity is strongly tied to the Ant look. Use it for pattern reference rather than adoption.

### Gaps
- Not verified this session: the SLDS repository license (commonly reported as BSD-3-Clause), the SAP Fiori guidelines and UI5 Web Components licenses, Fluent 2 data-grid density specifics, and the Carbon color-token names (the status page lists hex values and palette names only).
- Fiori's current number-formatting page (locale separators, right alignment of amounts) was blocked (403) and could not be quoted.
- No system's docs consulted here explicitly addressed the es-VE locale. Ant Design's es_ES locale pack exists by repute but was not confirmed in this session.
- WCAG conformance targets (e.g. "WCAG 2.1 AA") per system were not individually verified. Carbon's 3:1 non-text-contrast rule is the only cited figure.

## 2. What do well-regarded executive product UIs do for KPI tiles, financial tables, numeric alignment, status/severity, audit trails and budget-vs-actual comparisons?

### Takeaway
Stripe and Linear are the most cited references for "calm, dense, trustworthy" financial UIs, but the publicly available evidence is mostly third-party commentary (Stripe) or high-level redesign posts (Linear). The most concrete, normative guidance for budget-vs-actual comparisons comes from the IBCS notation (AC/PL/PY/FC with solid/outlined/hatched coding), widely implemented in Power BI visuals.

### Cited Findings
- **Linear**:
  - The March 2024 redesign aimed to "improve the hierarchy, balance, and density of all interface elements"; the Inbox got "increased density and better contrast". — [Linear changelog 2024-03-20](https://linear.app/changelog/2024-03-20-new-linear-ui)
  - The 2024 redesign moved theme generation from HSL to LCH for consistent appearance. — [How we redesigned the Linear UI](https://linear.app/blog/how-we-redesigned-the-linear-ui)
  - A later refresh (undated post, probably 2026 per an aggregator) says the challenge was "preserving that rich density of information without letting the interface feel overwhelming". Its principle is that not all elements should carry equal visual weight, and it moved toward a warmer, less saturated gray. — [Behind the latest design refresh](https://linear.app/now/behind-the-latest-design-refresh)
- **Stripe** (third-party analyses only; no official Stripe design write-up found):
  - Money amounts are right-aligned with decimal points aligned. Tables use tabular figures, and color is reserved for state ("state-only color"). — [925Studios: Stripe Dashboard breakdown](https://www.925studios.co/blog/stripe-dashboard-design-breakdown); [adminlte.io fintech dashboard examples](https://adminlte.io/blog/fintech-dashboard-design-examples/)
  - Hierarchy comes from typography and whitespace more than color. Home metrics are the ones that prompt action (e.g. disputes needing attention). Status uses icons plus subtle color. — [925Studios](https://www.925studios.co/blog/stripe-dashboard-design-breakdown)
  - A "Stripe-inspired" token file says every currency or count cell uses `tnum`, because without tabular numerals "number columns misalign". This is a third-party interpretation. — [shadcn.io Stripe-inspired DESIGN.md](https://www.shadcn.io/design/stripe)
- **Procore** (construction): it publishes its design system as React components (`@procore/core-react`, public GitHub repo) under a custom "Procore Developers License", not an OSI license. The license text was not found. — [@procore/core-react on npm](https://npmjs.com/package/@procore/core-react); [README via jsDelivr](https://cdn.jsdelivr.net/npm/@procore/core-react@12.47.0/README.md)
- **IBCS (budget vs actual), as implemented in Power BI ecosystems**:
  - Scenario codes: AC = actual, PL = plan/budget, PY = prior year, FC = forecast. The notation is AC solid dark, PY grey, PL outlined, FC hatched. The budget is "an empty frame that has to be filled up with the actuals". — [Zebra BI (A. Lapajne)](https://zebrabi.com/?p=5007); [Inforiver: variance analysis in Power BI](https://inforiver.com/blog/inforiver-analytics-plus/variance-analysis-powerbi-inforiver-analytics-plus/)
  - Variances are explicitly calculated and shown. Favourable variances are green and unfavourable red, which differs from simply positive vs negative. Actual, comparison and variance belong in one integrated visual. Labels are short, exact and horizontal. — [Inforiver](https://inforiver.com/blog/inforiver-analytics-plus/variance-analysis-powerbi-inforiver-analytics-plus/); [Zebra BI](https://zebrabi.com/?p=5007)
  - Caveat: these are vendor and practitioner summaries, not the normative IBCS document. — [IBCS](https://www.ibcs.com/?p=72984)
- **NN/g on dashboards** (2017, older):
  - Design for at-a-glance reading. Encode quantities with length and position (bars, lines).
  - Sort bars to aid comparison.
  - Avoid pie, donut, treemap, 3D and radial gauges, and prefer linear **bullet charts** against a target.
  - Don't use hue alone for magnitude, and pair color with shape.

  — [NN/g: Dashboards: Making Charts and Graphs Easier to Understand (2017)](https://www.nngroup.com/articles/dashboards-preattentive/)

### Inferences
- For Sílice's manager view, the IBCS "budget = outlined frame, actual = solid fill, variance = explicit bar or number colored favourable/unfavourable" convention fits the estimator-vs-auditor framing. "Favourable vs unfavourable" (not "positive vs negative") matters: a cost overrun is a *positive* delta that is *unfavourable*.
- Fiori's "KPI value + target + deviation are all mandatory" (section 1) and IBCS's integrated variance together give a defensible KPI-tile anatomy:
  - label
  - big value in the primary currency
  - secondary currency below
  - target/budget
  - signed deviation with arrow (Carbon differential indicator)
  - semantic color only on the deviation
- Stripe's "state-only color" and Linear's "unequal visual weight" principles suit a findings-heavy audit UI. Keep the chrome neutral (warm grays) and spend color only on severity.

### Gaps
- No primary design write-ups were found or fetched for Ramp, Brex, Vercel, Notion, Airtable, Smartsheet, Autodesk Construction Cloud or the Excel web UI. Claims about them would be unsourced.
- No primary source was found on audit-trail and activity-history visual patterns (e.g. Stripe's event log, Smartsheet cell history). This remains open.
- Power BI's own native KPI-visual guidance (Microsoft Learn) was not fetched.

## 3. Executive-dashboard component libraries (Tremor, shadcn/ui charts, Carbon Charts, Fluent UI charts): what they provide and licenses

### Takeaway
Tremor (React, Tailwind and Radix; now fully MIT including former paid Blocks after Vercel's January 2025 acquisition) and Carbon Charts (Apache-2.0, 26 charts, includes a vanilla-JS build) are the two strongest options. Carbon Charts is the only one confirmed usable without React, which matters for a Streamlit front end.

### Cited Findings
- **Tremor**:
  - Vercel acquired Tremor in January 2025. All Tremor products, including Tremor Blocks (formerly the Pro product), became free and open source. A mirror of the announcement says Blocks are released under MIT. — [Vercel: Vercel acquires Tremor](https://vercel.com/blog/vercel-acquires-tremor); [mirror](https://examples.vercel.com/blog/vercel-acquires-tremor)
  - Built on React, Tailwind CSS and Radix: 35 components and 300 copy-paste blocks for dashboards. The founders joined Vercel's Design Engineering team. — [Vercel blog](https://vercel.com/blog/vercel-acquires-tremor); [Walder Wyss deal note](https://www.walderwyss.com/fr/news/2025-01-22_walder-wyss-advises-on-exit-of-y-combinator-startup-tremor-labs-inc-to-vercel-inc)
  - A community thread asks about Tremor's ongoing support and a shadcn/ui port, with no official answer found. — [Vercel community: Tremor / shadcn and Vercel](https://community.vercel.com/t/tremor-shadcn-and-vercel/17242)
- **Carbon Charts**: Apache-2.0, "a component library of 26 charts" for vanilla JavaScript, Svelte, React, Vue.js and Angular (d3-based per other listings). Version 1.x is supported and 0.x is end-of-life. — [carbon-design-system/carbon-charts](https://github.com/carbon-design-system/carbon-charts)
- **Fluent UI**: the repository is MIT. The fetched README did not mention a charts package. — [microsoft/fluentui](https://github.com/microsoft/fluentui)

### Inferences
- With a Streamlit front end, Carbon Charts' vanilla build (via a custom component or HTML embed) is technically easier to adopt than Tremor or shadcn, which assume a React/Tailwind app. Alternatively, keep Python-native charts (Altair/Vega-Lite or Plotly, which Streamlit supports) and borrow only Carbon's or Tremor's *visual conventions*: palette, KPI-tile anatomy and bullet/variance bars.
- Tremor's MIT Blocks are a good *pattern catalog* (KPI cards with delta badges, bar lists, tables) to imitate even if the code is not used.

### Gaps
- shadcn/ui charts (reportedly built on Recharts, MIT) were not verified in this session.
- No Fluent UI charting package (e.g. `@fluentui/react-charting`) was confirmed, nor its license or maintenance status.
- Carbon Charts' latest release date was not visible on the fetched page.

## 4. Concrete patterns: findings/audit lists with severity, two-currency variance, tables with frozen columns and right-aligned tabular numbers, empty/error states, print/export

### Takeaway
The sourced patterns converge on four practices:
- right-aligned numbers using `font-variant-numeric: tabular-nums`
- frozen header row and identifier column
- severity shown with at least two cues (color plus icon/shape plus label) and the highest severity rolled up
- deltas shown as sign/arrow plus value, colored by favourable/unfavourable

For Spanish, the CLDR "minimum grouping digits = 2" rule hides the thousands separator on 4-digit numbers unless you force grouping. That breaks column alignment in a money table.

### Cited Findings
- **Tables**:
  - Freeze header rows and header columns when the table exceeds the screen.
  - Make the first column a human-readable identifier (e.g. the APU code or description, not an internal ID).
  - Put important columns first and related columns adjacent.
  - Show a visible indicator when filters are active or columns are hidden.
  - Use zebra striping or hover to keep place.

  — [NN/g: Data Tables: Four Major User Tasks (2022-04-03)](https://www.nngroup.com/articles/data-tables/)
- **Editing**: prefer a nonmodal side panel for row editing so the table stays visible. Edit-in-place suits only narrow tables, and the row should look distinct in edit mode to prevent accidental changes. Batch actions use row checkboxes with actions above or below the table. — [NN/g: Data Tables](https://www.nngroup.com/articles/data-tables/)
- **Numeric alignment**: right-align numbers to compare them. — [GOV.UK: Table](https://design-system.service.gov.uk/components/table/). `font-variant-numeric: tabular-nums` (OpenType `tnum`) makes all digits the same width so columns align, and combines with `lining-nums`. It is Baseline "widely available" since January 2020. — [MDN: font-variant-numeric](https://developer.mozilla.org/en-US/docs/Web/CSS/font-variant-numeric)
- **Severity**:
  - Use at least two of color, shape or symbol, with 3:1 contrast.
  - Consolidated status takes the highest attention level.
  - Use shape indicators for scanning large datasets.
  - Purple marks "outliers".

  — [Carbon Status indicators](https://carbondesignsystem.com/patterns/status-indicator-pattern/)
- **Number semantics**: negative/critical/positive/neutral states on numbers, an emphasized key number per row, and non-emphasized comparison numbers. — [SAP Fiori Object Display Elements](https://www.sap.com/design-system/fiori-design-web/v1-139/ui-elements/object-display-elements/usage)
- **Deltas**: Carbon's differential indicator (+/−, caret or arrow) is meant for financial deltas, with color optional when a sign is present. — [Carbon Status indicators](https://carbondesignsystem.com/patterns/status-indicator-pattern/). Use favourable/unfavourable coloring, not positive/negative. — [Inforiver](https://inforiver.com/blog/inforiver-analytics-plus/variance-analysis-powerbi-inforiver-analytics-plus/)
- **Empty and error states**:
  - Types: no data or first use, user action (no results, process completed), and error management (permissions, system, configuration, unsupported).
  - Content: a positive short title ("Start by adding…"), a body explaining the next step and why, and a primary action.
  - For errors, explain in plain language and "always provide a path to a solution".
  - When many widgets are empty, prefer text-only states and tertiary buttons. Decorative images use empty `alt`.

  — [Carbon: Empty states pattern](https://carbondesignsystem.com/patterns/empty-states-pattern/)
- **Loading**: use skeletons rather than spinners. — [Carbon Data table usage](https://carbondesignsystem.com/components/data-table/usage/)
- **Spanish number grouping**: ICU/CLDR sets minimum grouping digits to 2 for Spanish, so `1234` formats without a separator and `12345` becomes `12.345`. This is disputed (CLDR-13265). es_419 overrode it to 1 in past releases, and Latin American usage commonly separates 4-digit numbers. `Intl.NumberFormat` with `useGrouping: 'always'` forces `1.234`. — [CLDR-13265](https://unicode-org.atlassian.net/browse/CLDR-13265); [Tryton discussion: es and es_419](https://discuss.tryton.org/t/minimum-grouping-digits-for-spanish-es-and-es-419/3076); [lingo.dev: controlling thousands separators](https://lingo.dev/en/javascript-i18n/control-thousands-separators)

### Inferences
Concrete pattern set for Sílice, synthesized from the sources above:

1. **Hoja (editable sheet, "calcado" of the Excel)**
   - Use Carbon xs or sm density (24 or 32px rows). Right-align all amount cells with `tabular-nums lining-nums`.
   - Freeze the header row and the first identifier columns (código / descripción).
   - Mark edited or "draft" cells distinctly (NN/g edit-mode distinction).
   - Prefer a side panel for detailed APU editing.
2. **Findings list (hallazgos)**
   - One row per finding with a severity shape-and-label column (Alta/Media/Baja → red/orange-or-yellow/blue). Use purple for price outliers (alertas de precio).
   - Sort by severity by default, and roll up the highest severity to the budget header.
   - Use batch actions ("marcar revisado") via checkboxes.
3. **Two-currency variance**
   - Show the primary currency large and the secondary currency smaller and muted on the line below, both right-aligned.
   - The delta uses sign plus arrow plus value (Carbon differential), colored by favourable/unfavourable, never color alone.
   - In tables, use separate columns per currency (USD | Bs.) so decimal points align, and show the exchange rate and its date (BCV) in the caption (GOV.UK `<caption>`).
4. **KPI tiles**
   - Label, value, budget/target, and deviation (Fiori analytical-card anatomy).
   - Use a bullet bar instead of a gauge (NN/g).
   - No icons on KPI tiles (Fiori).
5. **Number formatting**: es-VE decimal comma and period grouping, with `useGrouping: 'always'` (or the Python/Babel equivalent) so that 4-digit amounts are grouped and columns stay aligned.
6. **Empty and error states** following Carbon's three types, in Spanish, with a recovery action.

### Gaps
- No sourced guidance was found on **print/export views** (print stylesheets, PDF export of tables, repeating table headers on printed pages) from any of the design systems consulted. This remains open.
- No design-system guidance was found specifically on **sticky/frozen columns** (Carbon's usage page omits it); NN/g is the only source.
- Venezuelan currency symbol conventions (e.g. CLDR symbol for VES, "Bs." vs "Bs.S" vs "Bs.D") were not verified.
- Whether Python-side formatting (Babel, used by many Streamlit apps) applies the same Spanish minimum-grouping rule was not verified.
