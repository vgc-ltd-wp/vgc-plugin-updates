# VGC Stock Manager — developer guide

The map I (Claude) read **first** in any session that touches this plugin, so I
stop re-discovering the same structure and re-hitting the same bugs. Durable by
design: conventions, patterns, checklists and gotchas — the things that don't
change per feature. For "where is function X" use the companion
**`vgc-stock-manager-codemap.md`** (regenerate with `python vgc-stock-manager-codemap.py`).

Companion docs at the project root:
- **`vgc-stock-manager-codemap.md`** — every function/method → file + line + purpose (generated).
- **`vgc-stock-manager-reference.md`** — the per-version changelog/architecture log (pinned, mirrored to the update repo each release).
- **`vgc-stock-manager-design-brief.md`** — original product brief.

---

## 1. Orientation

- **Two plugins.** `vgc-stock-manager` (this repo) is a **standalone** backoffice app served at a site root, behind a login. `vgc-stock-bridge` is a thin WooCommerce companion on the *shop* site; the app talks to it over REST (`X-VGC-Token`) for **stock push + low-stock read only** — never orders/customers.
- **No build step.** `app/app.js` is one hand-written ES5 IIFE loaded via `<script>`. `app/app.css` is hand-written. No bundler, no transpile, no npm. Edit the files directly.
- **Testing is on staging.** The user tests on their own WordPress staging site. I do **not** run WordPress locally. I verify with: PHP lint, `node --check`, and a **browser harness** for UI (see §9).
- **PHP CLI is available:** `/c/xampp/php/php.exe` (7.4.10 — the declared minimum). Lint every PHP file before shipping.
- **The project root is not a git repo.** Release zips in `_releases/` are the only local backup. Releases live in the **`vgc-ltd-wp/vgc-plugin-updates`** GitHub repo (see §8).

---

## 2. Repo map (responsibilities)

PHP (`includes/`), one class per concern:

| File | Class | Owns |
|---|---|---|
| `class-install.php` | `VGC_SM_Install` | **The schema** (every `CREATE TABLE`), `dbDelta` on version change |
| `class-repository.php` | `VGC_SM_Repository` | Items CRUD, `sanitize_item` (column whitelist), `record_movement` (the stock ledger), `list_items`, seeds |
| `class-bom.php` | `VGC_SM_BOM` | Recipes (bill of materials), nested cost roll-up `unit_cost_net()`, `max_buildable` |
| `class-production.php` | `VGC_SM_Production` | Production runs (consume components, yield product) |
| `class-partners.php` | `VGC_SM_Partners` | Partners, locations, contacts, prices; `roles()` (observed customer/supplier) |
| `class-notes.php` | `VGC_SM_Notes` | **Stock notes** (9 immutable types), the consignment/held ledger, statements, shop-held publishing |
| `class-orders.php` | `VGC_SM_Orders` | **Orders** — mutable outbound document, delta-reconcile, totals, payments |
| `class-purchases.php` | `VGC_SM_Purchases` | **Purchases** — mutable inbound document (buy/consignment), mirror of Orders |
| `class-store.php` | `VGC_SM_Store` | Physical-store allocation (`store_qty` bucket, `store_ledger`) |
| `class-sync-client.php` | `VGC_SM_Sync` | Talks to the Bridge (push stock, read shop stock) |
| `class-rest-api.php` | `VGC_SM_REST_API` | The **route table** (`register_routes`), permission callbacks, `error_response`. ~620 lines. |
| `rest/trait-*.php` | traits on `VGC_SM_REST_API` | **Handlers + `shape_*`**, grouped by resource: items, production, partners, notes, orders, purchases, shop, reports, admin. Composed into the main class (1.22.0). |
| `class-i18n.php` | `VGC_SM_I18n` | The Bulgarian catalogue (English source string → BG), overrides |
| `class-access.php` | `VGC_SM_Access` | The 4 permission levels (viewer/operator/manager/admin) |
| `class-audit.php` | `VGC_SM_Audit` | Activity log |
| `class-frontend.php` | `VGC_SM_Frontend` | Serves the SPA shell, enqueues app.js/css, boot payload, root-scoping |
| `class-help.php` | `VGC_SM_Help` | The in-app wiki text. **Highest apostrophe-risk file** (long single-quoted prose) |

