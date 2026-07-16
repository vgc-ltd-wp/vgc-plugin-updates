# VGC Stock Manager — Project Reference

> **Purpose of this file.** A complete, self-contained technical reference for the VGC Stock Manager system. Written so that a new chat (or a context-collapsed one) can pick up the work with no other background. Kept in GitHub (`vgc-ltd-wp/vgc-plugin-updates` → `docs/`), deliberately **not** part of any release zip.
>
> **Pinned to:** Stock Manager **1.13.0** · Stock Bridge **0.4.0**
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
| `partners` | Shops we supply / makers we take from. `type` (`customer`\|`supplier`\|`both`), `active` (archived, never deleted), `vat_registered`/`vat_number` (1.9.0), `payment_terms_days` (1.10.0, default 30; drives note due dates). Flat `contact_name`/`email`/`phone`/`address` are a **cached mirror of the primary** child rows (kept in step by `sync_primary_fields()`). |
| `partner_locations` | Branches/warehouses, **each with its own contact**: `label`, `address`, `contact_name`/`contact_role`/`contact_email`/`contact_phone` (1.6.0), `is_primary`, `sort_order`. |
| `partner_contacts` | **Additional** people not tied to a location: `name`, `role`, `email`, `phone`, `is_primary`, `sort_order`. |
| `partner_prices` | Agreed unit price per (partner, item). Drives note pricing. |
| `stock_notes` | The documents. `number` (`SN-YYYY-NNNN`), `partner_id`, `location_id` (destination), `direction`, `type`, `status`, `note_date` (user-set; drives `issued_at`), `due_date` (note_date + partner terms; money notes only), `skip_stock` ("already sent" — no stock effect), `is_refund` (a return that credits money and skips the pile), `total_net`/`total_vat`/`total_gross`. |
| `stock_note_lines` | `item_id`, `qty`, `unit`, `unit_price` (**net**), `vat_rate`, `line_net`/`line_vat`/`line_gross`, `line_note`, `is_display` (a display piece on loan). |
| `consignment_ledger` | **Second append-only ledger**: how much of an item is at a partner. Releases add, sale reports and returns subtract; cancels write reversing rows. `is_display` splits the pile into **sellable vs display pools** — a sale report can only draw on the sellable pool. |
| `orders` | **The order model (1.11.0) — deliberately MUTABLE.** One living doc per customer order: `number` (`ORD-YYYY-NNNN`), `partner_id`, `location_id`, `date_ordered`/`date_sent`/`date_received`, `payment_mode` (`full`\|`on_sale`), `payment_terms_days`, `due_date`, `prices_include_vat` (1.12.0 — whether a typed `unit_price` already has VAT in it), `transport_cost`/`transport_payer` (`us`\|`customer`), `already_sent`, `paid_amount`, `status` (`open`\|`completed` — never final). |
| `order_lines` | `item_id`, `qty_ordered`/`qty_sent`/`qty_sold`/`qty_returned`, `unit_price`, `unit_cost` (**snapshot**, so margin never drifts), `vat_rate`, `is_display`, `line_note`, plus **`applied_out`/`applied_pile`** — what the ledgers already reflect for this line. |
| `order_payments` | Partial payments against an order (1.13.0): `paid_on`, `amount`, `note`. **Paid is SUM(payments)** — never a typed-over field. One-time `migrate_paid_amounts()` turns a legacy `orders.paid_amount` into the first payment (`vgc_sm_order_payments_migrated`). |
| `audit` | Activity log (1.7.0): `user_id`, `user_name`, `action` (dotted slug), `object_type`/`object_id`, `summary`, `ip`, `created_at`. Append-only, best-effort (never blocks the action it records). |

### `items` columns worth knowing

`sku` (unique) · `name` · `kind` (`raw`\|`manufactured`) · `unit` (base/stock unit) · `stock_qty` (**cache**) · `reorder_level` · `is_sellable` · `woo_sku` · `woo_product_id` · `supplier` · `barcode` · `category_id` · `image_id` · `pack_label` · `pack_size` · `cost_net` · `vat_rate` (default 20) · `active` (0 = **archived**) · `shop_held` (held units currently listed on the shop) · `shop_baseline` (shop qty as last accounted for, drives reconcile)

**DB_VERSION is currently `0.16.0`.** Bump it in `vgc-stock-manager.php` whenever the schema changes — `create_tables()` runs `dbDelta` on `plugins_loaded` when it differs, which auto-migrates.

### Options

