# Design Brief 2 — VGC Stock Manager (the second half)

**For:** Claude Design
**Deliverable:** a design pass over everything built **since** your first design — bringing it up to the quality and consistency of the screens you already designed.
**Status:** the app is fully built and in daily testing. This is a **redesign of existing, working UI**, not new concepts. Read the original **`vgc-stock-manager-design-brief.md`** first — its domain model, constraints, goals and "what we want back" all still hold. This document is the **delta**: the features that were added after your last pass and have only had *functional* design attention.

---

## 0. What changed since your last design

Your first pass delivered the **warm parchment + terracotta** system that's now in place: the token set (`:root`), the card/list/button vocabulary, the inline SVG icon set, dark mode, and a **desktop sidebar** (the old 44rem-column problem is solved — desktop now has a left sidebar + wide content, phone keeps bottom tabs). That system is the baseline. **Everything below should be improved *within* it, staying consistent — not replaced.**

Since then the app roughly **doubled**. It grew from "make things and track stock" into a full **trade ledger**: who we sell to and buy from, on what terms, with money owed both ways. None of the following was in your first brief, and all of it was built prioritising *correctness* over *design* — it works, it's coherent, but it hasn't been designed the way the first half was.

The new surface, grouped:

- **Partners & the money** — partners (customers *and* suppliers, same record), per-partner statements, price lists.
- **Two living documents** — **Orders** (we sell) and **Purchases** (we buy), each a mutable, always-editable sheet with line items, a payment trail, running totals and profit.
- **Consignment** — goods we place at partners, and goods we hold from makers; publishing held stock to the shop.
- **Stock notes** — nine immutable document types that move stock/consignment/money.
- **The physical store** — allocating stock to a brick-and-mortar shelf, and selling from it.
- **Item money, expanded** — three prices per item (manufacturing cost, retail, B2B) with live margins, plus a physical-store allocation, plus a product↔material role.
- **The Materials / Products split** — the sidebar's single "Items" became two entries; every item is now a *product for sale* or a *material*, shown with badges.
- **Admin** — a Settings hub with sub-tabs, a Team/roles screen, an in-app Translations editor, an Activity log, and a paginated "Pull from shop" importer.

---

## 1. The design system as it stands (improve within this)

**Tokens** (`:root` in `app/app.css`) — this is your palette in production; extend, don't discard:

```
surfaces  --vgc-bg #F5F1EA  --vgc-canvas #E8E1D5  --vgc-card #FFF  --vgc-subtle #FBF8F2  --vgc-sunken #F0EBE2
lines     --vgc-border #E6DFD3  --vgc-border-strong #D6CCBC  --vgc-divider #F0EBE2
ink       --vgc-ink #221F1A  --vgc-ink-2 #6A645A  --vgc-ink-3 #9C958A  --vgc-ink-4 #C4BBAC
brand     --vgc-brand #B65C22 (terracotta)  --vgc-brand-dark #8A4417  --vgc-brand-tint #F7ECE0
semantic  --vgc-danger #B42318 (+bg/border)  --vgc-ok #2E7048 (+bg)  --vgc-info #3F5A75 (+bg/border)
dark panel --vgc-panel #221F1A  --vgc-panel-ink #F5F1EA  --vgc-panel-muted #B9AF9F
radii/shadow  --vgc-r-card 12px  --vgc-r-ctl 9px  --vgc-shadow / --vgc-shadow-lg
layout    --vgc-sidebar-w 236px  --vgc-nav-h 64px    mono: ui-monospace stack
```

**Layout today:** desktop = sticky left **sidebar** (nav + category shortcuts + user) + wide content; phone = **bottom tab bar** + stacked cards. Content is in `.vgc-sm-card`s. Full-width forms use `.vgc-sm-formgrid` (2-col) of `.vgc-sm-field`s. Dark mode via `prefers-color-scheme` using the panel tokens.

**Icon set** (inline SVG, `ICON_PATHS` in app.js): home, box, gear, chart, scan, search, plus, minus, edit, trash, camera, receive, shop, settings, sync, warn, check, chev, close, filter, exportIcon, recipe, run, user, logout, image, back, beaker. Add to this set as needed (same 24×24, 2px stroke, `currentColor`).

