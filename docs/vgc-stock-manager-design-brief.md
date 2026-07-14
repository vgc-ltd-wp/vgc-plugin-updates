# Design Brief — VGC Stock Manager (workshop inventory & production PWA)

**For:** Claude Design
**Deliverable:** an improved, functional visual + interaction design for an existing, working app
**Status:** the app is fully built and in daily testing. This is a **redesign of an existing UI**, not a greenfield concept. Everything proposed must be implementable against the current architecture (see *Hard constraints*).

---

## 1. What the product is

A **standalone workshop inventory and production system** for a small manufacturer (candles, gift sets and similar handmade goods).

It runs as a **WordPress plugin on a dedicated backoffice site** (`backoffice.<domain>`), where **the app *is* the whole site** — served at the site root, no theme, no wp-admin. It pushes finished-goods stock to a separate WooCommerce shop.

It is **not** a shop, not a CMS, and has no public pages. It is an internal tool.

### The core domain model (important — the UI is a direct expression of this)

- **One unified "item" model.** There is no hard line between "material" and "product". An item is `raw` (bought) or `manufactured` (made from a recipe). A **Base Candle** is simultaneously a sellable product, a component of a "Silna Stilna" candle, and a component of a Gift Box.
- **Recipes (Bill of Materials) nest arbitrarily.** Gift Box → Base Candle + Base Mug (each of which has its own recipe) → raw materials.
- **Production is batch-based.** A recipe has a **yield** ("1 run makes 24"). You produce in **runs**, not individual units.
- **Recipe quantities have a basis:** each component is entered **per item** (1 wick per candle) or **per batch** (a fixed amount per run).
- **Units convert.** Weight (mg/g/dag/kg) and volume (ml/cl/dl/l) convert automatically — wax stocked in **kg**, recipe calls for **g**.
- **Packaging.** Materials arrive in packs (1 carton = 22.5 kg). You receive in packs and track unopened packs.
- **Costing.** Raw items have an entered net cost + VAT rate (default 20%, currency default €). Manufactured items' cost is **calculated** by rolling the recipe up recursively, plus **non-material costs** (labour, overhead) per item or per batch.
- **Append-only ledger.** Every stock change is a movement (receive / consume / produce / ship / scrap / correct). Stock = sum of movements.
- **Scrap.** Write off stock with a reason, including defective units as part of a production run (net good quantity is what reaches the shop).
- **Categories.** User-defined, assigned to any item.
- **Images.** Each item can have a photo (camera upload).

---

## 2. Who uses it, and where

Two modes, same app, same login:

| Context | Device | Reality of use |
|---|---|---|
| **On the bench / in the workshop** | Android phone, installed as a PWA | One hand. Possibly wax-covered or gloved fingers. Standing. Glancing, not reading. Doing: scan a barcode, receive a delivery, run a batch, scrap a broken jar. Wi-Fi is flaky — **writes are queued offline**. |
| **Planning / admin** | Laptop browser | Sitting. Doing: build recipes, set costs, import a supplier list, read reports, reconcile shop stock. Wants density and overview. |

There are **two roles**: an **administrator** (everything, incl. shop connection settings) and a **Stock Operator** (a custom WP role with app access but *zero* wp-admin rights).

**The single most important contextual fact:** the phone experience must survive a workshop — big targets, high contrast, minimal precision, readable at arm's length. The laptop experience must not be a stretched phone.

---

## 3. Current information architecture

**Bottom tab bar (mobile):** Home · Items · Produce · Reports · Scan
**Top bar:** app title · current user · Sign out

### Screens (hash routes)