| Option | Contents |
|---|---|
| `vgc_sm_db_version` | Schema version guard. |
| `vgc_sm_partners_split` | Set once the 1.3.0 flat→child partner migration has run. |
| `vgc_sm_notes_vat_backfill` | Set once the 1.9.0 backfill (pre-VAT notes → `total_gross = total_net`, 0% VAT) has run. |
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
- `statement($partner,$from,$to)` (1.5.0) — every money-bearing note both ways over a period (issued + settled), with outstanding `they_owe` / `we_owe` / `net`. Outbound money = `sale_report`,`direct_sale`; inbound money = `purchase_in`,`buy_held`,`sold_held`. Only `issued` notes count towards outstanding.
- `push_to_shop()` — sellable + `auto_push` only, and always a **delta**.

**Shop publishing of held stock (1.4.0).** Held goods stay off the shop until the operator publishes them.
- `publish_held($item,$qty)` — push `+qty` delta, `shop_held += qty`, set `shop_baseline` to the shop qty just read back. `unpublish_held()` is the reverse.
- `reconcile_scan()` — for every item with `shop_held > 0`, read the shop; `sold = clamp(baseline − current, 0, shop_held)` (only the held share; own-stock sales are out of scope by the push-only design); split `sold` across makers **FIFO by earliest `created_at`** via `held_by_maker()`.
- `reconcile_preview()` (advisory) / `reconcile_apply()` (books one issued `sold_held` note per maker with `skip_clamp`, then lowers `shop_held` and re-baselines). Both recompute live.
- **Invariant:** the shop never lists more of a maker's goods than we still hold. `clamp_shop_held($item)` runs after any held-reducing note (`issue()` for inbound `consignment<0`; `cancel()` of a `take_in`) and pushes the surplus off. Reconcile passes `skip_clamp` because the online sale is what reduced the shop.

### Orders — `VGC_SM_Orders` (1.11.0)

The user asked for a spreadsheet, not a stack of immutable documents. So an order is **fully editable, forever** — and the ledgers stay append-only anyway, via reconciliation rather than rewriting.

- **The invariant:** every line stores `applied_out` / `applied_pile` = what the movement ledger and the consignment ledger already reflect for it. On each `save()` → `reconcile()`, the engine computes the *desired* state and writes **only the delta**:
  - `want_out  = already_sent ? 0 : (qty_sent - qty_returned)` → movement of `-(want_out - applied_out)`
  - `want_pile = qty_sent - qty_sold - qty_returned` → consignment row of `want_pile - applied_pile`
  This is why editing a sent qty from 3 → 5 a week later Just Works, and why history is never rewritten.
- **Removing a line** zeroes its quantities first so reconcile releases the stock, *then* deletes the row (same for `delete()` of a whole order).
- `net_unit($line, $incl)` (1.12.0) is the one place VAT-inclusive entry lives. `unit_price` is stored **exactly as typed**; `prices_include_vat` says how to read it (`incl ? price/(1+vat/100) : price`). Storing the typed figure rather than a converted one is deliberate — no rounding drift.
- **Display lines carry no money at all**: `billable_qty()` returns 0 for them, and the editor renders them in a separate section on a shorter grid (`.vgc-sm-oline--demo`, 8 columns) with no price/cost/VAT/margin fields.
- `billable_qty()` is the one place the payment mode lives: `full` → `sent - returned`; `on_sale` → `sold`. Display lines are **never** billable.
- `totals()` derives everything (net/VAT/gross/cost/**margin**/paid/balance/out_there). Transport lands on whoever `transport_payer` says: on the customer it adds to gross; on us it comes out of margin.
- `set_complete()` only flips `status`. **No status is final** — this is a product requirement, not an oversight.
- Orders write to the **same** ledgers as stock notes, so "Out on consignment", item stock and the shop push all keep working across both models.

---

## 5. REST API (`vgc-stock/v1`)

Auth: same-origin cookie + `X-WP-Nonce`. **Access levels (1.7.0)** — `VGC_SM_Access::level()` resolves a user to `viewer`|`operator`|`manager`|`admin`: admin = `manage_options`; otherwise the `vgc_sm_level` user-meta (default `operator`) for anyone with the `vgc_sm_access` cap; `null` = no access. Permission callbacks: `$auth` = viewer+ (reads), `$write` = `require_operator` (day-to-day writes), `$mgr` = `require_manager` (partners/prices/deletes/shop ops), `$admin` = `authorize_admin` (settings/translations/team/audit). Enforcement is server-side; the SPA hides what a level can't do via boot `perms` (`write`/`manage`/`admin`). Existing Stock Operators resolve to `operator`; nothing to migrate.

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
| GET | `/partners/{id}/statement?from=&to=` | money owed both ways over a period (lines + totals) |
| GET/POST | `/notes`, GET/PUT/DELETE `/notes/{id}` | PUT/DELETE are **drafts only** |
| POST | `/notes/{id}/issue` | 409 + `problems[]` if it would break stock |
| POST | `/notes/{id}/cancel`, `/notes/{id}/paid` | cancel = reversing entries; paid = `settled` |
| GET | `/consignment/outstanding` | `direction=out` (default, "what have we shipped") or `direction=in` (held stock); + totals at price and at cost |
| POST | `/consignment/publish`, `/consignment/unpublish` | list/de-list an item's held units on the shop (`item_id`, `qty`; qty≤0 = all) |
| GET/POST | `/consignment/reconcile` | GET = preview; POST = book detected shop sales as `sold_held` notes |
| GET/POST | `/orders`, GET/PUT/DELETE `/orders/{id}` | the order model; PUT is always allowed (never locks) |
| POST | `/orders/{id}/complete` | `{complete:0\|1}` — reversible |
| GET | `/help` | the in-app wiki |
| GET/POST | `/team`, `/team/{id}` | *(admin)* list users + levels / set a user's level (`viewer`\|`operator`\|`manager`\|`none`) |
| GET | `/audit` | *(admin)* activity log, filtered (`search`,`user_id`,`action`,`from`,`to`,`page`) + paginated |