---

## 2. New information architecture

**Sidebar (desktop), top to bottom:** Overview · **Products** · **Materials** · Produce · Reports · **Orders** · **Purchases** · **Stock notes** · **Partners** · **Out on consignment** · **Held stock** · Shop stock · Scan — then (manager) Categories, Import — then (admin) a **Settings** hub — then Help. Category shortcuts hang collapsibly under **Products**.

**Phone bottom tabs:** Overview · Products · Materials · Produce · Scan (the trade/admin screens are reachable but the phone bar can't hold them all — **this is a design question: what belongs on the phone at all?** Orders/Purchases/Statements are laptop tasks; the phone is the workshop).

**The nav grew from 6 items to ~15.** It needs grouping/hierarchy in the sidebar (e.g. *Catalogue* · *Trade* · *Stock* · *Admin*), and a real answer for the phone.

---

## 3. New screens — current state & what to improve

Ranked roughly by pain.

### 3.1 Orders & Purchases — the new "hard screens" (like the recipe editor was)
`/order/:id`, `/purchase/:id`. A **living document** you edit like a spreadsheet. Current structure is one long single-column stack of cards:
1. **Terms card** — partner/vendor, mode (pay-in-full / pay-as-sold, or buy / consignment), dates (ordered/sent/received), payment terms, transport + who pays, VAT-inclusive toggle, note. A `.vgc-sm-formgrid`.
2. **Lines** — a dense CSS-grid table (`.vgc-sm-oline` for orders = 13 columns: item, ordered, sent, sold, returned, out, price, cost, VAT, margin, note, "display" flag, remove; `.vgc-sm-pline` for purchases = item, ordered, received, sold, returned, cost, VAT, markup%, sell price, note, remove). One template shared by the header row and every line so captions stay aligned; on narrow screens the row reflows to a 2–4 col block with a label per field. Orders also have a separate **display-pieces** section.
3. **Money** — running totals. **Inconsistent between the two: Orders render a plain flex row (net/VAT/total/paid/balance/margin); Purchases render `.vgc-sm-stat` tiles (cost/VAT/we-owe/paid/balance/retail/profit/held).** This should be **one designed "document summary" component**.
4. **Payments** — a table plus an add-a-payment row.
5. **Actions** — Save, Complete/Reopen, Delete.

**Problems:** (a) it's a long scroll that doesn't use desktop width — a master/summary layout (sticky totals? two columns?) would help; (b) the line grid is spreadsheet-dense and is the main interaction — it deserves the recipe-editor level of care, desktop **and** phone (editing a 13-column line on a phone is the open question); (c) money summaries must be unified; (d) the whole thing must still read as *calm* despite carrying a lot. Purchases additionally has an **inline "New item" panel** and a **markup→sell-price** calculator with a live "= margin X%" hint.

### 3.2 Partner detail — too many cards
`/partner/:id`. A partner is now a customer **and** a supplier. The page stacks: a name header, a KPI row (out-on-consignment, owes-you, held, you-owe), an action bar (Release stock, Sale report, Return, Take on consignment, New order, New purchase — 6+ buttons), then cards for **Our goods at this partner**, **Their goods we're holding**, **Orders**, **Purchases**, **Stock notes**, and a **Price list**. It's long and flat. Wants **hierarchy or tabs** (e.g. Overview · Orders · Purchases · Consignment · Prices), and a calmer action set.

### 3.3 Partner statement — good bones, needs polish
`/statement/:id`. Leads with a **stat-tile row** (`.vgc-sm-statrow`: Turnover ex-VAT, Billed incl-VAT, VAT, Paid, They-owe, Overdue, You-owe, Profit + margin%, Items sold, Documents, Average value) — caption on top, value under, colour only on state (overdue) or sign (profit). Then a period filter and a **merged timeline** (orders + notes) with Total/Paid/Balance columns. The stat tiles are the strongest new component; use them as the **reference** for a unified summary treatment elsewhere. Opportunity: the timeline table and the tiles could feel more like one report; print styling is basic.

### 3.4 The tag / badge system — currently ad-hoc (and recently bit us)
Across items and documents we now render many chips with `.vgc-sm-tag` + modifiers (`--product`, `--ok`, `--danger`, `--outline`): **role** (Product for sale / Material), **sourcing** (Made / Bought), **status** (Open / Completed / overdue), **channel** (Sellable), **mode** (Consignment / Bought). They look alike and their meanings overlap — a made item marked as a material once showed *both* "Material" and "Product" because two different concepts used the same words (now fixed by making sourcing say Made/Bought). **This needs a designed taxonomy:** what is a role vs a status vs an attribute, each with a consistent shape/colour/placement, so a glance is unambiguous.

### 3.5 Item form — classification has grown crowded again
`/item/:id/edit`. Your first brief already flagged the item form as too flat; it has since grown. The **Classification** group now holds: a **role** select ("This item is: a product for sale / a material"), a **sourcing** select ("How it's obtained: bought / made from a recipe"), unit, category, **Sellable** checkbox, **Stocked at the physical store** checkbox. The **Pricing** group grew from one cost to: VAT, a recipe-cost display with a **"enter cost manually"** toggle revealing a manual block, then a **Selling prices** sub-section — Retail (net + incl-VAT) and B2B (net + incl-VAT), each with a **live margin line** (`.vgc-sm-marginline`). It works but it's a lot of controls; wants grouping, hierarchy and progressive disclosure — the same medicine the recipe editor needs.

### 3.6 The item detail — new blocks bolted on
`/item/:id`. On top of the original hero + stock + cost + actions, it now also shows: the **role/sourcing badges** (see 3.4), a **price+margin strip** (Retail and B2B, each with net, incl-VAT, and margin), and — when the item is stocked at the store — a **Physical store card** (two stat tiles "at store / at workshop" + Distribute / Sold-at-store buttons, currently driven by `prompt()`). These are functional add-ons that haven't been composed into the page's hierarchy.

### 3.7 Stock notes — nine document types, one plain editor
`/notes`, `/note/:id`. A list, and an editor that changes shape by type (release, sale report, return, direct sale; take-in, purchase-in, buy-held, sold-held, return-out). Lines, dates, VAT, partner, destination. Immutable once issued (a cancel writes a reversing entry). The editor is a flat form; the nine types could use clearer framing so the operator knows what each does (there's an in-app wiki, but the editor itself is bare).

### 3.8 Consignment views — plain tables
`/outstanding` (our goods at partners) and `/held` (goods we hold from makers): item tables with quantities and values, links to publish held stock to the shop. Functional tables; low design priority but should share the table/summary language of the rest.

### 3.9 Admin — Settings hub, Team, Translations, Activity log
`/settings` is a hub with **sub-tabs** (`.vgc-sm-subtabs`) for connection, translations, team, etc. `/team` lists users with a level dropdown (Viewer/Operator/Manager). `/translations` is a long list of string + edit-field rows. `/audit` is the activity log. All are functional-plain; the sub-tab pattern is new and could be the model for taming the partner detail (3.2).

### 3.10 Pull from shop
`/pull`. A paginated (20/page, Prev/Next), filterable (category, product type) list of shop products with checkboxes and an "Import as" control; selections persist across pages. Works; the pagination + selection UI is bespoke and could align with the rest.

---

## 4. New components introduced (needing specs, all states)

Map designs onto these (they exist in `app.css`); give each the full state matrix (default / hover / focus-visible / active / disabled / loading / error / empty, plus the domain states noted):

- **Line-item grid** — `.vgc-sm-oline` (orders), `.vgc-sm-pline` (purchases): shared header+row grid template, per-field labels on narrow screens, `.vgc-sm-of` field + `.vgc-sm-of__l` caption + `.vgc-sm-of__ro` read-only cell + `.vgc-sm-of__chk` checkbox cell. **The most important new component.** Desktop density vs phone editability is the core question.
- **Stat tiles** — `.vgc-sm-statrow` (grid, `--stat-cols` set inline) + `.vgc-sm-stat` (`__l` caption on top, `__v` value under, `__q` qualifier, `__d` detail, `--hero` / `--good` / `--bad`). The reference for summaries.
- **Sub-tabs** — `.vgc-sm-subtabs` / `.vgc-sm-subtab`.
- **Tags / badges** — `.vgc-sm-tag` (+ `--product` `--ok` `--danger` `--outline`). Needs the taxonomy in 3.4.
- **Form grid** — `.vgc-sm-formgrid` + `.vgc-sm-field` (+ `--row` checkbox, `--wide` full-span). The main form primitive now.
- **Margin line** — `.vgc-sm-marginline` (live profit readout under a price input).
- **Payment trail** — the (unclassed) payments table + add-row on orders/purchases; deserves a component.
- **Document summary** — currently two different treatments (orders flex row vs purchases stat tiles); **make it one**.
- **FAB** — `.vgc-sm-fab` (mobile add button). **Split** — `.vgc-sm-split` (desktop 2-col).

---

## 5. Cross-cutting goals for this pass

1. **Bring the second half up to the first half.** Consistency is the headline — the trade screens should feel like the same product as the item/recipe screens you designed.
2. **A designed document layout** for Orders & Purchases — the new hard screens. Desktop should use its width (sticky summary? two-pane?); the line editor should be as considered as the recipe editor; the phone story for these must be explicit (view vs edit).
3. **One money-summary language.** Unify the order/purchase/statement/store totals into a single stat-tile-based treatment. Net / VAT / gross / paid / balance / margin should read the same everywhere.
4. **A coherent tag/badge/status taxonomy** (3.4) — the single most confusing thing in the new UI.
5. **Tame the long stacked screens** — partner detail (3.2) and the item form (3.5) — with hierarchy, sub-tabs or progressive disclosure. Reuse the sub-tab pattern.
6. **Number legibility, continued** — the first brief asked for a numeric language; the new screens are *full* of money (net/gross/VAT/margin/markup/paid/balance/owed-both-ways). Make the hierarchy of *what it costs / what they owe / what we make* unambiguous, tabular where columns align.
7. **Replace the `prompt()` interactions** (store distribute/sell) with real inline UI.
8. **Print** — Orders and stock notes print (A4 portrait); give the printed document a proper design.

## 6. What we want back (delta on the first brief)

The tokens and icon set already exist, so this pass is mostly **components + key new-screen designs**, not a fresh system:

1. **Component specs** for §4, all states, mapped to the existing classes.
2. **The tag/badge/status taxonomy** — a small, unambiguous system.
3. **Key screen designs, desktop + phone:**
   - **Order document** and **Purchase document** (the priority)
   - **Partner detail** (tamed) and **Partner statement**
   - **Item form** (classification + pricing, re-grouped) and **Item detail** (with the new blocks composed in)
   - **Stock note editor** (type-aware framing)
   - **Settings hub / Team** (as the model for sub-tab pages)
4. **The unified document-summary component.**
5. **Responsive strategy for the trade screens** — what Orders/Purchases/Statements become on a phone, and whether they belong in the bottom bar at all.
6. **Sidebar grouping** for the grown nav (~15 entries).
7. **An implementation note per change** — "CSS only" vs "needs markup change X in app.js" — as before; it drives how we ship.

## 7. Constraints (unchanged — see brief 1 §4)

Vanilla JS, string-concatenated `innerHTML`, hash-routed. One stylesheet (`app.css`) with custom properties. Self-hosted only (offline PWA — no CDNs/fonts/icon libs; inline SVG). Touch targets ≥ 44px. Offline/queued write states are real. Deliverable as **CSS + defined markup changes**. **This is a design pass, not a re-architecture** — don't change the flows or move data; if a flow is genuinely wrong, say so.

---

*Companion docs: the original `vgc-stock-manager-design-brief.md`; the developer `vgc-stock-manager-dev-guide.md` (conventions, the full class inventory, gotchas) and `vgc-stock-manager-codemap.md` (every screen → file + line).*
