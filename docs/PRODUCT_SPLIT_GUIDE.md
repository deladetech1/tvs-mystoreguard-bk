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

## Endpoints

All under `/api/v1/products`. Require `permission-msg-products-split`.

### `POST /products/split`
```jsonc
{
  "source_product_id": "prd_pole",
  "source_qty_taken": 5,          // take 5 poles
  "divisor": 2,                   // each becomes 2 -> 10 units total
  "source_scope": "STORE",        // STORE (default) | WAREHOUSE | PRODUCT
  "price_mode": "AUTO",           // or "MANUAL"
  "unit_selling_price": null,     // required when price_mode = MANUAL
  "unit_cost_price": null,        // optional override

  "destination": "NEW",           // "NEW" or "EXISTING"

  // when destination = "EXISTING":
  "destination_product_id": null,

  // when destination = "NEW":
  "new_product_name": "Half Pole (10ft)",
  "new_product_sku": null,
  "new_product_bar_code": null,
  "new_product_description": null,
  "metadata_ids": [],

  // optional batch details (default to the source batch's values):
  "unit_of_measure_id": null,
  "supplier_id": null,
  "size": null,
  "expire_date": null
}
```
Returns the split record (source/derived product names, derived batch number, per-unit
prices, consumed source batches).

### `PUT /products/reverse-split`
```json
{ "split_id": "spl_xxx" }
```
Voids the derived batch and returns the taken quantity to the source. **Only allowed while
the derived batch is untouched** (none of the split units distributed to a location or
sold).

### `GET /products/splits`
Query: `source_product_id?`, `status?` (`ACTIVE`/`REVERSED`), `page`, `size`.

### `GET /products/split-detail`
Query: `split_id`.

## Notes

- For `STORE`/`WAREHOUSE` splits, the location is the caller's current location. To split
  warehouse stock, call from a warehouse context with `source_scope: "WAREHOUSE"`.
- Reversal requires the derived units to be fully intact (none sold or moved). For location
  splits the derived batch must still hold the full `derived_qty` on the shelf.
