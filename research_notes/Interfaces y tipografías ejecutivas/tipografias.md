# Executive typefaces for Sílice (data-dense financial / construction-budget UI + Excel exports)

Scope note: research done 2026-10-13 with ~20 tool calls. Primary sources were foundry/repo pages and Microsoft Learn. A local binary check of the fonts installed on the development machine (Windows 11, `C:\Windows\Fonts` and the Office cloud-font cache) was run with a small pure-Python OpenType parser (no fontTools). It read the OS/2 fsType, the x-height and the advance width of the digits 0-9. Those results are labelled "[local check]". They are first-hand measurements, not web citations.

## 1. Candidate typefaces: license, variable availability, finance features, Spanish coverage, weights, users

### Takeaway
Every open-source candidate (Inter, IBM Plex, Source Sans 3, Public Sans, Geist, Roboto Flex, Figtree, and by extension Manrope, DM Sans, Work Sans, Noto Sans, Open Sans and Lato) is under SIL OFL 1.1. That allows bundling in a proprietary Windows installer. **Segoe UI and Aptos must NOT be bundled.** They are licensed only as installed system or Office fonts, and Microsoft explicitly forbids copying them to servers, converting them to WOFF/WOFF2 or embedding them in apps. Inter is the best-documented fit for finance features: its specimen lists `tnum`, `zero`, `case`, `frac` and disambiguation sets, it covers weights 100-900 and has an optical-size axis. IBM Plex Sans + Plex Mono is the strongest "corporate/engineered" alternative with a ready-made mono partner.

### Cited Findings

