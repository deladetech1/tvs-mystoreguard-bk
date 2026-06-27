# Product Split — API Schemas (Frontend)

Base path: `/api/v1/products`. All endpoints require auth and the permission
`permission-msg-products-split` (read-only ones also accept `permission-msg-products-get`).
The store/warehouse **location is taken from the auth context** — never sent in the body.

## Model: a Split has many Items

A **Split** is the parent you open. It contains one or more **Items** — one per product you
broke up (pole, curtain, …). Each item is independently reversible; the split header shows
overall status (`ACTIVE` / `PARTIALLY_REVERSED` / `REVERSED`).

```
Split  S-0007  "Counter break-bulk"  Store A  [PARTIALLY_REVERSED]
├─ item: Pole    → 5 ÷2 → 10 Half Poles    [ACTIVE]
└─ item: Curtain → 2 ÷2 → 4 Half Curtains  [REVERSED]
```

---

## Response envelope (every endpoint)
```ts
type Respons<T> = {
  success: boolean;
  detail: string | null;
  error: string | null;          // error code when success=false, else null
  status_code: number;
  data: T[] | null;              // payload — ALWAYS an array (single result = 1-item array)
  pagination: { page: number; size: number; total: number; total_pages: number; has_next: boolean } | null;
};
```
Error codes: `VALIDATION_ERROR`, `NOT_FOUND`, `INSUFFICIENT_STOCK`, `CANNOT_REVERSE`,
`ALREADY_REVERSED`, `INTERNAL_ERROR`.

## Enums
```ts
type SourceScope   = "PRODUCT" | "STORE" | "WAREHOUSE";  // default "STORE"
type PriceMode     = "AUTO" | "MANUAL";                  // default "AUTO"
type Destination   = "EXISTING" | "NEW";                 // required per item
type ItemStatus    = "ACTIVE" | "REVERSED";
type SplitStatus   = "ACTIVE" | "PARTIALLY_REVERSED" | "REVERSED";
```

---

## Payload types

```ts
type SourceBatchConsumed = {
  batch_id: string;
  batch_number: string | null;
  batch_location_id: string | null;   // set only for STORE/WAREHOUSE splits
  qty_taken: number;
  cost_price: number | null;
  base_selling_price: number | null;
};

type SplitItem = {
  id: string;
  split_id: string;
  tenant_id: string; org_id: string; bus_id: string;
  source_product_id: string;
  source_product_name: string | null;
  source_qty_taken: number;
  divisor: number;
  derived_product_id: string;
  derived_product_name: string | null;
  derived_batch_id: string;
  derived_batch_number: string | null;
  derived_qty: number;                 // source_qty_taken * divisor
  unit_cost_price: number | null;
  unit_selling_price: number | null;
  price_mode: PriceMode;
  currency_id: string | null;
  status: ItemStatus;
  source_batches: SourceBatchConsumed[];
  cdate: string; ctime: string; cdatetime: string;
  created_by: string | null;
  reversed_by: string | null;
  reversed_at: string | null;
};

type Split = {                          // the parent you open
  id: string;
  split_number: string | null;          // e.g. "SPL-20260625-001"
  tenant_id: string; org_id: string; bus_id: string;
  description: string | null;
  source_scope: SourceScope;
  location_type: "STORE" | "WAREHOUSE" | null;  // null for PRODUCT scope
  loc_id: string | null;
  status: SplitStatus;
  item_count: number;
  items: SplitItem[];                   // the product lines
  cdate: string; ctime: string; cdatetime: string;
  created_by: string | null;
  created_by_name: string | null;
  reversed_by: string | null;
  reversed_at: string | null;
};
```

---

## 1. `POST /products/split` — create a split (one or more items, all-or-none)

```ts
type SplitItemRequest = {
  source_product_id: string;                 // required
  source_qty_taken: number;                  // required, > 0
  divisor: number;                           // required, >= 1
  price_mode?: PriceMode;                    // default "AUTO"
  unit_selling_price?: number | null;        // required if price_mode="MANUAL"
  unit_cost_price?: number | null;           // optional override; else source cost / divisor
  destination: Destination;                  // required
  destination_product_id?: string | null;    // required if destination="EXISTING"
  new_product_name?: string | null;          // required if destination="NEW"
  new_product_sku?: string | null;
  new_product_bar_code?: string | null;
  new_product_description?: string | null;
  metadata_ids?: string[];                   // default []
  unit_of_measure_id?: string | null;
  supplier_id?: string | null;
  size?: string | null;
  expire_date?: string | null;               // "YYYY-MM-DD"
};

type CreateSplitRequest = {
  description?: string | null;               // note/reason for the whole split
  source_scope?: SourceScope;                // default "STORE", applies to every item
  items: SplitItemRequest[];                 // 1..50
};
```
Response: `Respons<Split>` (the created split, with its items). All-or-none: if any item
fails, nothing is applied (`success=false`, `data=null`).

## 2. `PUT /products/reverse-split` — reverse a whole split
```ts
{ split_id: string }
```
Reverses all still-active items (all-or-none). Response: `Respons<Split>` (the updated split).

## 3. `PUT /products/reverse-split-item` — reverse one product item
```ts
{ item_id: string }
```
Reverses a single item; the others stay. Response: `Respons<Split>` (the updated parent
split — its `status` becomes `PARTIALLY_REVERSED` or `REVERSED`).

## 4. `GET /products/splits` — list splits (paginated)
Query (all optional):
```ts
{
  status?: SplitStatus;
  source_scope?: SourceScope;
  source_product_id?: string;   // splits that include this source product
  page?: number;                // default 1
  size?: number;                // default 20, max 100
}
```
Response: `Respons<Split>` with `data: Split[]` (each with its items) AND `pagination`.

## 5. `GET /products/split-detail` — one split
Query: `{ split_id: string }` → `Respons<Split>`.

## 6. `GET /products/split-statistics` — stats for one section
Query: `source_scope?` — `STORE` (default), `WAREHOUSE`, or `PRODUCT`. Stats are scoped to
that section only and are **never mixed** across sections. For `STORE`/`WAREHOUSE` the
location comes from the auth context; `PRODUCT` is pool-level (business-wide, `loc_id` null).
Call once per section to populate the Store / Warehouse / Product panels. Response:
`Respons<SplitStatistics>`:
```ts
type SplitStatistics = {
  source_scope: "STORE" | "WAREHOUSE" | "PRODUCT";
  loc_id: string | null;  // null for PRODUCT
  total_splits: number; active_splits: number; reversed_splits: number;
  partially_reversed_splits: number; reversal_rate: number;  // 0–100
  splits_today: number; splits_last_7_days: number; splits_last_30_days: number;
  total_items: number; total_source_qty_taken: number; total_derived_qty: number; average_divisor: number;
  derived_selling_value: number; derived_cost_value: number;
  original_selling_value: number; rounding_drift: number;
};
```

---

## Example: create a split with two products
```json
{
  "description": "Customer wanted halves",
  "source_scope": "STORE",
  "items": [
    { "source_product_id": "prd_pole",    "source_qty_taken": 5, "divisor": 2,
      "price_mode": "AUTO", "destination": "NEW", "new_product_name": "Half Pole" },
    { "source_product_id": "prd_curtain", "source_qty_taken": 2, "divisor": 2,
      "price_mode": "AUTO", "destination": "NEW", "new_product_name": "Half Curtain" }
  ]
}
```
The response `Split` has `items: [pole-item, curtain-item]`. To reverse only the curtain
later: `PUT /products/reverse-split-item { "item_id": "<curtain item id>" }` — the pole stays.
