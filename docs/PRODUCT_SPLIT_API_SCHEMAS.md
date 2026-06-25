# Product Split — API Schemas (Frontend)

Base path: `/api/v1/products`. All endpoints require auth and the permission
`permission-msg-products-split` (read-only ones also accept `permission-msg-products-get`).
The store/warehouse **location is taken from the auth context** — it is never sent in the body.

---

## Response envelope (every endpoint)

```ts
type Respons<T> = {
  success: boolean;
  detail: string | null;        // human-readable message
  error: string | null;         // error code when success=false, else null
  status_code: number;          // 200, 400, 403, ...
  data: T[] | null;             // payload — ALWAYS an array (single results = 1-item array)
  pagination: {                 // present only on list endpoints, else null
    page: number;
    size: number;
    total: number;
    total_pages: number;
    has_next: boolean;
  } | null;
};
```

### Error codes you may get back (`error` field)
| code | meaning |
|------|---------|
| `VALIDATION_ERROR` | bad/missing input (see `detail`) |
| `NOT_FOUND` | source/destination product, supplier, UoM, or split not found |
| `INSUFFICIENT_STOCK` | not enough stock to take the requested quantity |
| `CANNOT_REVERSE` | some split units already sold/moved — reversal blocked |
| `ALREADY_REVERSED` | the split was already reversed |
| `BATCH_ROLLED_BACK` | a batch op failed; **nothing** was applied/reversed |
| `INTERNAL_ERROR` | unexpected server error |

---

## Enums

```ts
type SourceScope  = "PRODUCT" | "STORE" | "WAREHOUSE";  // default "STORE"
type PriceMode    = "AUTO" | "MANUAL";                  // default "AUTO"
type Destination  = "EXISTING" | "NEW";                 // required
type SplitStatus  = "ACTIVE" | "REVERSED";
```

---

## Core payload: `Split`
Returned by `POST /split`, `POST /split-batch`, `GET /splits`, `GET /split-detail`.

```ts
type SourceBatchConsumed = {
  batch_id: string;
  batch_number: string | null;
  batch_location_id: string | null;   // set only for STORE/WAREHOUSE splits
  qty_taken: number;
  cost_price: number | null;
  base_selling_price: number | null;
};

type Split = {
  id: string;
  tenant_id: string;
  org_id: string;
  bus_id: string;

  source_product_id: string;
  source_product_name: string | null;
  source_qty_taken: number;
  divisor: number;
  source_scope: SourceScope;
  location_type: "STORE" | "WAREHOUSE" | null;  // null for PRODUCT scope
  loc_id: string | null;                        // null for PRODUCT scope

  derived_product_id: string;
  derived_product_name: string | null;
  derived_batch_id: string;
  derived_batch_number: string | null;
  derived_qty: number;                          // = source_qty_taken * divisor

  unit_cost_price: number | null;
  unit_selling_price: number | null;
  price_mode: PriceMode;
  currency_id: string | null;
  description: string | null;          // optional note/reason
  split_batch_id: string | null;       // group id shared by items split together; null for single splits

  status: SplitStatus;
  source_batches: SourceBatchConsumed[];

  cdate: string;        // "YYYY-MM-DD"
  ctime: string;        // "HH:MM:SS"
  cdatetime: string;    // ISO datetime
  created_by: string | null;
  created_by_name: string | null;
  reversed_by: string | null;
  reversed_at: string | null;   // ISO datetime, set when status="REVERSED"
};
```

---

## 1. `POST /products/split` — split one item

Request:
```ts
type SplitRequest = {
  source_product_id: string;                 // required
  source_qty_taken: number;                  // required, > 0
  divisor: number;                           // required, >= 1
  source_scope?: SourceScope;                // default "STORE"
  description?: string | null;               // optional note/reason for this split
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
  unit_of_measure_id?: string | null;        // default: source batch's
  supplier_id?: string | null;               // default: source batch's
  size?: string | null;
  expire_date?: string | null;               // "YYYY-MM-DD"
};
```
Response: `Respons<Split>` (data = 1-item array).

Conditional rules (server-enforced):
- `price_mode="MANUAL"` ⇒ `unit_selling_price` required
- `destination="EXISTING"` ⇒ `destination_product_id` required
- `destination="NEW"` ⇒ `new_product_name` required

---

## 2. `POST /products/split-batch` — split many (all-or-none)

Request:
```ts
type SplitBatchRequest = { splits: SplitRequest[] };  // 1..50 items
```
Response: `Respons<Split>` (data = one `Split` per item).
If any item fails the whole batch is rolled back: `success=false`, `error="BATCH_ROLLED_BACK"`, `data=null`.

---

## 3. `PUT /products/reverse-split` — reverse one

Request:
```ts
type ReverseSplitRequest = { split_id: string };
```
Response: `Respons<{ split_id: string; message: string }>`.

---

## 4. `PUT /products/reverse-splits` — reverse one / some / all (all-or-none)

Request:
```ts
type ReverseSplitsRequest = { split_ids: string[] };  // 1..50; duplicates ignored
```
Response: `Respons<{ split_id: string; message: string }>` (one entry per reversed split).
If any cannot be reversed: `success=false`, `error="BATCH_ROLLED_BACK"`, nothing reversed.

Examples:
```json
{ "split_ids": ["spl_curtain"] }                  // only curtains, leave the pole
{ "split_ids": ["spl_pole", "spl_curtain"] }      // all of them
```

---

## 5. `GET /products/splits` — list (paginated)

Query params (all optional):
```ts
{
  source_product_id?: string;
  status?: SplitStatus;                 // "ACTIVE" | "REVERSED"
  source_scope?: SourceScope;           // "PRODUCT" | "STORE" | "WAREHOUSE"
  split_batch_id?: string;              // returns all splits done together in one /split-batch call
  page?: number;                        // default 1
  size?: number;                        // default 20, max 100
}
```
Response: `Respons<Split>` with `data: Split[]` AND `pagination` populated.

> **Open a whole batch:** the `POST /split-batch` response returns each `Split` with the
> same `split_batch_id`. To view that batch later, call
> `GET /products/splits?split_batch_id=<id>`. Each item is still its own record, so you can
> reverse any single one (`PUT /products/reverse-split`) or all of them
> (`PUT /products/reverse-splits` with all their `split_id`s).

---

## 6. `GET /products/split-detail` — one split

Query params:
```ts
{ split_id: string }   // required
```
Response: `Respons<Split>` (data = 1-item array).

---

## 7. `GET /products/split-statistics` — stats for current location

Query params: none (location from auth context).

Response: `Respons<SplitStatistics>`:
```ts
type SplitStatistics = {
  loc_id: string | null;

  // counts & health (all splits)
  total_splits: number;
  active_splits: number;
  reversed_splits: number;
  reversal_rate: number;          // 0–100

  splits_today: number;
  splits_last_7_days: number;
  splits_last_30_days: number;

  // quantity flow (ACTIVE splits)
  total_source_qty_taken: number;
  total_derived_qty: number;
  average_divisor: number;

  // money (ACTIVE splits)
  derived_selling_value: number;
  derived_cost_value: number;
  original_selling_value: number;
  rounding_drift: number;         // derived_selling_value - original_selling_value
};
```
Note: covers STORE/WAREHOUSE splits done at the current location; PRODUCT (pool) splits are not location-bound and are excluded here.

---

## Example: split request body
```json
{
  "source_product_id": "prd_pole",
  "source_qty_taken": 5,
  "divisor": 2,
  "source_scope": "STORE",
  "price_mode": "AUTO",
  "destination": "NEW",
  "new_product_name": "Half Pole"
}
```