**Inter (rsms)**
- License: "free and open source", SIL Open Font License 1.1. "Inter" is a Reserved Font Name. It can be used commercially, but Inter itself and its derivatives may not be sold. — [rsms.me/inter](https://rsms.me/inter/); [github.com/rsms/inter](https://github.com/rsms/inter)
- Weights: Thin 100 to Black 900, nine named weights with matching italics. "Each glyph has three dedicated designs for weights 100, 400 and 900" (variable interpolation masters). — [rsms.me/inter](https://rsms.me/inter/)
- Optical size: "Optical size ranges from 'text' to 'display'". The CSS sample uses the family name `InterVariable`. — [rsms.me/inter](https://rsms.me/inter/)
- The GitHub README mentions a "Display subfamily" (for very large sizes) and links a `display-beta-1` tag. The README text fetched is older than the specimen page, so the two pages are inconsistent about whether Display is finished. — [github.com/rsms/inter](https://github.com/rsms/inter)
- OpenType features listed on the specimen that matter for finance: `tnum` (tabular numbers), `zero` (slashed zero), `frac`, `numr`/`dnom`, `sups`/`subs`/`sinf`, `case` (case alternates: punctuation re-centred for all-caps and figures), `ss01` ("open digits"), `ss02`/`ss04` (disambiguation, e.g. I/l/1), `pnum`, `cv01`–`cv13`, `calt`, `locl`, `ordn`. — [rsms.me/inter](https://rsms.me/inter/)
- Coverage: "over 2000 glyphs" and "147 languages", so Spanish (ñ á ¿ ¡ « ») is well inside the set. — [rsms.me/inter](https://rsms.me/inter/)
- Users listed in the README: ElementaryOS, **Figma**, **GitLab**, Unity, Guggenheim museums, ISO, Mozilla, NASA, Pixar Presto, Canton of Zurich, Zurich Airport. — [github.com/rsms/inter](https://github.com/rsms/inter). The specimen describes uses "from computer interfaces, advertising & airports, to NASA instrumentation & medical equipment". — [rsms.me/inter](https://rsms.me/inter/)
- Linear: the only sources found are third-party "Linear UI skills" packages. They say a Linear-style UI uses Inter, `tabular-nums` for numeric data and a reduced weight count. These are not Linear's own docs, so treat them as unverified. — [skills.sh linear-ui-skills](https://skills.sh/ihlamury/design-skills/linear-ui-skills)

**IBM Plex (Sans, Mono, Serif, Sans Condensed, Math + script companions)**
- License OFL-1.1. Families: Sans, Serif, Mono and Sans Condensed, "all with Roman and true italics". Plex Sans supports extended Latin plus Arabic, Chinese, Cyrillic, Devanagari, Greek, Hebrew, Japanese, Korean and Thai. — [github.com/IBM/plex](https://github.com/IBM/plex)
- Distributed as npm packages: `@ibm/plex-sans`, `@ibm/plex-mono`, `@ibm/plex-sans-condensed`, `@ibm/plex-serif`, etc. These are convenient for offline bundling because no CDN is needed. — [github.com/IBM/plex](https://github.com/IBM/plex)
- Weight selector on ibm.com/plex: Thin, Extra Light, Light, Regular (Text), Medium, Semi Bold, Bold. — [ibm.com/plex](https://www.ibm.com/plex/)
- Design traits: slab-serif-derived details, "the vertical stroke and right angle of the interior counters" against rounded outer curves. — [ibm.com/plex](https://www.ibm.com/plex/)

**Source Sans 3 (Adobe)**
- OFL-1.1. Described as "a set of OpenType fonts designed for user interface environments". Ships OTF, TTF, WOFF and WOFF2 folders and a `VF` (variable) folder plus `source-sans-3VF.css`. The fetched page did not list its OpenType features. — [github.com/adobe-fonts/source-sans](https://github.com/adobe-fonts/source-sans)

**Public Sans (USWDS)**
- OFL-1.1. A fork of Libre Franklin with adjusted vertical metrics and a tailed lowercase "l". The repo highlights **tabular figures** for data design. Variable files are in `fonts/variable` and "should be considered experimental". The README says "Public Sans is a Latin-only font". The repo now says the font is "not currently being actively developed or maintained" (v2.001). This maintenance risk is a mark against it. — [github.com/uswds/public-sans](https://github.com/uswds/public-sans)

**Geist / Geist Mono (Vercel)**
- "Licensed under OFL." The specimen lists nine weights, from Thin to Ultra Black, and offers variable files in the zip. Install with `npm i geist`. — [vercel.com/font](https://vercel.com/font)
- Feature caveat: Vercel's comparison table says the npm and zip builds include "full glyph set and font-feature-settings support", while the **Google Fonts build does not**. Bundle from npm or zip, not from Google Fonts. — [vercel.com/font](https://vercel.com/font) (as summarised in search results; also [vercel.com/font/mono](https://vercel.com/font/mono))
- Versions: Homebrew lists Geist Mono cask 1.4.2 and the Arch AUR package for the family is 1.8.0. A guide says v1.7.0 moved coding ligatures from `calt` to `ss11`. Version numbering differs between packagers. — [formulae.brew.sh](https://formulae.brew.sh/cask/font-geist-mono); [AUR ttf-geist](https://aur.archlinux.org/packages/ttf-geist)

**Roboto Flex (Google Fonts)**
- Fonts are under OFL 1.1, scripts under Apache 2.0. Axes: wght, wdth, opsz, slnt, GRAD, XOPQ, XTRA, YOPQ, YTAS, YTDE, YTFI, YTLC, YTUC. The repo says it is "not an official Google project, and Google provides no support for it". — [github.com/googlefonts/roboto-flex](https://github.com/googlefonts/roboto-flex)

**Figtree**
- OFL-1.1 (OFL.txt in repo). The repo landing page did not state its weights, variable status or features. — [github.com/erikdkennedy/figtree](https://github.com/erikdkennedy/figtree)

**Lato, Open Sans, DM Sans (tabular figures)**
- Lato's OpenType feature list includes `tnum`. — [Fedora Project Wiki: Lato fonts](https://fedoraproject.org/wiki/Lato_fonts)
- The Open Sans CTAN documentation lists `tnum` ("Tabular Figures, Numbers=Monospaced"). — [CTAN opensans.pdf](https://ctan.csail.mit.edu/fonts/opensans/doc/opensans.pdf)
- DM Sans is described as having tabular figures among its OpenType features (secondary source). — [befonts DM Sans](https://befonts.com/dm-sans-font-family.html)

**Segoe UI (Windows system font): NOT bundleable**
- Microsoft's redistribution FAQ: "Apart from the document embedding rights ... you may not redistribute the Windows fonts. You may not copy them to other computers or servers, and you may not convert them to other formats". On the web, you have no rights to "copy fonts from a Windows installation to a web server" (self-hosting) or to "convert the font to ... WOFF or WOFF2". — [Microsoft Learn: Font redistribution FAQ](https://learn.microsoft.com/en-us/typography/fonts/font-faq)
- **Referencing** a Windows font by name in a CSS font stack is allowed, "as the 'use' of the font occurs on the Windows device". — [Font redistribution FAQ](https://learn.microsoft.com/en-us/typography/fonts/font-faq)
- On embedding in apps: "Can I embed the fonts into a game, application or device ...? No". Extended rights can be bought from Monotype. "Segoe UI Variable is not available for licensing or use outside of Microsoft products or on non-Windows platforms." — [Font redistribution FAQ](https://learn.microsoft.com/en-us/typography/fonts/font-faq)
- Microsoft's open-source Segoe UI look-alike, **Selawik**, is OFL. — [Font Squirrel: Selawik](https://www.fontsquirrel.com/fonts/selawik)

**Aptos (Microsoft 365 default): NOT bundleable**
- Designed by Steve Matteson "as a new default Office font to replace Calibri". It has six weights (Light to Black) with redrawn obliques, plus Display, Narrow/Condensed, Mono and Serif variants. Code pages include 1252 Latin 1. — [Microsoft Learn: Aptos](https://learn.microsoft.com/en-us/typography/font-list/aptos)
- Microsoft's rationale: "clear-cut stroke endings emphasize order and restraint ... reduces visual crowding". It also says "the Condensed weights give Excel users a way to fit more information into spreadsheets and tables". — [Microsoft Learn: Aptos](https://learn.microsoft.com/en-us/typography/font-list/aptos)
- Licensing: © 2023 Microsoft. The page points to the redistribution FAQ and to Monotype for "hardware & software redistribution". Aptos is supplied as an Office **cloud font**. — [Microsoft Learn: Aptos](https://learn.microsoft.com/en-us/typography/font-list/aptos). A third-party summary says you may not "export, distribute or sell the individual font files". — [Office Watch](https://office-watch.com/2023/aptos-microsoft-fonts-legally-do/)
- [local check] On this Windows 11 machine, Aptos, Aptos Display and Aptos Narrow are present only in `%LOCALAPPDATA%\Microsoft\FontCache\4\CloudFonts`. They are not in `C:\Windows\Fonts`. This confirms they arrive through Office's on-demand download and are not guaranteed on every client.

**[local check] Metrics of system fonts on this machine (OS/2 table, units per em 2048)**

| Font | fsType | x-height / em | Digits 0-9 advance | ñ ¿ ¡ « » € present |
|---|---|---|---|---|
| Arial (arial.ttf) | 0x0008 (editable embedding) | 0.519 | all 1139 (tabular by default) | yes |
| Segoe UI (segoeui.ttf) | 0x0008 | 0.500 | all 1104 (tabular by default) | yes |
| Calibri (calibri.ttf) | 0x0008 | 0.464 | all 1038 (tabular by default) | yes |
| Aptos (cloud cache, first file) | 0x0008 | 0.477 | all 1094 (tabular by default) | yes |

fsType 0x0008 = "editable embedding", which permits embedding in documents only, not in apps. — [Font redistribution FAQ](https://learn.microsoft.com/en-us/typography/fonts/font-faq)

### Inferences
- License shortlist for a proprietary installer: every OFL candidate passes. Under OFL the font files may be bundled with commercial software provided they are not sold on their own and the OFL text plus copyright are shipped. Reserved Font Names (e.g., "Inter") mean a subsetted or modified build should arguably be renamed. Many projects nonetheless ship unmodified WOFF2 conversions. Verify this against the OFL FAQ before subsetting (see Gaps).
- For a Spanish finance UI the decisive features are `tnum`, `zero` (to tell 0 from O in codes like "UI-01-TUB"), `case`, and disambiguation of 1/l/I. Inter documents all of these explicitly. Plex Mono and Geist Mono give disambiguation for free by being monospaced.
- Public Sans is not maintained and Roboto Flex is officially unsupported, so neither is a good long-term default for a thesis product. Geist is fine but tied to Vercel's packaging (avoid the Google Fonts build).
- Because Arial's digits are tabular by default, the Excel side already has aligned columns without any OpenType switch.

### Gaps
- No primary-source confirmation was retrieved of `tnum`/`zero` for Source Sans 3, Manrope, Figtree, Work Sans, Noto Sans, Geist Sans or Geist Mono. Check them with `fc-query`/fontTools on the downloaded files or on Wakamai Fondue before committing.
- Exact variable-font file sizes (WOFF2) were not found on official pages. From prior knowledge only (unverified): InterVariable.woff2 is about 300-350 KB for the full glyph set, and a Latin subset is much smaller. Measure after download.
- Inter's current version number and the Inter 4.0 changelog (opsz axis, Inter Display) were not confirmed from the fetched pages, though the specimen confirms the text-to-display optical-size range.
- IBM Plex Sans Variable: whether a variable Plex Sans is now published was not confirmed (the GitHub page did not mention it).
- Who uses which font in finance products (e.g., Stripe, Bloomberg, banks): no primary sources found.
- x-heights for the OFL candidates were not measured (no font files downloaded). From prior knowledge, Inter has a notably tall x-height, but this is unverified here.

## 2. Evidence on legibility of numbers and dense tables; design-system rationales

### Takeaway
No peer-reviewed study comparing these specific fonts for numeric tables was found. The evidence is design-system rationale and foundry claims. Microsoft justifies Aptos by order, restraint, reduced crowding and Narrow weights for Excel density. IBM's Carbon system pairs Plex with a "productive" dense type scale based on 12 px. Inter is documented as a UI-first family with explicit numeric features and wide product adoption (Figma, GitLab).

### Cited Findings
- Carbon (IBM): Plex was "carefully designed to meet IBM's needs as a global technology company". For digital experiences Carbon recommends "IBM Plex Light, Regular, and SemiBold". SemiBold is "ideal for section headers, but should not be used for long text". Italics are reserved for emphasis. — [Carbon: Typography overview](https://carbondesignsystem.com/elements/typography/overview/)
- Carbon splits the type into a **productive** scale (suffix `-01`, "primarily used within product spaces", fixed headings) and an **expressive** scale (suffix `-02`, editorial/marketing, responsive headings). Sizes come from a formula with base y₀ = 12 px. The productive scale is the model for dense dashboards. — [Carbon: Typography overview](https://carbondesignsystem.com/elements/typography/overview/)
- Microsoft (Aptos): "the points where curved strokes meet straight strokes are crisp and well defined, which makes the typeface easily readable and reduces visual crowding". Matteson: "the austerity and directness that is required in huge variety of Office documents". Condensed weights let "Excel users ... fit more information into spreadsheets and tables". — [Microsoft Learn: Aptos](https://learn.microsoft.com/en-us/typography/font-list/aptos)
- Inter's specimen positions the family for "computer interfaces" and for instrumentation and medical equipment, which are dense numeric contexts. — [rsms.me/inter](https://rsms.me/inter/)
- Tabular numerals are toggled in CSS with `font-variant-numeric: tabular-nums` (equivalent to `font-feature-settings: "tnum"`). Use only one of the two. — [wiert.me](https://wiert.me/?p=194589); Flutter exposes the same feature as `FontFeature.tabularFigures()`. — [api.flutter.dev](https://api.flutter.dev/flutter/dart-ui/FontFeature/FontFeature.tabularFigures.html)

### Inferences
- For a defensible thesis rationale, cite the design-system arguments (Carbon's productive scale, Aptos's anti-crowding and condensed-for-Excel arguments) rather than claiming a font is "proven" more legible.
- The functional requirements to state are: tabular figures in every amount column, a slashed or dotted zero in codes, distinct 1/l/I, and a large enough x-height at 12-14 px. Inter meets these by documentation. Plex meets them via Plex Mono for codes.

### Gaps
- No empirical legibility study (e.g., reading-speed or error-rate tests of numerals in tables for Inter vs Plex vs Arial) was located within the call budget.
- Fluent 2 and Atlassian typography docs were not fetched. Microsoft's FAQ confirms Fluent's Segoe UI Variable cannot be used outside Microsoft products. Atlassian's current UI font (reportedly a custom "Atlassian Sans" in 2024-2025) is unverified.
- GitHub's typeface is not Inter in its current Primer system (GitHub has its own Mona Sans/Hubot Sans, from prior knowledge, unverified). The premise "GitHub uses Inter" should not be stated without a source.
- Butterick's *Practical Typography* was not fetched.

## 3. Pairings for executive dashboards and how many weights to ship

### Takeaway
Use one UI sans with tabular figures for everything, plus at most one monospaced companion reserved for codes and IDs (item codes, audit-finding IDs), never for prose. Ship 3-4 weights, or a single variable file. Carbon's guidance (Light/Regular/SemiBold, SemiBold for headers only) and the "reduce weight count" convention in Linear-style systems support a small set.

### Cited Findings
- Carbon recommends three weights for product UI: Light, Regular and SemiBold, with SemiBold only for headers. — [Carbon: Typography overview](https://carbondesignsystem.com/elements/typography/overview/)
- IBM Plex is designed as a superfamily: Sans + Mono + Serif + Sans Condensed share the design. — [github.com/IBM/plex](https://github.com/IBM/plex)
- Geist is designed as a Sans + Mono pair. The npm and zip builds keep `font-feature-settings` support. — [vercel.com/font](https://vercel.com/font)
- Aptos itself ships a Mono and a Narrow sibling, which shows Microsoft's own view that office and finance documents need a condensed style and a mono style. Aptos cannot be bundled, though. — [Microsoft Learn: Aptos](https://learn.microsoft.com/en-us/typography/font-list/aptos)
- Third-party Linear-style guidance: one family throughout, `tabular-nums` on numeric data, fewer weights. — [skills.sh linear-ui-skills](https://skills.sh/ihlamury/design-skills/linear-ui-skills)
- A single variable font "can be used as a replacement for multiple font files", but variable fonts "typically have larger file sizes" than a single static style. — [web.dev: font best practices](https://web.dev/articles/font-best-practices)

### Inferences (candidate pairings for Sílice)
- **Option A (recommended): Inter (variable, roman + optionally italic) alone**, with `tnum` on all numeric cells and `zero` for code columns. Inter's optical size covers KPI hero numbers without a separate display font. Add **JetBrains Mono or IBM Plex Mono** only if code columns need mono. Neither mono font was researched here beyond Plex's OFL license.
- **Option B (corporate/engineered look): IBM Plex Sans + IBM Plex Mono** (+ optional Plex Sans Condensed for wide tables). Ship Regular 400, Medium 500 and SemiBold 600, plus Mono Regular. This choice is backed directly by Carbon's documentation.
- **Option C: Geist + Geist Mono**, if a more contemporary or technical tone is wanted. Bundle from npm or zip.
- Weight budget: 400 (body/table), 500 (labels/column headers), 600 (section headers/totals). 700 is optional for grand totals. With static files that is 3-4 WOFF2 files; with a variable file it is one file per style.

### Gaps
- No primary source compared mono companions (JetBrains Mono, Plex Mono, Geist Mono, Roboto Mono) for numeric legibility.
- No sourced recommendation for using a serif heading companion in finance dashboards was found. The default inference is not to add one.

## 4. Practical: offline bundling in the web app, and Arial vs UI font in Excel exports

### Takeaway
Self-host WOFF2 files inside the app package via `@font-face` with `font-display: swap` (or `optional` for body text). Subset to Latin plus Latin-1 Supplement plus the punctuation and currency symbols Sílice needs (ñ á é í ó ú ü ¿ ¡ « » € $ Bs.). Use a fallback stack ending in `"Segoe UI", Arial, sans-serif`, which is legal because it only references installed fonts. **Keep Arial in the Excel exports.** An `.xlsx` only stores the font name, and a client without Inter or Plex installed will substitute another font. Arial is on every Windows machine, matches the company template, and already has tabular digits.

### Cited Findings
- WOFF2 "compresses 30% better than WOFF". Bram Stein (2022 Web Almanac): "Use only WOFF2 and forget about everything else." — [web.dev: font best practices](https://web.dev/articles/font-best-practices)
- Self-hosting performance gains depend on CDN/HTTP2. When self-hosting, apply subsetting and WOFF2 yourself. "Always check the font licenses to confirm they allow subsetting". — [web.dev](https://web.dev/articles/font-best-practices)
- `unicode-range` "informs the browser which characters a font can be used for", and "a font file is downloaded if the page contains one or more characters matching the unicode range". Removing unused glyphs "can significantly reduce the filesize". — [web.dev](https://web.dev/articles/font-best-practices)
- `font-display: swap` "delays text render the least" but can cause layout shift. With `optional`, render "is delayed for no longer than 100ms" but the font may not be used if late. `fallback` has a 100 ms block and a 3 s swap period. The article suggests swap for branding and optional for body text. — [web.dev](https://web.dev/articles/font-best-practices)
- Preload "ignores unicode-range declarations" and "should only be used to load a single font format". Use `size-adjust` descriptors on the fallback face to reduce layout shift. — [web.dev](https://web.dev/articles/font-best-practices)
- Microsoft: listing Windows fonts in a CSS font stack is allowed, but self-hosting them or converting them to WOFF/WOFF2 is not. — [Font redistribution FAQ](https://learn.microsoft.com/en-us/typography/fonts/font-faq)
- Excel font substitution: ClosedXML falls back to Microsoft Sans Serif when a cell's font is missing ("It is responsibility of developer to ensure that required font/s are present"). — [ClosedXML docs: missing font](https://github.com/ClosedXML/ClosedXML/blob/0.100.0/docs/tips/missing-font.rst). Aspose.Cells checks the workbook's default font, then searches installed fonts for glyph coverage. — [Aspose docs](https://docs.aspose.com/cells/python-net/set-defaultfont-property-of-pdfsaveoptions-and-imageorprintoptions-to-have-priority). Excel itself "won't show you what font it is using to display the text on the screen. It will happily tell you it is 'Calibri' even when we know it isn't." — [TMS FlexCel docs](https://doc.tmssoftware.com/flexcel/net/tips/finding-the-actual-fonts-used-when-exporting-to-pdf.html)
- Document font embedding is a separate right from app embedding and is allowed only where the format and application follow the OpenType fsType rules. Word and PowerPoint do; the FAQ does not mention Excel. — [Font redistribution FAQ](https://learn.microsoft.com/en-us/typography/fonts/font-faq)
- [local check] Arial: x-height 0.519 em (the tallest of the system fonts checked) and every digit 0-9 has the same advance width (1139/2048). Totals align in Excel columns without any feature switch. fsType 0x0008.

### Inferences
- Packaging pattern for the offline installer: put `fonts/Inter-roman.var.subset.woff2` (and the italic, if used) in the app's static folder, declared with `@font-face { font-family: "Inter"; src: url(...) format("woff2"); font-weight: 100 900; font-display: swap; unicode-range: U+0000-00FF, U+2013-2014, U+2018-201E, U+20AC, ... }`. Add a metric-adjusted fallback face over local Arial/Segoe UI with `size-adjust`. Ship the OFL.txt next to the fonts and list it in the installer's third-party notices. The app runs offline, so no CDN is involved and preloading is optional.
- Apply `font-variant-numeric: tabular-nums` to amount, quantity, unit-price and KPI cells, and `slashed-zero` (or `font-feature-settings: "zero"`) to code/ID columns.
- Excel export: keep Arial, as the company template does. Reasons: (a) openpyxl and xlsx only record the font name, so Inter would silently fall back on clients without it; (b) Excel does not reliably embed fonts in workbooks (Microsoft's FAQ names Word and PowerPoint as compliant embedders, not Excel); (c) Arial is universally installed and has tabular digits. If brand continuity is wanted, pick a UI font whose proportions sit close to Arial's (neo-grotesque: Inter, Public Sans), so screen and spreadsheet feel related. Do not use Aptos in exports either: it is a cloud font, absent until Office downloads it, and absent on machines without Microsoft 365.

### Gaps
- Whether Excel for Windows embeds TrueType fonts in .xlsx at all (Word has "Embed fonts in the file"; Excel has no equivalent option, per prior knowledge, unverified) was not confirmed from a Microsoft source.
- Exact openpyxl behaviour (writes `<font><name val="..."/>` only) is inferred from the file format, not cited.
- The OFL FAQ was not fetched. Its position on whether subsetting or converting to WOFF2 counts as a "Modified Version" that must drop the Reserved Font Name ("Inter") should be checked at scripts.sil.org/OFL-FAQ before shipping subset files under the original name.
