# VGC Stock Manager — Component Map (Dev Mode)

This is the address book for the app's UI. Turn on **Dev mode** and every tagged
panel shows its **component ID** as a small badge above it; use those IDs to point
at exactly what you want changed ("in `item-header`, make the image larger").

## Using dev mode

- **Turn it on:** Settings → *Developer mode* → tick *Show component IDs on every panel*.
  It's a per-user preference, saved to your account (server-side), so it persists across
  sessions and follows your login — and it never affects other users' view.
- **Read the badge:** each tagged panel gets a small brand-coloured ID badge at its
  **top-right** corner and a dashed outline around it.
- **Comment & copy:** click the badge — a small note box opens. Type what you'd like
  changed (optional), then hit **Copy**. It puts a ready-to-send line on your clipboard —
  `` In `item-header`: make the image larger `` — which you paste straight into a message
  to the dev, who then knows the exact component *and* your comment. (Leave the note empty
  and Copy just gives you the `` `id` ``.)
- **Print:** badges, outlines and the popover never appear on printouts/PDFs.

## ID convention

`page-component`, all lowercase, hyphen-separated — the page first, then a short name
for the block. Examples: `item-header`, `order-summary`, `catalogue-toolbar`.

Only **panels** (cards / major sections) are tagged, not every small element — the
goal is a stable handle for each meaningful block, not clutter.

## Keeping this in sync

Tags live in `vgc-stock-manager/app/app.js` as `data-devid="…"`. After tagging a
screen, run `python vgc-stock-manager-components.py` — it lists every ID in the code
and flags any not yet described here.

## Coverage

Tagging is rolling out screen by screen. Status:

- [x] **Item detail** (Phase 1)
- [x] **Orders list, Purchases list, Partners list, Order, Purchase, Statement, Partner** (Phase 2)
- [ ] Catalogue, Item form, Recipe, Produce, Scan (Phase 3)
- [ ] Stock notes list/editor, Consignment out/held, Pull, Home, Shop (Phase 4)
- [ ] Settings, Team, Translations, Audit, Import, Login (Phase 5)

---

## Item detail — `#/item/{id}`

The single-item screen: its header, live stock and cost, store split, actions and
recent movements.

| ID | Panel | What it is |
|----|-------|------------|
| `item-header` | Header card | Thumbnail image, name, SKU and role/kind/category/sellable badges. |
| `item-stock` | Stock & cost card | "In stock" big number, packs/reorder/at-partners/held lines, manufacturing cost, the retail/B2B price-margin strip, and any shop/buildable banners. |
| `item-store` | Physical-store card | The store vs workshop split (only when the item is stocked at the store) and its distribute / sold-at-store actions. |
| `item-actions` | Actions card | Receive, Scrap, Set qty, Edit, Recipe, Produce, publish/unpublish, remove/restore. |
| `item-movements` | Recent movements card | The item's latest stock movements (in/out, note, date, signed quantity). |

---

## Orders list — `#/orders`

| ID | Panel | What it is |
|----|-------|------------|
| `orders-toolbar` | Toolbar | The intro line and the **New order** button. |
| `orders-list` | Orders table | Every order — number, partner, sent date, still-out, total, paid, balance, margin, status. |

## Purchases list — `#/purchases`

| ID | Panel | What it is |
|----|-------|------------|
| `purchases-toolbar` | Toolbar | The intro line and the **New purchase** button. |
| `purchases-list` | Purchases table | Every purchase — number, vendor, received date, mode, still-held, total, paid, balance, potential profit, status. |

## Partners list — `#/partners`

| ID | Panel | What it is |
|----|-------|------------|
| `partners-toolbar` | Toolbar | The **New partner** button. |
| `partners-list` | Partners list | Each partner — name, role, contact, and what they owe. |

## Order — `#/order/{id}`

| ID | Panel | What it is |
|----|-------|------------|
| `order-header` | Document header | Order number, partner link, status/mode badges. |
| `order-summary` | Summary tiles | Net, VAT, Total (hero), Paid, Balance, Margin, Still-out. |
| `order-details` | Details card | Partner, destination, dates, payment mode/terms, transport, "already sent". |
| `order-lines` | Lines card | The order's item lines (qty ordered/sent/sold/returned, price, cost, VAT, margin, note) + add-item. |
| `order-onloan` | Display-pieces card | Items sent on loan (never priced/billed) — the blue panel. |
| `order-sales` | Sales-from-sent card | Recorded consignment sales log + **Record sale** (consignment orders only). |
| `order-payments` | Payments card | The payment trail and the add-payment row. |
| `order-actions` | Note & actions card | Order note, Save, Complete/Reopen, Print, Delete. |

## Purchase — `#/purchase/{id}`

| ID | Panel | What it is |
|----|-------|------------|
| `purchase-header` | Document header | Purchase number, vendor link, status/mode badges. |
| `purchase-summary` | Summary tiles | Cost, VAT, We-owe-them (hero), Paid, Balance, Retail value, Potential profit, Still-held. |
| `purchase-details` | Vendor & terms card | Vendor, buy/consignment mode, dates, terms, transport, VAT-registered and cost-basis options, note. |
| `purchase-lines` | Lines card | The delivery's lines (qty, cost, VAT, markup, sell price, note) + bulk markup + add-item. |
| `purchase-payments` | Payments card | The payment trail and the add-payment row. |
| `purchase-actions` | Actions | Save, Complete/Reopen, Delete. |

## Statement — `#/statement/{id}`

| ID | Panel | What it is |
|----|-------|------------|
| `statement-filter` | Date-range card | From/To date filter and Apply/Clear. |
| `statement-tiles` | KPI tiles | Turnover (hero), Billed, VAT, Paid, They-owe, Profit, Items sold, Documents, Average value. |
| `statement-timeline` | Money-bearing notes table | Every money-bearing document in the period — date, number, type, due, total, paid, balances, status. |
| `statement-actions` | Actions | Print and CSV export. |

## Partner — `#/partner/{id}`

| ID | Panel | What it is |
|----|-------|------------|
| `partner-header` | Header | Avatar, name, role/VAT pills and VAT number. |
| `partner-summary` | Summary tiles | Out on consignment, Owes you, Held from them, You owe. |
| `partner-actions` | Action bar | New order/purchase, release/sale-report/return, statement, edit. |
| `partner-directory` | Locations & contacts card | Branches and the people you deal with. |
| `partner-outstanding` | Our goods at this partner | Items out on consignment there. |
| `partner-held` | Their goods we hold | Items we're holding from this maker. |
| `partner-orders` | Orders card | This partner's orders. |
| `partner-purchases` | Purchases card | Purchases from this partner. |
| `partner-notes` | Stock notes card | Stock notes involving this partner. |
| `partner-prices` | Price list card | Agreed per-item prices with this partner. |
