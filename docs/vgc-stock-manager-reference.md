# VGC Stock Manager — Project Reference

> **Purpose of this file.** A complete, self-contained technical reference for the VGC Stock Manager system. Written so that a new chat (or a context-collapsed one) can pick up the work with no other background. Kept in GitHub (`vgc-ltd-wp/vgc-plugin-updates` → `docs/`), deliberately **not** part of any release zip.
>
> **Pinned to:** Stock Manager **1.3.0** · Stock Bridge **0.3.0**
>
> ⚠️ **This file is updated and pushed with every release** — it must never lag the shipped version. See §7 (Working conventions).

---

## 1. What this is

A **workshop inventory and production system** for a small manufacturer (candles, mugs, gift sets). It is **not** a shop — it runs on its own dedicated WordPress site (a backoffice subdomain) and pushes finished-goods stock to a separate WooCommerce shop.

### Two plugins

| Plugin | Slug | Installed on | Job |
|---|---|---|---|
| **VGC Stock Manager** | `vgc-stock-manager` | Backoffice WP site | The whole app: items, recipes, production, costing, reports, PWA |
| **VGC Stock Bridge** | `vgc-stock-bridge` | The WooCommerce shop | Tiny token-auth REST surface: list products, read/adjust/set stock. **No orders, no customers.** |

### Non-negotiable design decisions (do not "fix" these)

1. **Unified item model.** No hard line between material and product. A Base Candle is a sellable product *and* a component of a Gift Box. This is what makes nested recipes possible.
2. **The ledger is truth.** Stock is the **sum of append-only movements**, never a typed number. `items.stock_qty` is only a cache, rebuildable via `recompute_stock()`.
3. **Production is batch-based.** Recipes have a **yield** ("1 run makes 24"). The UI inputs **runs**, not units.
4. **Consume-from-stock.** One run = **one assembly level**. To make a Gift Box you must already have Base Candles in stock. You produce each level as its own run.
5. **Push deltas, never absolutes.** Producing a sellable item pushes `+N` to the shop, so **online sales made in the meantime are never clobbered**. `set` exists only as an explicit, confirmed reconcile.
6. **Shop price is never imported as cost.** A selling price is not a cost price; it would poison every roll-up and margin.
7. **All UI on the WP front-end**, at the **site root**. Never wp-admin. Other front-end URLs redirect to `/`.
8. **No framework, no build step.** Vanilla JS, `innerHTML` rendering, hash routing, one plain CSS file. Must work offline as an installed PWA — **no CDNs, no external fonts/icons**.

---

## 2. Repository / file layout

Local working dir: `C:\Projecs\Claude Code\`

```
vgc-stock-manager/                  ← the app plugin (zipped for release)
  vgc-stock-manager.php             main file: constants, table helpers, bootstrap
  uninstall.php                     drops tables + options
  readme.txt                        changelog
  includes/
    class-vgc-plugin-updater.php    shared VGC self-update (reused verbatim)
    class-install.php               dbDelta schema
    class-units.php                 VGC_SM_Units — unit registry + conversion
    class-repository.php            VGC_SM_Repository — all DB access + ledger
    class-bom.php                   VGC_SM_BOM — recipe maths
    class-production.php            VGC_SM_Production — production runs
    class-sync-client.php           VGC_SM_Sync — talks to the Bridge; settings
    class-i18n.php                  VGC_SM_I18n — catalogue + editable overrides
    class-help.php                  VGC_SM_Help — in-app wiki content
    class-access.php                VGC_SM_Access — capability + role
    class-rest-api.php              VGC_SM_REST_API — every endpoint
    class-frontend.php              VGC_SM_Frontend — shell, login, SW, manifest
  app/
    app.css                         the entire design system
    app.js                          the entire SPA
    icon-192.png, icon-512.png      PWA icons (generated, brand terracotta)

