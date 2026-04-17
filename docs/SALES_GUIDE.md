# Store Sales Guide

This guide explains how the sales process works in the system — from verifying prices to completing a sale, handling payments, and tracking inventory.

---

## The Sales Flow

Every sale follows this process:

```
Step 1: Verify Prices (optional but recommended)
    |
Step 2: Create Sale (with items + payments)
    |
Step 3: Inventory Deducted (based on sale mode)
    |
Step 4: Payments Recorded
    |
Step 5: Promo / Gift Card / Affiliate Tracked
    |
Done: Sale completed
```

---

## Sale Modes

The system supports three ways to sell:

### INSTANT Mode (default)
**"Pay now, take now."**

| Payment State | Sale Status | Inventory |
|---|---|---|
| No payment | PARTIALLY_PAID | NOT deducted (on hold) |
| Partial payment | PARTIALLY_PAID | NOT deducted (on hold) |
| Full payment | PAID | Deducted (goods released) |

The customer must pay in full before goods are released. If they pay partially, the sale is on hold — inventory stays reserved but not deducted until fully paid.

### DEPOSIT Mode
**"Pay a deposit, pay the rest later."**

| Payment State | Sale Status | Inventory |
|---|---|---|
| No payment | ON_HOLD | NOT deducted |
| Deposit paid | PARTIALLY_PAID | NOT deducted |
| Full payment | PAID | Deducted (goods released) |

Works like INSTANT but explicitly designed for deposit scenarios. The customer puts down a deposit and pays the balance later. Inventory is only released when the full amount is paid.

### CREDIT Mode
**"Take now, pay later."**

| Payment State | Sale Status | Inventory |
|---|---|---|
| No payment | ON_HOLD | Deducted immediately |
| Partial payment | PARTIALLY_PAID | Already deducted |
| Full payment | PAID | Already deducted |

The customer takes the goods immediately. Payment is tracked separately — they can pay in installments over time. Inventory is deducted at the moment of sale, regardless of payment status.

---

## Step 1: Verify Prices (Pre-Checkout)

Before creating a sale, call the verify-price endpoint to get accurate prices with all rules and taxes applied.

**Endpoint:** `POST /api/v1/store-sales/verify-price`

### What It Calculates

For each item:

```
Base Selling Price (from batch)
    ↓
Actual Price (from product prices, with specificity: SKU > LOCATION > CATEGORY > GLOBAL)
    ↓
Price After Pricing Rule (discounts/markups applied — including quantity breaks)
    ↓
Price After Promo (if promo code provided — per-item eligibility checked)
    ↓
Price After Tax (inclusive extracted, exclusive added)
    ↓
Final Price × Quantity = Line Total
```

### What It Returns

```json
{
    "items": [
        {
            "product_id": "prod-001",
            "product_name": "Samsung Galaxy A15",
            "quantity": 2,
            "base_selling_price": 250.00,
            "actual_price": 250.00,
            "price_after_pricing_rule": 225.00,
            "price_after_tax": 236.25,
            "final_price": 236.25,
            "line_total": 472.50,
            "tax_amount": 11.25,
            "taxes_applied": [
                {"tax_name": "Sales Tax", "rate": 5.0, "is_inclusive": false, "amount": 11.25}
            ],
            "pricing_rule_applied": {
                "rule_name": "10% Phone Discount",
                "rule_type": "PERCENTAGE_DISCOUNT",
                "price_before": 250.00,
                "price_after": 225.00
            }
        }
    ],
    "business_name": "TechMart",
    "total_amount": 472.50,
    "total_tax_amount": 22.50,
    "promo_discount_amount": 0,
    "final_total_amount": 472.50,
    "gift_card_balance_available": 100.00,
    "gift_card_amount_usable": 100.00
}
```

The frontend uses these verified prices when creating the sale — no need to recalculate.

---

## Step 2: Create a Sale

**Endpoint:** `POST /api/v1/store-sales/add`

### Request Body

```json
{
    "sale_date": "2026-04-17",
    "sale_mode": "INSTANT",
    "customer_id": "cust-001",
    "description": "Walk-in sale",
    "items": [
        {
            "product_id": "prod-001",
            "quantity": 2,
            "base_selling_price": 250.00,
            "actual_price": 250.00,
            "price_after_pricing_rule": 225.00,
            "price_after_tax": 236.25,
            "final_price": 236.25,
            "tax_rate": 5.0,
            "tax_amount": 11.25,
            "is_inclusive": false,
            "taxes_applied": [
                {"tax_id": "tax-001", "tax_name": "Sales Tax", "rate": 5.0, "is_inclusive": false, "amount": 11.25}
            ]
        }
    ],
    "payments": [
        {
            "payment_method": "CASH",
            "paid_amount": 472.50
        }
    ],
    "promo_code": "SAVE10",
    "gift_card_code": "GC-ABC-123",
    "affiliate_code": "REF-JOHN",
    "verified_total_amount": 472.50,
    "verified_final_total_amount": 472.50
}
```