Front end:
- `app/app.js` — the entire SPA (router + every screen + helpers). ~5.4k lines, one IIFE.
- `app/app.css` — all styles. `vgc-sm-*` naming.

`vgc-stock-manager.php` — bootstrap: table-name helpers, `require_once` order, DB-version check, **one-time migrations** (option-guarded).

---

## 3. Data model & invariants

**Ledgers are the truth; cached numbers are for speed.** Three append-only ledgers, each with a cache on the item row:

| Ledger (table) | Caches | Meaning |
|---|---|---|
| `movements` | `items.stock_qty` | Our own stock. `record_movement()` inserts a row and `stock_qty += qty`. |
| `consignment_ledger` | (summed live) | `direction='out'` = our goods at a partner; `direction='in'` = the **held** bucket (their goods at us). |
| `store_ledger` | `items.store_qty` | Units physically on the brick-and-mortar shelf (a slice of `stock_qty`). |

Rules that must hold:
- **A cache is never authoritative.** It's always reconstructable by summing its ledger. `stock_qty` only ever changes via `record_movement`; `store_qty` only via `VGC_SM_Store::write`.
- **Held stock is NOT our stock.** It sits in `consignment_ledger(in)` and only becomes `stock_qty` when bought.
- **The store bucket is a slice of stock**, never additional. Moving to the store doesn't change `stock_qty`; only a store *sale* does. `record_movement` calls `VGC_SM_Store::clamp` on any negative delta so the slice can't exceed stock.

**Immutable vs mutable documents:**
- **Stock notes** (`VGC_SM_Notes::types()`, 9 types) are **immutable** once issued; a cancel writes reversing ledger entries. The type table drives `stock`/`consignment`/`movement`/`owes_us`/`we_owe` multipliers.
- **Orders and Purchases** are deliberately **mutable** — the operator edits them like a spreadsheet. Safe because each line stores `applied_*` (what the ledgers already reflect) and **`reconcile()` writes only the delta**. This is the single most important pattern in the app; read `VGC_SM_Orders::reconcile` once.

**VAT:** prices are stored **exactly as typed**; a `prices_include_vat` flag says how to read them. `strip_vat()` (in orders/purchases) divides out VAT when the flag is set — a 0% rate makes it a no-op (that's how non-VAT-registered vendors' "final" prices work). Margin is always ex-VAT on both sides. Margin % convention across the app = **margin / selling price × 100** (of price, not markup).

**The item model** (`vgc_sm_items`) — the columns that carry meaning:
- `kind` — `raw` (bought) or `manufactured` (made from a recipe). Drives recipe/production. **Sourcing, not role.**
- `for_sale` — the material↔product divide (1.21.0). An end product for sale vs a material/ingredient. **Role, independent of `kind`.**
- `is_sellable` — pushed to the online WooCommerce shop.
- `store_stocked` / `store_qty` — physical store.
- `cost_net` + `cost_manual` — manufacturing cost (recipe-computed unless `cost_manual`).
- `price_net` (retail) + `price_b2b` (wholesale) — selling prices, net; gross derived from `vat_rate`.

---

## 4. PHP conventions

- **REST routes** are all registered in one place — `VGC_SM_REST_API::register_routes()` in `class-rest-api.php` (the whole API surface at a glance). Permission callbacks are set once near the top: `$auth` (viewer+), `$write` (operator+), `$mgr` (manager+), `$admin`. Pick the tightest that fits.
- **REST handlers live in resource traits** (`includes/rest/trait-<resource>.php`), composed into `VGC_SM_REST_API`. To add an endpoint: register the route in `register_routes()`, add the handler method to the matching trait. `self::`, `__CLASS__` and `array( __CLASS__, 'x' )` all resolve to the composed class, so a handler in one trait can call a `shape_*`/helper in another (or in the main class) freely. Every method name must be unique across all traits + the main class (PHP fatals on a trait collision — which is a useful guard). Verify a REST refactor with the route-dump + reflection harnesses in scratch (see §9).
- **`shape_*($row)`** functions turn a DB row into the JSON the app expects (numbers as numbers, derived fields, translated where needed). One per entity: `shape_item`, `shape_order`, `shape_purchase`, `shape_partner`, `shape_note`. The list endpoints map `shape_*` over rows.
- **Writable columns are whitelisted** in `VGC_SM_Repository::sanitize_item` (and the parallel lists in `item_input` / `shape_item`). A column not in the whitelist can't be written — that's how `stock_qty`/`store_qty` stay guarded.
- **Migrations:** bump `VGC_STOCK_MANAGER_DB_VERSION` and add a `dbDelta` for new tables/columns in `class-install.php` (dbDelta adds columns in place). Data backfills go in `vgc-stock-manager.php` as **one-time, option-guarded** blocks (`if ( ! get_option('vgc_sm_x') ) { …; update_option('vgc_sm_x', 1); }`).
- **Audit** side-effectful actions with `VGC_SM_Audit::log(...)`.