vgc-stock-bridge/                   ← the shop companion (zipped for release)
  vgc-stock-bridge.php
  includes/class-rest-controller.php   ← the whole surface
  includes/class-settings.php          ← token + API URL display
  includes/class-vgc-plugin-updater.php

_releases/                          ← built zips live here
vgc-stock-manager-design-brief.md   ← design brief (not shipped)
vgc-stock-manager-reference.md      ← THIS FILE (not shipped)
```

---

## 3. Data model

### Tables (prefix `wp_vgc_sm_`)

| Table | Purpose |
|---|---|
| `items` | The unified item model. |
| `categories` | User-defined categories. |
| `boms` | One recipe per manufactured item: `output_item_id`, `yield_qty`. |
| `bom_items` | Recipe components: `component_item_id`, `quantity`, `unit`, **`basis`** (`item`\|`run`). |
| `bom_extras` | Non-material costs: `label`, `amount`, `basis`. |
| `movements` | **Append-only ledger.** `type` (receive/consume/produce/ship/scrap/correct/consign_out/consign_return), signed `qty`, `ref_type`/`ref_id`, `partner_id`. |
| `production_runs` | One row per run; movements reference it. |
| `sync_log` | Every Bridge call. |
| `partners` | Shops we supply / makers we take from. `type` (`customer`\|`supplier`\|`both`), `active` (archived, never deleted). Flat `contact_name`/`email`/`phone`/`address` are a **cached mirror of the primary** child rows (kept in step by `sync_primary_fields()`). |
| `partner_locations` | Branches/warehouses: `label`, `address`, `is_primary`, `sort_order`. |
| `partner_contacts` | People: `name`, `role`, `email`, `phone`, `is_primary`, `sort_order`. |
| `partner_prices` | Agreed unit price per (partner, item). Drives note pricing. |
| `stock_notes` | The documents. `number` (`SN-YYYY-NNNN`, assigned on issue), `partner_id`, `direction`, `type`, `status` (`draft`\|`issued`\|`settled`\|`cancelled`), `total_net`. |
| `stock_note_lines` | `item_id`, `qty`, `unit`, `unit_price`, `line_net`. |
| `consignment_ledger` | **Second append-only ledger**: how much of an item is at a partner. Releases add, sale reports and returns subtract; cancels write reversing rows. |

### `items` columns worth knowing

`sku` (unique) · `name` · `kind` (`raw`\|`manufactured`) · `unit` (base/stock unit) · `stock_qty` (**cache**) · `reorder_level` · `is_sellable` · `woo_sku` · `woo_product_id` · `supplier` · `barcode` · `category_id` · `image_id` · `pack_label` · `pack_size` · `cost_net` · `vat_rate` (default 20) · `active` (0 = **archived**)

**DB_VERSION is currently `0.8.0`.** Bump it in `vgc-stock-manager.php` whenever the schema changes — `create_tables()` runs `dbDelta` on `plugins_loaded` when it differs, which auto-migrates.

### Options

| Option | Contents |
|---|---|
| `vgc_sm_db_version` | Schema version guard. |
| `vgc_sm_partners_split` | Set once the 1.3.0 flat→child partner migration has run. |
| `vgc_sm_settings` | `bridge_url`, `bridge_token`, `auto_push`, `currency` (default `€`), `language` (default `en`). |
| `vgc_sm_units` | Custom (non-builtin) unit codes. |
| `vgc_sm_i18n_overrides` | `{ lang: { source_string: translation } }` — user-edited wording. |

---

## 4. The engine (the part that must stay correct)

### Units — `VGC_SM_Units`
Built-in registry with a **dimension** and a **factor**: weight (mg/g/dag/kg → base g), volume (ml/cl/dl/l → base ml), count (pcs). Custom units are count/1. `convert($qty,$from,$to)` scales within a dimension and returns unchanged across dimensions (degrade safely).

### Recipe maths — `VGC_SM_BOM`
The pivotal helper:

```php
per_item_qty($c, $yield)      // basis 'item' → quantity; basis 'run' → quantity / yield
demand_per_item($c, $yield)   // per_item_qty converted into the COMPONENT'S base/stock unit
```

**Everything routes through `demand_per_item()`** — `direct_requirements()`, `max_buildable()`, `plan_produce()`, `explode_raw()`, `unit_cost_net()`. This is why a recipe in grams reconciles with stock in kg, and why per-item and per-batch both work.

- `direct_requirements($item,$qty)` — one assembly level. Returns need (in the component's stock unit), available, short, unit_cost, line_cost, plus `recipe_unit`/`need_recipe` for the "180 g → 0.18 kg" display.
- `plan_build($item,$qty)` — recursive **net requirements**: uses on-hand stock of intermediates first, only builds/buys the shortfall. A mutable `available` map is decremented as it allocates, so a component shared across branches isn't double-counted. Returns `feasible`, ordered `builds` (children first), `raw_short`.
- `unit_cost_net($item)` — recursive roll-up: Σ(component unit cost × demand_per_item) **+ extras** (per-item, or per-batch ÷ yield). Cycle- and depth-guarded.
- `would_create_cycle()` — used by the recipe editor to reject A→B→A.

### Production — `VGC_SM_Production`
`run()` is **transactional**: `production_runs` row + `consume` movements + `produce` movement + optional `scrap` movement, all inside `START TRANSACTION`/`COMMIT`. Blocks on shortages unless `allow_negative`. Fires:

```php
do_action( 'vgc_sm_production_completed', $item_id, $net_qty, $run_id );
```

`$net_qty` is **produced minus scrap** — the sync client listens here and pushes that, so defective units never reach the shop.

### Sync — `VGC_SM_Sync`
`request()` → Bridge with `X-VGC-Token`. `push_adjust()` (delta, the normal path), `push_set()` (reconcile only), `read_stock()`, `pull_products()`, `shop_levels()`, `push_item()`. Everything logged to `sync_log`.

### Partners and stock notes — `VGC_SM_Partners`, `VGC_SM_Notes`

`VGC_SM_Notes::types()` is the single table that drives everything. Each type declares its effect:

| type | direction | `stock` | `consignment` | movement | owes us | we owe |
|---|---|---|---|---|---|---|
| `release` | out | −1 | +1 | `consign_out` | no | no |
| `sale_report` | out | 0 | −1 | — | **yes** | no |
| `return_in` | out | +1 | −1 | `consign_return` | no | no |
| `direct_sale` | out | −1 | 0 | `ship` | **yes** | no |
| `take_in` | in | 0 | +1 | — | no | no |
| `purchase_in` | in | +1 | 0 | `receive` | no | **yes** |
| `buy_held` | in | +1 | −1 | `receive` | no | **yes** |
| `return_out` | in | 0 | −1 | — | no | no |
| `sold_held` | in | 0 | −1 | — | no | **yes** |

Read it as: *what happens to my stock* and *what happens to the pile*. For `direction=out` the pile is **our goods at the partner** (`consignment_ledger` direction `out`); for `direction=in` it is the **held bucket** — the maker's goods at our place (direction `in`). A release moves goods out of stock into the out-pile without selling; a sale report never touches stock but clears the out-pile and the partner owes us. Inbound mirrors it: `take_in` fills the held bucket without touching our stock; `sold_held`/`buy_held` empty it and we owe the maker; `buy_held`/`purchase_in` are the only inbound types that add to our own stock.

**Held stock is never our own stock and is never pushed to the shop** (that is the on-demand Phase 4). Only `stock`-affecting movements push, so `purchase_in`/`buy_held` push a positive delta for sellable items; everything else inbound is stock-neutral.

- `save_draft()` — drafts only; an issued note is immutable. A line with no price falls back to the partner's price list.
- `issue()` — **pre-flight first**: never release stock you do not have, never report/return more than the partner is holding. Problems → `WP_REST_Response` 409 with `problems[]` and **nothing is written**. Otherwise one transaction: movements + consignment rows + number + status, then shop pushes.
- `cancel()` — writes **reversing entries** in both ledgers and pushes the reverse to the shop. Never deletes.
- `outstanding()` / `outstanding_all($partner,$direction)` / `at_partners()` / `held()` / `balance_owed()` / `balance_we_owe()` — all derived by SUM over the ledgers, so they cannot drift. `outstanding_all(..,'in')` is the held report; `held($item)` is the per-item held total.
- `push_to_shop()` — sellable + `auto_push` only, and always a **delta**.

---

## 5. REST API (`vgc-stock/v1`)

Auth: same-origin cookie + `X-WP-Nonce`. Permission: `vgc_sm_access`; `$admin` routes additionally need `manage_options`.

| Method | Route | Notes |
|---|---|---|
| GET/POST | `/items` | list (filters: `search`, `kind`, `category_id`, `low_only`, `archived`) / create |
| GET/PUT/**DELETE** | `/items/{id}` | DELETE takes `?mode=archive\|delete`; refuses if used in a recipe (409 + `used_in`) |
| GET | `/items/{id}/movements` | ledger history |
| GET | `/items/{id}/shop-stock` | live shop qty for a sellable item |
| GET | `/items/lookup?code=` | barcode/SKU |
| GET | `/items/suggest-sku?name=` | unique SKU from a name |
| POST | `/items/import` | CSV rows upsert |
| POST | `/movements` | `receive` \| `ship` \| `scrap` \| `adjust` \| `set` |
| GET/PUT | `/recipe/{id}` | components + extras; PUT rejects cycles |
| GET | `/production/preview` | requirements, shortages, materials/extras/total cost |
| GET | `/production/plan` | recursive build plan |
| POST | `/production/run` | `qty`, `allow_negative`, `scrap_qty`, `scrap_note` |
| GET | `/dashboard` | low materials / low products |
| GET | `/reports/stock`, `/reports/production` | + scrap; CSV built client-side |
| GET/POST | `/categories`, PUT/DELETE `/categories/{id}` | |
| GET/POST | `/units` | codes + `meta{dimension,factor}` |
| POST | `/media` | image upload (gated by `vgc_sm_access`, **not** `upload_files`) |
| GET/POST | `/settings`, POST `/settings/test` | *(admin)* |
| GET/POST | `/translations`, POST `/translations/reset` | *(admin)* |
| GET | `/shop/levels`, POST `/shop/push` | |
| GET | `/shop/products`, POST `/shop/pull` | *(admin)* pull products, incl. image sideload |
| GET/POST | `/partners`, GET/PUT/**DELETE** `/partners/{id}` | DELETE archives. GET {id} returns outstanding + notes + price list + `owed`. |
| POST | `/partners/{id}/prices` | upsert one agreed price (empty `unit_price` clears it) |
| GET/POST | `/notes`, GET/PUT/DELETE `/notes/{id}` | PUT/DELETE are **drafts only** |
| POST | `/notes/{id}/issue` | 409 + `problems[]` if it would break stock |
| POST | `/notes/{id}/cancel`, `/notes/{id}/paid` | cancel = reversing entries; paid = `settled` |
| GET | `/consignment/outstanding` | `direction=out` (default, "what have we shipped") or `direction=in` (held stock); + totals at price and at cost |
| GET | `/help` | the in-app wiki |

### Bridge (`vgc-stock-bridge/v1`) — on the shop
Auth: `X-VGC-Token` header (shared secret) over HTTPS.

`GET /ping` · `GET /products?page&per_page&search` (variations expanded; returns `image` + `image_full`) · `GET /stock?skus=` · `POST /stock/adjust` (**signed deltas — the normal path**) · `POST /stock/set` (absolute).

---

## 6. Front end

`class-frontend.php` serves the app at the **site root** on `template_redirect` with a standalone full-screen template (no theme). Not logged in / lacking `vgc_sm_access` → a branded login (not `wp-login.php`).

- **PWA**: manifest + service worker served *virtually* at `/vgc-app.webmanifest` and `/vgc-sw.js` (matched by path on `init`, so root scope works). SW is registered with `updateViaCache:'none'` + a version-stamped URL, calls `reg.update()` each load and **reloads once on `controllerchange`** — this is why plugin updates land without a hard refresh. The REST API is **never** cached.
- **Offline**: writes go through an **IndexedDB queue** (`write()`), replayed on reconnect. Reads fail offline by design.
- `app.js` boot payload (`window.VGC_SM`): `restUrl`, `nonce`, `appUrl`, `swUrl`, `logoutUrl`, `canManage`, `currency`, `lang`, `strings`, `user`, `version`.

### Design system (0.16.0, implemented from a Claude Design project)
Warm parchment + terracotta, "Workshop backoffice".
Brand `#B65C22` · bg `#F5F1EA` · card `#FFF` · ink `#221F1A` · danger `#B42318` · ok `#2E7048` · dark payoff panel `#221F1A`.
Inline SVG icon set (`ICON_PATHS` / `icon()`). **Desktop ≥900px** = sidebar + tables + sticky cost panel; **phone** = bottom tabs + FAB. Numbers/SKUs/money are monospace + tabular.