### What Happens Behind the Scenes

1. **Validates the customer** (if provided)
2. **Checks inventory** using FIFO batch selection (oldest stock first)
3. **Generates sale number** (e.g., SAL-20260417-001)
4. **Creates the sale record** with total amounts
5. **Creates sale items** with pricing details and batch references
6. **Deducts inventory** (based on sale mode — see above)
7. **Processes payments** and updates sale status
8. **Processes gift card** (deducts from balance, marks as USED if balance = 0)
9. **Records promo code usage** (increments counter, links to sale)
10. **Records affiliate referral** (creates referral + commission if fully paid)

---

## How FIFO Inventory Works

When selling, the system automatically picks stock from the **oldest batches first** (First-In, First-Out).

### Example

You have 3 batches of "Samsung Galaxy A15" at your store:

| Batch | Date Received | Qty Available | Cost Price |
|---|---|---|---|
| Batch 1 | Jan 15 | 5 units | $200 |
| Batch 2 | Feb 20 | 10 units | $210 |
| Batch 3 | Mar 10 | 8 units | $220 |

Customer buys **7 units**:

```
Batch 1: 5 units taken (all used up, 0 remaining)
Batch 2: 2 units taken (8 remaining)
Batch 3: 0 units taken (not needed)
Total: 7 units allocated
```

The system:
- Deducts 5 from Batch 1 in `batch_locations`
- Deducts 2 from Batch 2 in `batch_locations`
- Reduces `store_products.current_qty` by 7
- Creates 2 product movement records (one per batch, type: OUT, reason: SALE)

### Insufficient Stock

If inventory is not enough, the system returns a helpful error:

```
"Insufficient inventory for Samsung Galaxy A15.
 Need: 7, Available at this location: 3.
 Other store locations have: 12.
 Warehouse has: 25."
```

---

## Payment Methods

| Method | Value |
|---|---|
| Cash | `CASH` |
| Card | `CARD` |
| Bank Transfer | `BANK_TRANSFER` |
| Mobile Money | `MOBILE_MONEY` |
| Cheque | `CHEQUE` |
| Bitcoin | `BITCOIN` |
| Gift Card | `GIFT_CARD` |
| Other | `OTHERS` |

### Split Payments

A sale can have multiple payments with different methods:

```json
{
    "payments": [
        {"payment_method": "CASH", "paid_amount": 200.00},
        {"payment_method": "MOBILE_MONEY", "paid_amount": 150.00},
        {"payment_method": "GIFT_CARD", "paid_amount": 122.50}
    ]
}
```

### Adding Payments Later

For DEPOSIT or CREDIT sales, use the add payment endpoint:

**Endpoint:** `POST /api/v1/store-sales/payments/add`

```json
{
    "sale_id": "sale-001",
    "payment_method": "CASH",
    "payment_status": "SUCCESS",
    "paid_amount": 200.00
}
```

The system automatically recalculates the sale status:
- If total paid >= total amount → `PAID`
- If some paid but not all → `PARTIALLY_PAID`

---

## Sale Status Flow

```
                                    ┌─── PAID (fully paid)
                                    │
ON_HOLD ──→ PARTIALLY_PAID ────────┤
                                    │
                                    └─── OVERDUE (past deadline)

                    OR

ON_HOLD ──→ CANCELLED (sale voided)
```

| Status | Meaning |
|---|---|
| `ON_HOLD` | Sale created, awaiting payment or action |
| `PARTIALLY_PAID` | Some payment received, balance outstanding |
| `PAID` | Fully paid |
| `OVERDUE` | Payment deadline passed |
| `CANCELLED` | Sale cancelled, inventory restored |
| `QUEUED` | Sale is queued for processing |

---

## Promo Codes

If a promo code is provided during sale creation:

1. **Validates** the code (active, not expired, not over usage limit)
2. **Checks eligibility** per item (product, category, brand restrictions)
3. **Applies discount** to eligible items only:
   - `PERCENTAGE` — discount applied per unit
   - `FIXED_AMOUNT` — discount applied once to the line total
4. **Records usage** (links promo to sale and customer)
5. **Updates usage count** on the promo code

Items that don't match the promo's product/category restrictions get full price — no discount.

---

## Gift Cards

If a gift card code is provided:

1. **Validates** the card (ACTIVE status, has balance, not expired, valid for this location)
2. **Calculates usable amount**: min(gift card balance, remaining sale balance)
3. **Deducts from balance** on the gift card
4. **If balance reaches $0**: Card status changes to `USED`
5. **Creates transaction record** (type: REDEMPTION)
6. **Stores** gift_card_id and amount used on the sale

---

## Affiliate Tracking

If an affiliate code is provided:

1. **Validates** the affiliate (ACTIVE, location/product restrictions)
2. **Creates referral record** linked to the sale
3. **If sale is fully paid:**
   - Status: `CONVERTED`
   - Calculates commission (percentage or fixed amount)
   - Creates commission record
   - Updates affiliate stats (referrals, conversions, earnings)
4. **If sale is not fully paid:**
   - Status: `PENDING`
   - Commission calculated when sale is eventually fully paid

---

## Cancelling a Sale

**Endpoint:** `PUT /api/v1/store-sales/cancel`

When a sale is cancelled:

1. **Sale status** → `CANCELLED`
2. **Inventory restored:**
   - Batch quantities restored (each batch gets its units back)
   - Store product quantity restored
   - Reverse product movements created (type: IN, reason: SALE_CANCELLED)
3. **Payments remain on record** (for audit trail)

---

## Backdating Sales

For owners and admins, sales can be backdated using the `occurred_at` parameter:

```json
{
    "occurred_at": "2026-04-10T14:30:00",
    "items": [...],
    "payments": [...]
}
```

Accepts:
- ISO format: `"2026-04-10T14:30:00"`
- Date only: `"2026-04-10"`
- Natural language: `"10 April 2026"`

The sale number, date, and all timestamps will reflect the backdated date. Useful for recording offline sales or correcting past entries.

---

## Complete Example

**Scenario:** Customer buys 2x Samsung Galaxy A15 ($236.25 each after tax) and 1x Phone Case ($25.00) using a 10% promo code. Pays with cash and a gift card.

### Step 1: Verify prices
```
POST /store-sales/verify-price
Items: 2x Galaxy A15, 1x Phone Case
Promo: SAVE10 (10% off phones)
Gift Card: GC-ABC-123 (balance: $100)
```

Response:
```
Galaxy A15: $250 → 10% discount → $225 → 5% tax → $236.25 × 2 = $472.50
Phone Case: $25 → no discount (not a phone) → no tax → $25.00
Subtotal: $497.50
Promo discount: -$50.00 (10% of $500 on phones only)
Total: $447.50
Gift card usable: $100.00
```

### Step 2: Create sale
```
POST /store-sales/add
Sale mode: INSTANT
Payments: Cash $347.50 + Gift Card $100.00
```

### What happens:
```
1. Sale SAL-20260417-001 created
2. FIFO: Galaxy A15 deducted from oldest batch (2 units)
3. FIFO: Phone Case deducted from oldest batch (1 unit)
4. Store product qty: Galaxy A15 -2, Phone Case -1
5. Product movements: 3 records (OUT, reason: SALE)
6. Payments: $347.50 CASH + $100.00 GIFT_CARD = $447.50
7. Gift card: balance reduced by $100 (may become USED if was exactly $100)
8. Promo: SAVE10 usage recorded, counter incremented
9. Sale status: PAID (fully paid)
10. Fulfillment: FULFILLED (inventory released)
```

---

## API Endpoints

### Sales

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/store-sales/verify-price` | Verify prices before checkout |
| `POST` | `/store-sales/add` | Create a new sale |
| `GET` | `/store-sales/get?sale_id=` | Get a single sale |
| `GET` | `/store-sales/list` | List sales with filters |
| `PUT` | `/store-sales/update?sale_id=` | Update a sale |
| `PUT` | `/store-sales/cancel` | Cancel a sale (restores inventory) |
| `DELETE` | `/store-sales/delete` | Permanently delete a sale |
| `GET` | `/store-sales/statistics` | Sales statistics |

### Payments

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/store-sales/payments/add` | Add payment to existing sale |
| `PUT` | `/store-sales/payments/refund` | Refund a payment (soft delete) |

### List Filters

| Parameter | Description |
|---|---|
| `page` | Page number |
| `size` | Page size (max 100) |
| `customer_id` | Filter by customer |
| `status` | Filter by status |
| `sale_mode` | Filter by mode (INSTANT, DEPOSIT, CREDIT) |
| `fulfillment_status` | Filter by fulfillment |
| `from_date` / `to_date` | Date range |
| `search` | Search by sale number or customer name |

---

## Key Rules to Remember

1. **INSTANT mode** — goods released only when fully paid
2. **DEPOSIT mode** — same as INSTANT, designed for deposit workflows
3. **CREDIT mode** — goods released immediately, payment tracked separately
4. **FIFO** — oldest stock is always sold first (per batch receive date)
5. **Only ONE pricing rule applies** per product, but ALL matching taxes stack
6. **Promo codes** are checked per-item — only eligible items get the discount
7. **Gift cards** deduct from balance, auto-set to USED when balance reaches $0
8. **Cancelling a sale** restores all inventory to the original batches
9. **Split payments** — a single sale can have multiple payments with different methods
10. **Sale numbers** are sequential per location per day (SAL-YYYYMMDD-NNN)
11. **Backdating** is available to owners/admins for past sale entry
12. **Verify prices first** — use the verify-price endpoint before creating a sale to ensure accurate pricing with all rules, taxes, and promos applied