| Route | Screen | Contents today |
|---|---|---|
| `/` | **Home / Overview** | Quick actions (Scan, Produce, New item); "Low materials" list; "Low products" list; links to Shop stock and Shop settings |
| `/items` | **Items** | Search; category filter; kind chips (All / Materials / Products / Low); import button; add button. Rows: thumbnail, name, `SKU · kind · category · unit cost`, stock qty |
| `/item/:id` | **Item detail** | Hero photo; big "In stock" figure; meta line (SKU, kind, category, sellable, reorder level); pack breakdown ("2 cartons + 17.5 kg loose"); unit cost (net / incl. VAT, "calculated" pill); "can assemble now"; action row (Receive, Set qty, Scrap, Edit, Recipe, Produce); an **inline form** that appears for the chosen action; recent movements list |
| `/item/new`, `/item/:id/edit` | **Item form** | ~14 fields: photo, name, SKU (+ Generate), type, unit (dropdown + add-new), category (dropdown + add-new), reorder level, sellable, shop SKU, supplier, barcode (+ Scan), **Packaging** (pack label, units per pack), **Pricing** (VAT %, unit cost net, unit cost incl. VAT, cost per pack — all live-linked) |
| `/recipe/:id` | **Recipe editor** | Product hero photo; yield ("1 run yields N"); **Components** — each: thumbnail, name/SKU, quantity, unit (dropdown, restricted to compatible units), basis (per item / per batch), and its **cost per item**; component search-to-add; **Other costs** (label, amount, per item/per batch); running **"Recipe unit cost"** total |
| `/produce` | **Produce** | Search a product → shows "1 run = 24 pcs"; number of **runs** input with live "→ produces 48 pcs"; **Check** → **Consumes** list (each: name, cost, `180 g → 0.18 kg` conversion, shortage flag); **build plan** when short ("make 6 base mugs, then assemble"); **cost card** (Total, split materials / other, per-unit); optional **Scrap from this run** (qty + reason, live "net good"); Run button |
| `/scan` | **Scan** | Live camera barcode (native BarcodeDetector), manual entry fallback |
| `/reports` | **Reports** | **Produced** (period chips 7/30/90/365, totals, run list, CSV export); **Scrapped** (write-offs + reasons); **Stock on hand** (total value, materials vs products split, item list, CSV export) |
| `/import` | **Import** | Paste CSV or pick file; downloadable template; parsed preview; import; result summary (created/updated/errors) |
| `/categories` | **Categories** | Add / rename / delete |
| `/shop` | **Shop stock** | Sellable items: local qty vs shop qty, low-on-shop flags, total stock value, "set shop = local" reconcile |
| `/settings` | **Shop settings** (admin) | Bridge URL, shared token, auto-push toggle, currency symbol, Test connection |
| — | **Login** | Standalone branded login (site name, username, password, keep me signed in) |

---

## 4. Hard constraints (the design must live inside these)

These are non-negotiable; a design that ignores them can't be shipped.

1. **No framework, no build step.** The app is **vanilla JS**, rendered by string concatenation into `innerHTML`, hash-routed. There is no React, no Tailwind, no bundler, no preprocessor.
2. **One stylesheet:** `app/app.css`, plain CSS with **custom properties**. Light and dark via `prefers-color-scheme`.
3. **Everything must be self-hosted.** No CDNs, no Google Fonts, no external icon libraries — the app must work **offline** as an installed PWA. System font stack today. Any icons must be **inline SVG** (or an inlined sprite).
4. **Mobile-first, but genuinely responsive.** Currently the main column is capped at `44rem`, so the laptop view is a narrow phone column in the middle of a wide screen — **this is a key thing to fix**.
5. **Touch targets ≥ 44px.** Workshop use.
6. **Offline/queued states are real** and must be expressible: a write can be "queued", and a badge shows the pending count.
7. The design should be deliverable primarily as **CSS + a defined set of markup changes**, because implementation means editing `app.css` and the HTML strings inside `app.js`.

### Existing CSS class inventory (please map your design onto these where possible)

```
Layout/shell : .vgc-sm-topbar .vgc-sm-main .vgc-sm-nav .vgc-sm-tab .vgc-sm-toast .vgc-sm-qbadge
Structure    : .vgc-sm-card .vgc-sm-h1 .vgc-sm-subhead .vgc-sm-meta .vgc-sm-muted .vgc-sm-back
Data         : .vgc-sm-list .vgc-sm-qty (.is-low/.is-pos/.is-neg) .vgc-sm-stat .vgc-sm-pill
Controls     : .vgc-sm-btn (.vgc-sm-btn--primary) .vgc-sm-input (.vgc-sm-input--sm)
               .vgc-sm-chip .vgc-sm-chips .vgc-sm-field .vgc-sm-inline .vgc-sm-toolbar
Composites   : .vgc-sm-row (recipe) .vgc-sm-crow (stacked component row) .vgc-sm-result
               .vgc-sm-results .vgc-sm-steps .vgc-sm-scan .vgc-sm-x
Media        : .vgc-sm-thumb (.vgc-sm-thumb--lg) .vgc-sm-hero .vgc-sm-imgrow
States       : .vgc-sm-loading .vgc-sm-error .vgc-sm-ok .vgc-sm-placeholder
Auth         : .vgc-sm-auth .vgc-sm-auth__card ...
```

---

## 5. What's wrong today (the problems to solve)

Ranked by pain:

1. **The laptop experience is wasted.** A 44rem column on a 1440px screen. Reports, the item list, the recipe editor and the shop view all want **tables, multi-column layouts, or master–detail**. This is the biggest single win.
2. **Feature creep has crowded the screens.** The item form is now ~14 fields in one flat stack (identity, classification, stock, packaging, pricing). The item detail packs stock + packs + cost + VAT + buildable + 6 action buttons into one card. Both need **grouping, hierarchy and progressive disclosure**.
3. **The recipe editor is the most complex screen** and is presented as flat stacked rows. Each component carries name, photo, quantity, unit, basis, cost — plus there's yield, other costs, and a running total. It needs a **real structure** (the total is the payoff and should feel like it).
4. **Icons are Unicode glyphs** (`▤ ❏ ⚙ ▦ ❒ ＋ ✕ ⤓`). They render inconsistently and look unfinished. Needs a **proper inline SVG icon set** (~20 icons).
5. **Numbers are the content, and they're not designed.** Quantities, units, costs, conversions ("180 g → 0.18 kg"), shortages, VAT — there's no consistent numeric/tabular treatment or clear hierarchy between *what you have*, *what you need*, and *what it costs*.
6. **Weak states.** Loading is a bare "Loading…", empty states are a muted sentence, errors are red text. Offline/queued is a small badge. These deserve real design.
7. **The Produce flow is a long scroll** (pick → runs → check → consumes → plan → cost → scrap → run). It's a genuine multi-step task and should feel like one — with a confident final confirmation.
8. **No visual identity.** Currently neutral grey/dark. It's a workshop tool for a candle maker — it can have warmth and character without becoming decorative.
9. **Accessibility hasn't been designed**: focus states, contrast in both themes, form labelling, screen-reader semantics.

---

## 6. Goals

- **Glanceability on the phone.** From arm's length, standing at a bench: what's low, what can I make, did that save.
- **Density and control on the laptop.** Real tables, sortable overviews, side-by-side editing.
- **Make the numbers legible.** Stock, need, shortage, cost — a clear, consistent numeric language.
- **Tame complexity.** The recipe editor and item form must feel calm despite carrying a lot.
- **Trustworthy.** This app changes stock and pushes to a live shop. Destructive/consequential actions (Run production, Scrap, "set shop = local") must feel deliberate and clearly reversible-or-not.
- **Fast.** No heavy assets. It must stay instant on a mid-range Android over workshop Wi-Fi.

---

## 7. What we want back

1. **Design tokens** — colour (light + dark), type scale, spacing, radii, borders, elevation, motion. Expressed as **CSS custom properties**, ideally a drop-in replacement for the `:root` block.
2. **Component specs** mapped to the existing class names above (and any new ones), with all states: default, hover, focus-visible, active, disabled, loading, error, low/short, queued/offline.
3. **An inline SVG icon set** (~20): scan/barcode, items/box, produce/gear, reports/chart, home, search, add, remove, edit, camera, receive/download, scrap/trash, shop, settings, sync, warning, check, chevron, filter, export.
4. **Responsive strategy** — breakpoints, and what changes at each. Specifically: **what the laptop layout becomes** (bottom tabs → sidebar? lists → tables? item detail → master-detail?).
5. **Key screen designs**, mobile **and** desktop, for at minimum:
   - Home / Overview
   - Items (list → table on desktop)
   - Item detail
   - Item form (grouped)
   - **Recipe editor** (the hard one)
   - **Produce** (the flow)
   - Reports
   - Login
6. **State designs:** empty, loading (skeletons?), error, offline/queued, success.
7. **Accessibility notes:** contrast ratios, focus treatment, target sizes, semantics.
8. **An implementation note** per change: "this is CSS only" vs "this needs markup change X in `app.js`". Please be explicit — it directly drives how we ship it.

## 8. Brand

There's no defined brand for the backoffice yet. The business is a **handmade candle / gift workshop**. Warmth (wax, amber, flame) is available as a direction, but this is a **tool**, so it must stay quiet, high-contrast and functional — not decorative. If you want to propose a small palette + one accent, do; keep it working in both light and dark, and keep semantic colours (low stock = danger, produced = positive) distinct from brand colour.

## 9. Out of scope

- Marketing/public pages (there are none).
- Changing the domain model or the flows themselves — **this is a design pass, not a re-architecture**. If a flow is genuinely wrong, say so, but don't assume you can move data around.
- Anything requiring a JS framework, build step, or external asset.

---

## Appendix — glossary

- **Run / batch** — one execution of a recipe; produces `yield` units.
- **Yield** — how many units one run makes (e.g. 24).
- **Basis** — whether a recipe quantity is *per item* or *per batch*.
- **Pack** — how a material arrives (1 carton = 22.5 kg).
- **Net / gross** — cost excluding / including VAT (default 20%; currency default €).
- **Bridge** — the companion plugin on the WooCommerce shop that the app pushes stock to.
- **Movement** — one append-only ledger entry (receive / consume / produce / ship / scrap / correct).
