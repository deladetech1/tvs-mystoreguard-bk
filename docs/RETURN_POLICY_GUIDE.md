# Return Policy Guide

This guide explains how return policies work in the system — how to create them, how they apply to products, and how the system decides which policy governs a return.

---

## What is a Return Policy?

A return policy is a set of rules that defines:
- **Which products** can be returned
- **How long** after purchase a return is accepted
- **What condition** the item must be in
- **How much** the customer gets back (restocking fees)
- **Who needs to approve** the return
- **How** the refund is issued

Organizations can create multiple policies that target different products, categories, brands, or locations.

---

## Creating a Return Policy

When creating a policy, you configure these settings:

### 1. Basic Information

| Field | Description | Example |
|---|---|---|
| `name` | Name of the policy | "Electronics Return Policy" |
| `description` | Optional notes | "Applies to all electronics sold in-store" |

### 2. Applies To (Targeting)

This controls WHICH products the policy applies to. Same targeting system as pricing rules.

| Target Type | `policy_target_id` | Example |
|---|---|---|
| `ALL_PRODUCTS` | Not required | "Default policy for everything" |
| `PRODUCT` | Product ID | "Policy for iPhone 15 only" |
| `SKU` | SKU value | "Policy for SKU-IPHONE15-BLK" |
| `CATEGORY` | Category metadata ID | "Policy for all Electronics" |
| `BRAND` | Brand metadata ID | "Policy for all Samsung products" |
| `TAG` | Tag metadata ID | "Policy for all 'fragile' tagged items" |
| `LABEL` | Label metadata ID | "Policy for all 'final-sale' items" |
| `LOCATION` | Location ID | "Policy for Manhattan store only" |

### 3. Return Rules

| Field | Description | Example |
|---|---|---|
| `return_window_days` | Number of days after purchase within which a return is accepted. **0 = non-returnable.** | `7` (7-day return window) |
| `condition_required` | What condition the item must be in | See below |
| `receipt_required` | Whether proof of purchase is needed | `true` |
| `allow_expired_returns` | Whether to accept expired items (refund but write off, not restock) | `false` |

**Condition Required Options:**

| Value | Meaning |
|---|---|
| `ANY` | Item can be in any condition |
| `UNOPENED` | Item must be sealed/unopened |
| `WITH_TAGS` | Item must still have original tags |
| `UNDAMAGED` | Item must not be damaged |

### 4. Refund Rules

| Field | Description | Example |
|---|---|---|
| `restocking_fee_percent` | Percentage deducted from the refund as a restocking fee | `10.00` (10% fee) |
| `refund_method` | How the refund is issued | See below |

**Refund Method Options:**

| Value | Meaning |
|---|---|
| `ORIGINAL_PAYMENT` | Refund via the same method customer paid with |
| `STORE_CREDIT` | Refund as store credit |
| `CASH` | Refund as cash |
| `ANY` | Any refund method allowed (staff decides) |

**Restocking Fee Example:**
- Item price: $100
- Restocking fee: 10%
- Customer gets back: $100 - $10 = **$90**

### 5. Approval Settings

| Field | Description | Example |
|---|---|---|
| `approval_required` | Whether returns under this policy need manager approval | `true` |
| `approvers` | List of email addresses authorized to approve/reject returns | `["manager@store.com", "admin@store.com"]` |
| `approval_threshold_amount` | If set, approval is only required when refund exceeds this amount. Must be greater than 0. | `500.00` |

**How Approval Works:**

| Setup | Behavior |
|---|---|
| `approval_required: false` | Returns are auto-approved. No one needs to review. |
| `approval_required: true`, no threshold | Every return needs approval |
| `approval_required: true`, threshold: $500 | Only returns above $500 need approval. Below $500 = auto-approved. |
| `approvers: ["manager@store.com"]` | Only this person can approve/reject. Others get "NOT_AUTHORIZED_APPROVER" error. |
| `approvers: null` or `[]` | Anyone with the approve permission can approve. |

### 6. Policy Behavior

| Field | Description | Example |
|---|---|---|
| `stops_other_policies` | If true, this policy prevents other policies from being evaluated | `false` |
| `priority` | Higher number = evaluated first within the same specificity level | `10` |
| `is_active` | Enable or disable the policy | `true` |

### 7. Time-Based Activation

| Field | Description | Example |
|---|---|---|
| `start_datetime` | When the policy becomes active | `"2026-12-01T00:00:00"` |
| `end_datetime` | When the policy expires | `"2027-01-15T23:59:59"` |

If both are null, the policy is always active. Use this for seasonal policies like "Holiday Extended Returns."

---

## Which Policy Wins?

When a customer returns a product, the system finds the most applicable policy. It checks specificity first, then priority:

```
1. SKU policy          (most specific - wins first)
2. PRODUCT policy
3. TAG / CATEGORY / BRAND / LABEL policy
4. LOCATION policy
5. ALL_PRODUCTS policy (least specific - used as fallback)
```

Within the same specificity level, higher priority number wins. Only **ONE** policy is applied per return.

**Example:**