---

## 5. app.js conventions

**Structure:** one IIFE. At top: `boot` (the `window.VGC_SM` payload), DOM handles (`APP`, `NAV`, `SIDEBAR`, `TITLE`, `BACKBTN`), then helpers, then one `viewX()` function per screen, then the router, then boot (`router()` at the very end). Banner comments `/* Screen: X */` mark each screen — the codemap lists them with line numbers.

**The helper vocabulary** (memorise — these are used everywhere):

| Helper | Signature | Does |
|---|---|---|
| `t` | `t(str)` | Translate (English key → current lang). |
| `screen` | `screen(html)` | Replace `APP` innerHTML, then `translateTree(APP)`. Every view ends here. |
| `loading` | `loading()` | A spinner card. Call before an async fetch. |
| `get` | `get(path)` → Promise | REST GET (via `rawFetch`). |
| `rawFetch` | `rawFetch(path, {method, body})` | The one HTTP client. `body` is auto-JSON. Rejects with `err.message` on !ok. |
| `write` | `write(path, method, body, label)` | Write that **queues offline** (IndexedDB) and replays. Use for user writes; `label` shows in the queue. |
| `field` | `field(name, label, value, type, wide)` | *(item-form local)* a labelled input `#f-<name>`. Note: signature differs from other screens — check scope. |
| `btn` | `btn(label, ic, attrs, variant)` | A `<button>`. `variant` = `primary`/`danger`/… `attrs` is a raw string (e.g. `'id="x" data-y="1"'`). |
| `linkBtn` | `linkBtn(label, ic, href, variant)` | An `<a>` styled as a button. |
| `sectionLabel` | `sectionLabel(text)` | A card section heading. |
| `emptyState` | `emptyState(title, sub)` | The empty-list placeholder. |
| `icon` | `icon(name, size)` | Inline SVG from `ICON_PATHS`. Add new icons there. |
| `money` / `fmt` | `money(n)` / `fmt(n)` | Currency / plain number formatting. |
| `esc` | `esc(str)` | HTML-escape. **Always** escape interpolated data. |
| `toast` | `toast(msg, kind)` | Transient notice. `kind='warn'` for errors. |
| `go` | `go(hash)` | Navigate (`location.hash = hash`). |
| `val` | `val(id)` | Trimmed value of `#id`, or `''`. |
| `debounce` | `debounce(fn, ms)` | For search inputs. |
| `canWrite`/`canManage`/`isAdmin` | — | UI permission gates (server also enforces). |
| `translateTree` | `translateTree(root)` | Walks text nodes + `placeholder/title/aria-label`, replacing any that **exactly** match an i18n key. |

**Routing:** `router()` calls `parseHash()` → `{ path, query }`, then a chain of `if (r.path === '/x')` → `viewX()`. Add a route there. `activeKey(path)` decides which nav entry highlights.

**i18n in views:** you can either wrap a string in `t('…')` **or** write the English literal directly — `translateTree` (run by `screen()`) translates exact text-node matches. Either way the **English string must exist as a key** in `class-i18n.php`. New strings → add the key + BG value.

**Closures — the #1 source of my bugs here:** view helpers are often defined as **siblings outside** the `.then(function(r){ var i = … })` callback, so they only see per-request data (`i`) if it is **passed in as a parameter**. When you add `i.foo` to a helper, confirm `i` is actually in that helper's scope. See §10.

---

## 6. CSS conventions

