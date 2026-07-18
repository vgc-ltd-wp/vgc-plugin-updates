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
- [ ] Orders/Purchases lists, Order, Purchase, Statement, Partner, Partners list (Phase 2)
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
