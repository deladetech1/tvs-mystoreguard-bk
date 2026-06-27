# Product Split (Break-Bulk) Guide

Split one product into smaller, individually-priced units. Example: a **GHc 200 pole**
with **50 pieces** in stock. A customer wants half a pole. You take some pieces off the
pole and break each one into 2 (or 3, 4, …), giving you smaller units priced at GHc 100
(or 66.67, 50, …) each.

The smaller units can be added to an **existing product** (as a new batch) or land as a
**brand-new product**.

## How it works

- `derived_qty = source_qty_taken × divisor`.
- Stock is taken from the source product **FIFO** (oldest first), logging `OUT`
  (`SPLIT_OUT`) movements.
- A new **batch** of `derived_qty` units is created on the destination product, logging an
  `IN` (`SPLIT_IN`) movement.
- A row in `msg_product_splits` records the lineage so the split can be **reversed**.

### Where the stock comes from — `source_scope`

The customer is usually standing in a **store**, so by default the split works on that
location's shelf stock. `source_scope` selects the pool:

| `source_scope` | Takes from | Lands the new units |
|----------------|-----------|---------------------|
| `STORE` *(default)* | shelf stock at the current store (`batch_locations` + `store_products.current_qty`) | back at the same store |
| `WAREHOUSE` | shelf stock at the current warehouse (`batch_locations` + `warehouse_products.current_qty`) | back at the same warehouse |
| `PRODUCT` | the unallocated purchase-batch pool (`qty_remaining`), before distribution | the pool |

For `STORE`/`WAREHOUSE` the location is the caller's current location (from the auth
context), exactly like the store/warehouse product endpoints. So splitting the GHc 200 pole
at a store reduces that store's pole count and adds the new half-poles to the same store —
ready to sell immediately.

### Pricing

| Mode | Selling price per unit | Cost price per unit |
|------|------------------------|---------------------|
| `AUTO` | source selling ÷ divisor | source cost ÷ divisor |
| `MANUAL` | you provide `unit_selling_price` | `unit_cost_price` if given, else source cost ÷ divisor |

Prices are rounded to 2 dp (ROUND_HALF_UP). Note `200 ÷ 3 = 66.67`, so three units total
`200.01` — a 1-pesewa rounding artifact, which is expected.

## Setup

1. Create the table — see [`app/src/entities/products/product_splits.sql`](../app/src/entities/products/product_splits.sql).
2. Register the permission **`permission-msg-products-split`** in the trovesuite
   core-platform DB (same way other `permission-msg-products-*` rows are seeded) and grant
   it to the appropriate roles.

## Model: a Split (parent) has Items (lines)

A **split** is the operation you open; it holds one or more **items**, one per product you
broke up. Each item is independently reversible. The split header status is `ACTIVE`,
`PARTIALLY_REVERSED` (some items reversed), or `REVERSED` (all reversed). Two tables:
`msg_product_splits` (header) and `msg_product_split_items` (lines).

## Endpoints

All under `/api/v1/products`. Require `permission-msg-products-split`.
Full field/response shapes: see [PRODUCT_SPLIT_API_SCHEMAS.md](PRODUCT_SPLIT_API_SCHEMAS.md).

### `POST /products/split` — create a split with 1+ items (all-or-none)
One transaction: if any item fails, nothing is applied. `source_scope` applies to all items.
```jsonc
{
  "description": "Customer wanted halves",   // optional note for the whole split
  "source_scope": "STORE",                   // STORE (default) | WAREHOUSE | PRODUCT
  "items": [
    { "source_product_id": "prd_pole", "source_qty_taken": 5, "divisor": 2,
      "price_mode": "AUTO", "destination": "NEW", "new_product_name": "Half Pole" },
    { "source_product_id": "prd_curtain", "source_qty_taken": 2, "divisor": 2,
      "price_mode": "MANUAL", "unit_selling_price": 40,
      "destination": "EXISTING", "destination_product_id": "prd_half_curtain" }
  ]
}
```
Returns the `Split` with its `items`. Guard: 1..50 items.

### `PUT /products/reverse-split` — reverse a whole split
```json
{ "split_id": "spl_xxx" }
```
Reverses all still-active items (all-or-none). Returns the updated `Split`.

### `PUT /products/reverse-split-item` — reverse one product item (others stay)
```json
{ "item_id": "spli_curtain" }
```
Reverses just that item — e.g. undo the curtain, leave the pole. Returns the updated `Split`
(header becomes `PARTIALLY_REVERSED`, or `REVERSED` once all items are undone).

### `GET /products/splits`
Query: `status?`, `source_scope?`, `source_product_id?`, `page`, `size`. Returns headers with
their items.

### `GET /products/split-detail`
Query: `split_id`. Returns the split with its items.

### `GET /products/split-statistics`
Query: `source_scope?` (`STORE` default | `WAREHOUSE` | `PRODUCT`). Stats for one section
only, never mixed: STORE/WAREHOUSE use the caller's current location; PRODUCT is pool-level
(business-wide).

## Notes

- For `STORE`/`WAREHOUSE` splits, the location is the caller's current location. To split
  warehouse stock, call from a warehouse context with `source_scope: "WAREHOUSE"`.
- An item can be reversed only while its derived units are fully intact (none sold or moved).
  For location splits the derived batch must still hold the full `derived_qty` on the shelf.