### i18n (self-contained — the SPA has no `wp.i18n`)
English source strings are the **keys**. `VGC_SM_I18n::map()` = shipped catalogue **+ user overrides on top**. In JS: `t()` for composed/dynamic strings, toasts, prompts; plus `translateTree()` (a TreeWalker) that translates whole static text nodes and `placeholder`/`title`/`aria-label` after each render. **Changing language reloads the page** (the catalogue ships in the boot payload).
To add a language: add a catalogue method in `class-i18n.php` and list it in `languages()`.

---

## 7. Working conventions (follow these)

1. **Bump the version on every change** — plugin header + `VGC_STOCK_MANAGER_VERSION` constant + `readme.txt` Stable tag + changelog entry.
2. **Build zips with forward slashes.** PowerShell's `Compress-Archive` writes backslash entry paths that **break on Linux**. Use `System.IO.Compression.ZipArchive` and `CreateEntry(rel.Replace('\\','/'))`. Zips go to `_releases/` as `vgc-<slug>-<version>.zip`.
3. **The user tests on staging** — do not run or lint the plugin locally. (`node --check app/app.js` and a CSS brace check are fine and worth doing.)
4. **TEST MODE: publish every update immediately** (until the user says production mode). Publishing =
   - `gh release create vgc-<slug>-<version> _releases/<zip> --repo vgc-ltd-wp/vgc-plugin-updates`
   - update `plugins.json` in that repo (`version`, `download_url`, prepend changelog)
   - **update THIS file** — the "Pinned to" line, the feature-history table, and any section the change touches — and copy it to `docs/vgc-stock-manager-reference.md` in the same commit
   - commit, push, verify with `gh api .../contents/plugins.json` (the raw CDN lags ~5 min).