### Bridge (`vgc-stock-bridge/v1`) — on the shop
Auth: `X-VGC-Token` header (shared secret) over HTTPS.

`GET /ping` · `GET /products?page&per_page&search&category&type` (variations expanded; returns `image`+`image_full`, `virtual`/`downloadable`; `category`=term slug, `type`=simple/variable/grouped/external — 0.4.0) · `GET /product-categories` (0.4.0) · `GET /stock?skus=` · `POST /stock/adjust` (**signed deltas — the normal path**) · `POST /stock/set` (absolute).

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
| 1.3.0 | **Multi-location / multi-contact partners**: `partner_locations` + `partner_contacts` child tables (one primary each), repeatable rows in the partner editor, directory card on the partner page. Flat partner fields become a cached mirror of the primaries (`sync_primary_fields()`); one-time `migrate_flat_fields()` seeds child rows from the old columns (guarded by `vgc_sm_partners_split`). Partner create/update accept `locations[]`/`contacts[]`. |
| 1.4.0 | **Shop publishing of held stock** (Phase 4): `items.shop_held` + `shop_baseline`; publish/unpublish held units to the shop; "Reconcile from shop" reads the shop back, FIFO-splits online sales across makers, previews then books `sold_held` notes; `clamp_shop_held()` invariant keeps the shop from ever offering more than we hold. Item detail gains Publish/Unpublish + "On shop from held"; Held stock screen gains Reconcile. |
| 1.5.0 | **Partner statements + printable documents** (Phase 5): `VGC_SM_Notes::statement()`, `/partners/{id}/statement`; Statement screen (`#/statement/{id}`) with date range, both-way outstanding totals, net position, CSV. `@media print` letterhead (boot `siteName`) prints issued notes and statements as one clean sheet; `.vgc-sm-noprint`/`.vgc-sm-printonly`/`.vgc-sm-printhead` control what shows. **Completes the consignment feature set.** |
| 1.6.0 | **Per-location contacts**: `partner_locations` gains `contact_name/role/email/phone`; the standalone `partner_contacts` list is relabelled "Additional contacts". `sync_primary_fields()` now prefers the primary location's contact (falls back to the first additional contact). Partner editor location rows gain a contact block; directory card shows each location's contact. DB_VERSION 0.10.0 (dbDelta adds the columns; no data migration). |
| 1.7.2 | Partner name shown in the sticky top bar on the partner page (`setTopTitle()` in `viewPartner`). |
| 1.7.3 | Pull products fetched all pages at 100/page (superseded by 1.7.4). |
| 1.7.4 | **Pull products paginated** — `viewPull` loads one page of `PULL_PER=20` at a time with Previous/Next; selection persists across pages in a `picks` map keyed by `product_id`. |
| **1.13.0** | **Partial payments** (`order_payments`, DB 0.16.0) — `add_payment()`/`delete_payment()`/`paid_total()`; `totals()[paid]` is the sum of the trail. **Overdue fix**: `overdue` now also requires `balance > 0.005` (a paid order past its date was wrongly flagging). Orders surfaced on the partner screen (`get_partner` returns `orders`), and `shape_partner[owed]` = notes balance **+** open-order balances. |
| 1.12.0 | Display pieces moved to their own section in the order editor (no price/VAT/margin fields; excluded from totals via `billable_qty()`), and `orders.prices_include_vat` (DB 0.15.0) lets prices be typed VAT-inclusive — `VGC_SM_Orders::net_unit()` derives the net, the typed figure is stored untouched. |
| 1.11.0 | **Orders** — a mutable, order-centric model replacing the note-per-event dance for customer orders. `class-orders.php`, `orders`/`order_lines` (DB 0.14.0). Ordered/sent/sold/returned per line on one screen; payment mode `full`\|`on_sale`; transport + payer; paid/balance; **margin** from a snapshotted `unit_cost`; complete/reopen. Editing reconciles the ledgers by delta (`applied_out`/`applied_pile`). Stock notes remain for ad-hoc/inbound movements and share the same ledgers. |
| **1.10.0** | **Payment terms, refundable returns, display flag, print fixes** (DB 0.13.0). `partners.payment_terms_days` → `stock_notes.due_date` on issue (only for `is_money_note()` types; credits never fall due); statement gains due/overdue + an `overdue` total. `stock_notes.is_refund` on a `return_in`: credits `balance_owed`, skips the consignment write **and** its pre-flight (those goods were billed, not lent). `is_display` on note lines **and** the consignment ledger splits the pile into sellable/display pools — `outstanding()` takes a `$display` filter, sale reports can only draw on the sellable pool, `outstanding_all()` returns `display_qty`. Print: `@page A4 portrait`, cards `break-inside:auto` (they *must* flow), `thead` repeats, rows never split, `.vgc-sm-tablewrap` overflow visible (it was clipping), thumbs hidden. |
| 1.9.0 | **Note dates, "already sent", destinations, per-line VAT + notes, partner VAT** (DB 0.12.0). `note_date` drives `issued_at` on issue; `skip_stock` makes `issue()`/`cancel()` bypass the stock ledger *and* its pre-flight (consignment still applies); `location_id` = destination (validated against the partner's own locations). Lines gain `vat_rate`/`line_vat`/`line_gross`/`line_note`; net↔gross auto-fill is client-side, net is what's stored. **Balances + statements now sum `total_gross`** — one-time `backfill_vat()` sets legacy notes to gross=net/0% so they still read correctly. Partner `vat_registered`/`vat_number`. Editor lines are one flex row (`.vgc-sm-nline`). `list_partners` now returns `locations` via `locations_map()` (one query). |
| 1.8.0 | **Pull filters + virtual default** (needs Bridge 0.4.0): category (`product_cat` slug) and product-type filters on the pull screen, populated from `/shop/product-categories`. Bridge `shape_product` adds `virtual`/`downloadable`; `list_products` takes `category`/`type`. Auto-tick now skips `virtual` products (shown with a tag) as well as `already`. |
| 1.7.1 | **Settings hub**: the four admin config screens (Connection=`/settings`, `/translations`, `/team`, `/audit`) are grouped under one **Settings** sidebar entry with a shared tab bar (`settingsTabs()` + `SETTINGS_TABS`); `activeKey()` maps all four to `#/settings`. Help moved to its own bottom navlist (`NAV_HELP`). UI-only, no schema change. |
| **1.7.0** | **Roles + audit log**: four access levels (viewer/operator/manager/admin) via `VGC_SM_Access::level()`/`at_least()`/`set_level()` (user-meta `vgc_sm_level`); every REST route gated by `$write`/`$mgr`/`$admin`; boot `perms` + level drive UI gating. `class-audit.php` (`VGC_SM_Audit::log/query`) + `audit` table; logged at the mutation handlers and on `wp_login`/`wp_logout`. New admin screens **Team** (`#/team`) and **Activity log** (`#/audit`); DB_VERSION 0.11.0. |

---

## 9. Consignment: what is agreed but not yet built

All five phases have shipped: outbound (1.1.0), inbound/held bucket (1.2.0), multi-location/contact partners (1.3.0), shop publishing of held stock (1.4.0), and partner statements + printable notes (1.5.0). The consignment feature set is complete.

Standing defaults the user accepted: **held stock is consumed oldest-received-first** across makers when reconcile books shop sales (FIFO); **the shop never offers more held units than we hold** (`clamp_shop_held`); own-stock online sales remain out of scope (push-only design — the shop is authoritative for its own sales, we don't pull orders back). **You can only release what you own** (a maker's held goods cannot be released onward on an outbound note).

---

## 10. Known gaps / candidate next steps

- Historical costs are **not snapshotted** at run time — reports estimate using each item's *current* unit cost.
- Pulling many products with photos does one download per product; a huge catalogue can hit a PHP timeout (pull in batches, or move image copying to a background job).
- No margin view (computed cost vs shop selling price) — the Bridge already returns `price`, so this is cheap to add.
- No order pull-back: online sales reduce shop stock but not local stock. Deliberate (the user chose push-only), but a `/orders` style sync is the natural extension if local and shop stock must fully agree.
- Categories are a **flat list** (no nesting).
- Archiving a sellable item does **not** touch the shop (the WooCommerce product stays live).
- The wiki (`class-help.php`) is **English only** — its body HTML isn't routed through the i18n catalogue.
