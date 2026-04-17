# Store Returns Guide

This guide explains how the store returns process works — from a customer requesting a return to the refund being issued and inventory being updated.

---

## The Return Flow

Every return goes through this process:

```
Step 1: Create Return (staff submits return request)
    |
Step 2: Approval (if required by policy)
    |
Step 3: Process Return (restock items + issue refund)
    |
Done: Return completed
```

---

## Step 1: Create a Return

When a customer wants to return items, staff creates a return request.

### What You Need

| Field | Required | Description |
|---|---|---|
| `sale_id` | Yes | The original sale the items are being returned from |
| `return_type` | Yes | Type of return (see below) |
| `reason` | Yes | Why the customer is returning |
| `reason_notes` | No | Additional details about the reason |
| `refund_method` | Yes | How the refund should be issued |
| `items` | Yes | List of items being returned (at least one) |

### Return Types

| Value | Meaning |
|---|---|
| `REFUND` | Customer wants their money back |
| `EXCHANGE` | Customer wants to swap for a different item |
| `STORE_CREDIT` | Customer wants store credit instead of cash |

### Return Reasons

| Value | When to Use |
|---|---|
| `DEFECTIVE` | Product has a fault or defect |
| `WRONG_ITEM` | Customer received the wrong item |
| `CUSTOMER_CHANGED_MIND` | Customer simply doesn't want it anymore |
| `EXPIRED` | Product has passed its expiry date |
| `DAMAGED_IN_TRANSIT` | Product was damaged during delivery |
| `OTHER` | Any other reason (explain in `reason_notes`) |

### Return Items

Each item in the return needs:

| Field | Required | Description |
|---|---|---|
| `sale_item_id` | Yes | ID of the original sale item being returned |
| `quantity_returned` | Yes | How many units to return (can be partial) |
| `condition` | Yes | What condition the item is in |
| `reason` | No | Per-item reason (optional) |

### Item Condition

This determines whether the item goes back to inventory or is written off:

| Value | Goes Back to Stock? | Meaning |
|---|---|---|
| `RESALABLE` | Yes | Item is in good condition, can be resold |
| `DAMAGED` | No — written off | Item is physically damaged |
| `EXPIRED` | No — written off | Item has passed its expiry date |
| `OPENED` | No — written off | Item packaging has been opened |
| `WRITE_OFF` | No — written off | General write-off (any other reason) |

> Only `RESALABLE` items are returned to sellable inventory. Everything else is recorded as a loss.

### What Happens When You Create a Return

The system automatically:

1. **Validates the sale** — checks it exists and isn't cancelled
2. **Validates each item** — confirms the item belongs to the sale and the quantity is available
3. **Prevents double returns** — checks how much was already returned for each item
4. **Finds the applicable return policy** — looks up the most specific policy for the product
5. **Enforces the policy:**
   - Checks the return window (rejects if expired)
   - Checks if the item is non-returnable (rejects if `return_window_days = 0`)
   - Checks expired items against the policy's `allow_expired_returns` setting
6. **Calculates the refund:**
   - Unit price from original sale x quantity returned
   - Minus restocking fee (from policy)
7. **Determines if approval is needed** (from policy settings)
8. **Creates the return** with status `PENDING` or `APPROVED`

### Example Request

```json
{
    "sale_id": "sale-abc-123",
    "return_type": "REFUND",
    "reason": "DEFECTIVE",
    "reason_notes": "Screen flickering after 3 days of use",
    "refund_method": "ORIGINAL_PAYMENT",
    "items": [
        {
            "sale_item_id": "si-item-456",
            "quantity_returned": 1,
            "condition": "DAMAGED",
            "reason": "Screen defect"
        }
    ]
}
```

### Partial Returns

You don't have to return everything from a sale. You can return:
- **Some items** — return 2 of 5 items from a sale
- **Partial quantities** — bought 10 units, return 3

```json
{
    "sale_id": "sale-abc-123",
    "return_type": "REFUND",
    "reason": "CUSTOMER_CHANGED_MIND",
    "refund_method": "CASH",
    "items": [
        {
            "sale_item_id": "si-item-001",
            "quantity_returned": 3,
            "condition": "RESALABLE"
        },
        {
            "sale_item_id": "si-item-002",
            "quantity_returned": 1,
            "condition": "DAMAGED"
        }
    ]
}
```