5. **This reference is always pinned to the current version.** It is part of the release, not an afterthought: a release is not finished until the doc matches what shipped. A stale reference is worse than none, because the next session will trust it.
6. **Self-update wiring**: instantiate `VGC_Plugin_Updater` **after** the `ABSPATH` guard. (Several older VGC plugins have it *inside* the guard, so it never runs — a real bug worth auditing separately.)
7. Update the memory files under `.claude/projects/.../memory/` when a durable decision changes.

---

## 8. Feature history (what exists and why)

| Ver | Feature |
|---|---|
| 0.1–0.5 | Foundation, front-end shell + login, BOM engine, REST + SPA + PWA, sync client |
| 0.6 | Packaging (packs) + pricing with VAT |
| 0.7 | Costing on Produce; **production became run/batch-based** |
| 0.8 | Recipe components **per item or per batch** |
| 0.9 | **Unit conversion** (weight/volume) |
| 0.10 | Non-material costs (labour/overhead) |
| 0.11 | SKU generation, currency (€ default), price formatting |
| 0.12 | **Cache-safe updates**, Reports, CSV import, scrap |
| 0.13 | Scrap as part of a production run (net good pushed) |
| 0.14 | Categories |
| 0.15 | Item photos |
| 0.16 | **Design system implementation** (sidebar + tables + panels) |
| 0.17 | UI language setting + full Bulgarian |
| 0.18 | **Pull products from the shop** (Bridge 0.2.0) |
| 0.19 | Pull imports photos; shop stock on item detail (Bridge 0.3.0) |
| 0.20 | **Remove items**: archive vs permanent delete, recipe-usage guard |
| 0.21 | Full-width desktop; sortable items table |
| 0.22 | Sorting persists; sorting on reports/shop/pull |
| 0.23 | Sidebar category shortcuts (`#/items?category=…`) |
| 0.24 | **Editable translations** (overrides survive updates) |
| **1.0.0** | **In-app wiki**; first stable release |
| 1.0.1 | Shop stock: photos fixed (`/shop/levels` now returns `image_thumb` + category), category filter + sortable Category column; sidebar category shortcuts made collapsible (open only in the Items section) |
| 1.1.0 | **Partners + stock notes (outbound)**: price lists, `SN-YYYY-NNNN` documents (release / sale report / return / direct sale), draft → issue → settle/cancel, pre-flight validation, consignment ledger, **Out on consignment** report, "At partners" on item detail, shop reduced on release |
| 1.2.0 | **Inbound notes + held bucket**: take on consignment / purchase / buy-held / return-out / sold-from-held; `held()` + `balance_we_owe()`; partner page shows held goods + "You owe"; **Held stock** report; "Held (from makers)" on item detail; note-type dropdown grouped inbound/outbound. Also wired the `/outstanding` route that 1.1.0 shipped un-routed. |
| **1.3.0** | **Multi-location / multi-contact partners**: `partner_locations` + `partner_contacts` child tables (one primary each), repeatable rows in the partner editor, directory card on the partner page. Flat partner fields become a cached mirror of the primaries (`sync_primary_fields()`); one-time `migrate_flat_fields()` seeds child rows from the old columns (guarded by `vgc_sm_partners_split`). Partner create/update accept `locations[]`/`contacts[]`. |