- All classes are `vgc-sm-*`. **Grep before you name a new class** — reusing an existing name silently inherits its rules (this bit me: `.vgc-sm-stat` collision, `.vgc-sm-ov` didn't exist). 
- Form layout: `.vgc-sm-formgrid` (2-col) wrapping `.vgc-sm-field` (`<label><span>caption</span><input/></label>`); `.vgc-sm-field--row` for a checkbox row; `.vgc-sm-field--wide` spans both columns.
- Line-item grids share **one template** between the header row and the data rows so captions can't drift: `.vgc-sm-oline` (orders), `.vgc-sm-pline` (purchases). Read-only cell = `.vgc-sm-of__ro`; per-field caption = `.vgc-sm-of__l`.
- Stat tiles: `.vgc-sm-statrow` (grid) + `.vgc-sm-stat` (caption `__l` on top, value `__v` under). Desktop column count is set inline via `--stat-cols` because the tile count varies.
- Desktop breakpoint is **900px**. Some form rules live inside `@media (min-width:900px)`.

---

## 7. Recipe: add a field to an item

The single most common task. Touch these, in order:

1. **Schema** — add the column to the items `CREATE TABLE` in `class-install.php`, and **bump `VGC_STOCK_MANAGER_DB_VERSION`** (dbDelta adds it in place).
2. **Whitelist** — add it to `VGC_SM_Repository::sanitize_item` (with the right cast/sanitiser).
3. **REST in** — add it to `item_input`'s `$fields` array in `class-rest-api.php`.
4. **REST out** — add it to `shape_item` (with any derived/computed siblings).
5. **Form render** — add the control in `viewItemForm` (usually in `pricingHtml`/the Classification group).
6. **Form save** — add it to the `body` object in the save handler.
7. **i18n** — add the label's English key + BG value in `class-i18n.php`.
8. **(optional) migration** — a one-time option-guarded backfill in `vgc-stock-manager.php`.
9. Lint (§9), then a **browser-harness render** of the form.

## 7b. Recipe: add a screen

1. Nav entry in `NAV_MAIN` (or `NAV_MANAGER`/`NAV_ADMIN`). Give it an `ic` that exists in `ICON_PATHS` (add one if not).
2. Title in the titles map; highlight in `activeKey`.
3. Route in `router()` → `viewX(r.query)`.
4. `viewX()` following the `loading()` → `get()` → `screen()` shape.
5. Back-links, i18n, then browser-harness render.

---

## 8. Release ritual (test mode = publish every change)

1. Bump the version in **three** places: header comment + `VGC_STOCK_MANAGER_VERSION` in `vgc-stock-manager.php`, and `Stable tag` in `readme.txt`. Add a `readme.txt` changelog entry.
2. Build the zip with **forward-slash paths** (`System.IO.Compression`, not `Compress-Archive` — it uses backslashes that break on Linux). The scratch `build.ps1` does this; it verifies every entry is forward-slashed under `vgc-stock-manager/`.
3. `gh release create vgc-stock-manager-<ver> _releases/<zip> --repo vgc-ltd-wp/vgc-plugin-updates …`
4. Update `plugins.json` in the `vgc-plugin-updates` repo (version, download_url, last_updated, prepend changelog HTML), commit, push.
5. **Re-pin `vgc-stock-manager-reference.md`** to the new version and copy it to that repo's `docs/`.
6. Verify: `curl` the **raw CDN** `plugins.json` shows the new version, and the release asset returns **200**. (Raw CDN can lag the API a few minutes.)
7. The site only sees it after the updater's 1-hour cache expires — hit `…/wp-admin/update-core.php?force-check=1` to see it now.

## 9. Verification (do this before every ship)

**Lint gauntlet:**
- `php -l` on **every** PHP file (a broken string literal takes the whole site down — this is not optional). `for f in $(find . -name '*.php'); do /c/xampp/php/php.exe -l "$f"; done`
- `node --check app/app.js`.
- Apostrophe/lexer safety on `class-i18n.php`/`class-help.php` via `token_get_all`.
- i18n dupes + coverage (a small script; only the pre-existing `Remove` dup is acceptable).

**`node --check` catches syntax, NOT scope/DOM/runtime bugs.** For any non-trivial `app.js` view change, **render it in a browser** (this has caught real, shipping bugs three+ times):
- A static HTML harness in the project root with the DOM shell (`#vgc-sm-app`, `#vgc-sm-nav`, `#vgc-sm-sidebar`, `#vgc-sm-toast`, `#vgc-sm-title`, `#vgc-sm-back`, `#vgc-sm-offline`), a `window.VGC_SM` boot object (`restUrl`, `nonce`, `perms:{write,manage,admin}`, `currency`, `strings:{}`, `user`, `level`, `logoutUrl`), a `window.fetch` stub returning mock JSON by URL, then `location.hash='#/…'` and `<script src="vgc-stock-manager/app/app.js">`.
- Serve via a temporary `.claude/launch.json` (`python -m http.server 8791`) + `preview_start`, drive with the `javascript_tool` (assert DOM/console — **screenshots time out; measure instead**), then delete the harness + launch.json.
- To find *why* something is wrong, stash state on `window` (`window.__x = …`) or capture `(new Error()).stack` and reload — that's how the arg-dropping wrapper was found.

---

## 10. Gotchas index (things that have actually bitten)

- **Helper out of scope for `i`.** A view helper defined outside the `.then` closure referencing `i` → "i is not defined", blank screen. Fix: pass `i` in. (1.20.0)
- **A wrapper that drops a new argument.** `viewItemForm` is reassigned by a barcode-prefill wrapper `function (id){ origItemForm(id) }`; adding a 2nd param (`query`) silently failed until the wrapper forwarded it. **When you add a parameter, grep for `X = function` / `var origX = X` wrappers.** (1.21.0)
- **CSS class-name collision.** New tiles reused `.vgc-sm-stat`, an orphan rule from a replaced component, and inherited flex layout. **Grep the class before naming.** (1.16.1)
- **`.vgc-sm-ov` didn't exist** — invented a class instead of the real `.vgc-sm-of__ro`. Verify classes exist.
- **Invented helper names** (`post`/`put`/`del_`/`dialog`/`today`) — the real ones are `rawFetch`/`confirm()`/`new Date().toISOString().slice(0,10)`. Check §5 before calling.
- **Translation said the opposite:** cost was labelled «Единична цена» (unit *price*) → users typed sale prices into the cost field. Now «Себестойност». Read the BG value, not just the key.
- **Status vocabulary drift:** orders use `'completed'`; I once wrote `'complete'` in purchases. Match the existing string.
- **Unescaped apostrophe** in a single-quoted PHP string in `class-help.php` took the site down (1.13.0). Every `'` inside single quotes must be `\'`; `php -l` catches it.
- **Printing re-rendered the page:** the desktop media-query `change` listener fired against the A4 paper box. Guard with a `printing` flag.
- **`Compress-Archive`** writes backslash paths that break the plugin on Linux — build zips via `System.IO.Compression`.
- **`cd "path" && cmd`** in Bash triggers a permission prompt every time; use absolute paths instead (67% of prompts came from this).

---

## 11. Refactor backlog (honest assessment)

The app works and is only tested on staging, so **a big-bang refactor is high-risk for low immediate payoff** — I am deliberately not doing one. These are the *incremental, low-risk* wins to take when nearby, in rough priority:

1. **Regenerate the codemap after structural edits** (`python vgc-stock-manager-codemap.py`) — near-zero cost, keeps navigation fast. (This is the real speed unlock.)
2. **Extract one shared money helper.** `strip_vat`/net↔gross/margin logic is duplicated across `class-orders.php`, `class-purchases.php`, and the item form JS. A shared PHP trait/util and one JS helper would remove ~4 copies. Do it the next time one of them changes.
3. ~~**Split `class-rest-api.php` (3.2k lines)** by resource.~~ **DONE (1.22.0)** — handlers moved into 9 resource traits under `includes/rest/`; the main class kept the route table + permission callbacks (~620 lines). Verified route-for-route identical (route-dump harness) and all 98 methods present with none extra (reflection harness). Scratch harnesses: `route-dump.php`, `reflect-check2.php`, `extract-traits.php`.
4. **`app.js` is one 5.4k-line IIFE.** A build-free split into several `<script>` files sharing one namespace object is *possible* but touches the frontend enqueue and the closure model — only worth it if it keeps growing. Not now.
5. **Kill dead code** as found (e.g. the `type` partner column is retained but unread since 1.18.0; `itemsState.kind` removed in 1.21.0). Grep-verify before deleting.

Whenever a gotcha recurs, add it to §10. Whenever a convention is discovered, add it to the relevant section. This file paying for itself = fewer of the bugs in §10 shipping.