---

## Step 2: Approval (If Required)

If the return policy requires approval, the return is created with status `PENDING`.

### Who Can Approve?

- If the policy has an **approvers list** (e.g., `["manager@store.com", "admin@store.com"]`), only those users can approve or reject
- If no approvers list is set, anyone with the `store-returns-approve` permission can approve

### Approve a Return

```json
{
    "return_id": "ret-xyz-789",
    "notes": "Verified defect, approved for refund"
}
```

Status changes: `PENDING` → `APPROVED`

### Reject a Return

```json
{
    "return_id": "ret-xyz-789",
    "rejection_reason": "Item was damaged by customer, not a manufacturing defect"
}
```

Status changes: `PENDING` → `REJECTED` (process ends here, no refund issued)

### Auto-Approval

If the policy says `approval_required: false`, or the refund amount is below the threshold, the return skips this step entirely and goes straight to `APPROVED`.

---

## Step 3: Process the Return

Once a return is `APPROVED`, staff processes it. This is when the real work happens.

```json
{
    "return_id": "ret-xyz-789",
    "notes": "Item received back, refund issued as cash"
}
```

### What Happens During Processing

For **each return item**, the system does one of two things:

**If the item is RESALABLE:**
```
Item goes back to inventory:
  ├── Batch quantity restored (batch_locations.qty + quantity_returned)
  ├── Store product quantity restored (store_products.current_qty + quantity_returned)
  └── Product movement recorded: IN, reason: 'RETURN'
```

**If the item is DAMAGED / EXPIRED / OPENED / WRITE_OFF:**
```
Item is written off (NOT restocked):
  ├── Product movement recorded: IN, reason: 'RETURN'
  └── Product movement recorded: OUT, reason: 'WRITE_OFF_DAMAGED' (or EXPIRED, etc.)
  
  Store quantity does NOT change. The item is a loss.
```

### The Refund

The refund amount is recorded on the return itself. The original sale stays untouched:

```
Sale:    PAID ($500) → stays PAID (not modified)
Return:  COMPLETED (refund: $450, restocking fee: $50)
```

The system records the refund. The actual cash handover (giving money back to the customer) happens outside the system — the cashier handles it.

Status changes: `APPROVED` → `COMPLETED`

---

## Complete Example

**Scenario:** Customer bought a Samsung Galaxy case ($50) and a screen protector ($15) on January 1st. On January 5th, they want to return the case because it's the wrong size.

### Step 1: Staff creates the return
```json
{
    "sale_id": "sale-001",
    "return_type": "REFUND",
    "reason": "WRONG_ITEM",
    "reason_notes": "Case doesn't fit customer's phone model",
    "refund_method": "CASH",
    "items": [
        {
            "sale_item_id": "si-case-001",
            "quantity_returned": 1,
            "condition": "RESALABLE"
        }
    ]
}
```

### System processes:
```
1. Sale exists, not cancelled                                    ✓
2. Sale item "si-case-001" belongs to sale, qty available        ✓
3. Not already returned                                          ✓
4. Policy found: "Standard Return Policy" (14-day window, 0% fee)
5. Return window: Jan 1 + 14 days = Jan 15. Today is Jan 5      ✓ (within window)
6. Refund calculation: $50 - 0% fee = $50
7. Approval: not required by policy
8. Return created: RET-0001, status: APPROVED
```

### Step 2: Approval skipped (not required)

### Step 3: Staff processes the return
```
Processing RET-0001:
  ├── Item: Samsung Galaxy Case, qty: 1, condition: RESALABLE
  │   ├── Batch quantity: +1
  │   ├── Store product quantity: +1
  │   └── Movement: IN, reason: RETURN
  │
  └── Refund: $50 recorded on RET-0001
      Sale stays PAID ($65 total, untouched)
```

### Result:
```
Return RET-0001: COMPLETED
  - Refund: $50
  - Item restocked: 1x Samsung Galaxy Case
  - Sale: still PAID ($65)
```

Cashier gives the customer $50 back.

---

## What Happens to the Money?