---

## 9. Consignment: what is agreed but not yet built

The outbound half shipped in 1.1.0; the inbound half (held bucket) in 1.2.0. Remaining, as agreed with the user:

- **Phase 4 — shop publishing of held stock**, synced *on demand* (not automatically — held stock is deliberately kept out of the shop until then), plus a "Reconcile from shop" action.
- **Phase 5 — balances/statements** per partner (both directions) and printable notes.

Two standing defaults the user accepted, relevant to Phase 4: **held stock is consumed before own stock** when something sells (operator-driven for now; matters once shop sales auto-decrement), and **you can only release what you own** (a maker's held goods cannot be released onward on an outbound note).

---

## 10. Known gaps / candidate next steps

- Historical costs are **not snapshotted** at run time — reports estimate using each item's *current* unit cost.
- Pulling many products with photos does one download per product; a huge catalogue can hit a PHP timeout (pull in batches, or move image copying to a background job).
- No margin view (computed cost vs shop selling price) — the Bridge already returns `price`, so this is cheap to add.
- No order pull-back: online sales reduce shop stock but not local stock. Deliberate (the user chose push-only), but a `/orders` style sync is the natural extension if local and shop stock must fully agree.
- Categories are a **flat list** (no nesting).
- Archiving a sellable item does **not** touch the shop (the WooCommerce product stays live).
- The wiki (`class-help.php`) is **English only** — its body HTML isn't routed through the i18n catalogue.