```
Policy A: ALL_PRODUCTS, 14 days, priority 0
Policy B: CATEGORY "Electronics", 7 days, priority 10
Policy C: PRODUCT "Earphones", 0 days (non-returnable), priority 20

Customer returns a laptop   -> Policy B wins (CATEGORY is more specific than ALL_PRODUCTS)
Customer returns earphones  -> Policy C wins (PRODUCT is more specific than CATEGORY)
Customer returns a shirt    -> Policy A wins (ALL_PRODUCTS is the fallback)
```

---

## Policy Enforcement

When a return is created, the system automatically enforces the matched policy:

### Return Window Check
```
Sale date: Jan 1
Policy: 7-day return window
Deadline: Jan 8
Today: Jan 5 -> ALLOWED (within window)
Today: Jan 10 -> REJECTED ("Return window has expired")
```

### Non-Returnable Check
```
Policy: return_window_days = 0
Result: REJECTED ("This item is non-returnable")
```

### Expired Item Check
```
Item condition: EXPIRED
Policy: allow_expired_returns = false
Result: REJECTED ("Expired items cannot be returned")

Policy: allow_expired_returns = true
Result: ALLOWED (item is refunded but written off, not restocked)
```

### Restocking Fee Calculation
```
Item price: $200
Policy: restocking_fee_percent = 15%
Restocking fee: $200 x 15% = $30
Customer refund: $200 - $30 = $170
```

### Approval Requirement
```
Refund amount: $800
Policy: approval_required = true, threshold = $500
$800 > $500 -> Status: PENDING (needs approval)

Refund amount: $300
$300 <= $500 -> Status: APPROVED (auto-approved)
```

---

## Example Policies for a Retail Store

### Policy 1: Default (catch-all)
```json
{
    "name": "Standard Return Policy",
    "policy_target_type": "ALL_PRODUCTS",
    "return_window_days": 14,
    "condition_required": "ANY",
    "receipt_required": true,
    "allow_expired_returns": false,
    "restocking_fee_percent": 0,
    "refund_method": "ANY",
    "approval_required": false,
    "priority": 0,
    "is_active": true
}
```

### Policy 2: Electronics (stricter)
```json
{
    "name": "Electronics Return Policy",
    "policy_target_type": "CATEGORY",
    "policy_target_id": "cat-electronics-id",
    "return_window_days": 7,
    "condition_required": "UNOPENED",
    "receipt_required": true,
    "allow_expired_returns": false,
    "restocking_fee_percent": 10,
    "refund_method": "ORIGINAL_PAYMENT",
    "approval_required": true,
    "approvers": ["manager@store.com", "supervisor@store.com"],
    "approval_threshold_amount": 500,
    "priority": 10,
    "is_active": true
}
```

### Policy 3: Non-returnable items
```json
{
    "name": "No Returns - Earphones",
    "policy_target_type": "PRODUCT",
    "policy_target_id": "prod-earphones-id",
    "return_window_days": 0,
    "condition_required": "ANY",
    "receipt_required": false,
    "restocking_fee_percent": 0,
    "refund_method": "ANY",
    "approval_required": false,
    "priority": 20,
    "is_active": true
}
```

### Policy 4: Holiday season (time-based)
```json
{
    "name": "Holiday Extended Returns",
    "policy_target_type": "ALL_PRODUCTS",
    "return_window_days": 30,
    "condition_required": "ANY",
    "receipt_required": true,
    "restocking_fee_percent": 0,
    "refund_method": "ANY",
    "approval_required": false,
    "priority": 5,
    "start_datetime": "2026-12-01T00:00:00",
    "end_datetime": "2027-01-15T23:59:59",
    "is_active": true
}
```

During Dec 1 - Jan 15, this policy (priority 5) overrides the default (priority 0) for ALL_PRODUCTS, giving customers 30 days instead of 14.

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/return-policies/add` | Create a new return policy |
| `PUT` | `/api/v1/return-policies/update?policy_id=` | Update an existing policy |
| `GET` | `/api/v1/return-policies/get?policy_id=` | Get a single policy |
| `GET` | `/api/v1/return-policies/list` | List all policies (with filters) |
| `DELETE` | `/api/v1/return-policies/delete` | Delete a policy |
| `GET` | `/api/v1/return-policies/statistics` | Get policy statistics |

### List Filters

| Parameter | Description |
|---|---|
| `page` | Page number (default: 1) |
| `size` | Page size (default: 10, max: 100) |
| `policy_target_type` | Filter by target type |
| `is_active` | Filter by active status |

---

## Key Rules to Remember

1. **Only ONE policy applies per return** — the most specific one wins
2. **Specificity beats priority** — a PRODUCT policy at priority 0 beats an ALL_PRODUCTS policy at priority 100
3. **Priority breaks ties** within the same specificity level
4. **0 days = non-returnable** — setting `return_window_days` to 0 blocks returns entirely
5. **Approvers list is optional** — if not set, anyone with the approve permission can approve
6. **Threshold must be greater than 0** — you can't set it to 0 (use `null` for "always require approval")
7. **Time-based policies auto-activate and expire** — no manual intervention needed
8. **Expired items are never restocked** — even if the return is approved, expired items are written off