| Scenario | Customer Gets | Item Goes To | Business Impact |
|---|---|---|---|
| Item is RESALABLE | Refund minus restocking fee | Back to inventory | No loss (item can be resold) |
| Item is EXPIRED | Refund minus restocking fee | Written off | Loss = refund + cost of goods |
| Item is DAMAGED | Refund minus restocking fee | Written off | Loss = refund + cost of goods |
| Item is OPENED | Refund minus restocking fee | Written off | Loss = refund + cost of goods |
| Policy says non-returnable | Nothing | Stays with customer | No loss (return rejected) |
| Return window expired | Nothing | Stays with customer | No loss (return rejected) |

> The customer always gets their refund (minus restocking fee) regardless of item condition. The item condition only affects whether it goes back to sellable inventory or is written off as a loss.

---

## Return Statuses

| Status | Meaning | What Can Happen Next |
|---|---|---|
| `PENDING` | Waiting for manager approval | Can be approved or rejected |
| `APPROVED` | Approved, ready to be processed | Can be processed |
| `REJECTED` | Return denied | Nothing — process ends |
| `COMPLETED` | Processed, refund issued, inventory updated | Nothing — process ends |

```
PENDING ──→ APPROVED ──→ COMPLETED
   │
   └──→ REJECTED
```

---

## Preventing Abuse

The system has built-in protections:

### Double Return Prevention
```
Sale: 10 units of Product A
Return 1: 3 units returned
Return 2: Customer tries to return 8 more
System: REJECTED — "Only 7 available (sold: 10, already returned: 3)"
```

### Return Window Enforcement
```
Sale date: Jan 1
Policy: 7-day window
Today: Jan 10
System: REJECTED — "Return window has expired. Deadline was Jan 8"
```

### Non-Returnable Items
```
Product: Earphones
Policy: return_window_days = 0
System: REJECTED — "This item is non-returnable"
```

### Cancelled Sale Protection
```
Sale status: CANCELLED
System: REJECTED — "Cannot return items from a cancelled sale"
```

### Authorized Approvers Only
```
Policy approvers: ["manager@store.com"]
User trying to approve: "cashier@store.com"
System: REJECTED — "You are not an authorized approver"
```

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/store-returns/add` | Create a return request |
| `PUT` | `/api/v1/store-returns/approve` | Approve a pending return |
| `PUT` | `/api/v1/store-returns/reject` | Reject a pending return |
| `PUT` | `/api/v1/store-returns/process` | Process an approved return |
| `GET` | `/api/v1/store-returns/get?return_id=` | Get a single return |
| `GET` | `/api/v1/store-returns/list` | List returns (with filters) |
| `GET` | `/api/v1/store-returns/statistics` | Get return statistics |

### List Filters

| Parameter | Description |
|---|---|
| `page` | Page number (default: 1) |
| `size` | Page size (default: 10, max: 100) |
| `status` | Filter by status: `PENDING`, `APPROVED`, `REJECTED`, `COMPLETED` |
| `sale_id` | Filter by original sale ID |

### Reports

| Endpoint | What It Shows |
|---|---|
| `GET /api/v1/reports/returns/summary` | Overall stats — return rate, totals, restocked vs written off |
| `GET /api/v1/reports/returns/detailed` | Individual return records with filters |
| `GET /api/v1/reports/returns/by-reason` | Returns grouped by reason with percentages |
| `GET /api/v1/reports/returns/by-product` | Which products get returned most and why |
| `GET /api/v1/reports/returns/write-off` | Inventory losses from returns (damaged, expired items) |
| `GET /api/v1/reports/returns/graphical` | Returns over time for charts |

---

## Key Rules to Remember

1. **Returns are separate from sales** — the original sale stays PAID, the return is its own record
2. **Only RESALABLE items go back to stock** — damaged, expired, opened items are written off
3. **The customer always gets their refund** — item condition affects inventory, not the refund
4. **Restocking fees are deducted from the refund** — configured per policy
5. **Partial returns are supported** — return some items or partial quantities from a sale
6. **Double returns are blocked** — the system tracks what's already been returned per sale item
7. **Return window is enforced automatically** — based on sale date + policy's return_window_days
8. **Approvers are per-policy** — different policies can have different approvers
9. **The return tracks everything** — who created, approved, rejected, processed it, and when
