# Pricing Calculation Guide

This guide explains how product prices are calculated in the system, step by step.

---

## The Pricing Pipeline

Every product price goes through 5 steps in this exact order:

```
Step 1: Cost Price
    |
Step 2: Base Selling Price
    |
Step 3: Actual Price (custom pricing)
    |
Step 4: Price After Pricing Rule (discounts/markups)
    |
Step 5: Price After Tax (final price customer pays)
```

---

## Step 1: Cost Price

**What it is:** The price your business paid the supplier for the product.

**Where it comes from:** The purchase batch. When you receive goods from a supplier, you record the cost price per unit.

**Example:**
- You bought 100 units of "Samsung Galaxy A15" at $ 1,200 each
- Cost Price = $ 1,200

> This is an internal number. Customers never see it. It is used for profit calculations.

---

## Step 2: Base Selling Price

**What it is:** The default selling price you set when receiving the product.

**Where it comes from:** The purchase batch. When you receive goods, you set the base selling price alongside the cost price.

**Example:**
- Cost Price: $ 1,200
- Base Selling Price: $ 1,500

> This is your starting price before any custom pricing, rules, or taxes are applied.

---

## Step 3: Actual Price (Custom Pricing)

**What it is:** A custom price that overrides the base selling price. You can set different prices based on different conditions.

**Where it comes from:** The Product Prices settings. You can create price entries that target:

| Target Type | Example |
|---|---|
| GLOBAL | "All locations pay $ 1,500" |
| LOCATION | "Manhattan store sells at $ 1,600, Brooklyn store sells at $ 1,450" |
| SKU | "SKU-A15-BLK sells at $ 1,550" |
| CATEGORY | "All phones sell at $ 1,500" |
| BRAND | "All Samsung products sell at $ 1,500" |
| TAG | "All 'premium' tagged items sell at $ 1,500" |
| LABEL | "All 'clearance' items sell at $ 800" |

**Which price wins when multiple match?**

The system picks the most specific price first:

```
1. SKU price           (most specific - wins first)
2. LOCATION price
3. TAG / CATEGORY / BRAND / LABEL price
4. GLOBAL price        (least specific - used as fallback)
```

If two prices are at the same level (e.g., two CATEGORY prices), the one with the higher priority number wins.

If no custom price is found, the Base Selling Price from Step 2 is used.

**Example:**
- Base Selling Price: $ 1,500
- You set a LOCATION price for Manhattan store: $ 1,600
- You set a GLOBAL price: $ 1,550
- Customer buys from Manhattan store -> Actual Price = $ 1,600 (LOCATION is more specific than GLOBAL)
- Customer buys from Brooklyn store -> Actual Price = $ 1,550 (GLOBAL is the fallback)

---

## Step 4: Price After Pricing Rule (Discounts & Markups)

**What it is:** Automatic discounts or markups that are applied to the actual price based on rules you define.

**Where it comes from:** Pricing Rules settings. You create rules that automatically adjust prices.

### Pricing Rule Types

| Rule Type | What It Does | Example |
|---|---|---|
| FIXED_PRICE | Sets the price to an exact amount | "Sell this phone at exactly $ 1,400" |
| FIXED_AMOUNT | Sets the price to a fixed amount | "Sell this item at $ 1,300" |
| PRICE_DISCOUNT | Subtracts a fixed amount from the price | "Take $ 100 off the price" -> $ 1,500 - $ 100 = $ 1,400 |
| PERCENTAGE_DISCOUNT | Subtracts a percentage from the price | "10% off" -> $ 1,500 - $ 150 = $ 1,350 |
| PRICE_MARKUP | Adds a fixed amount to the price | "Add $ 200" -> $ 1,500 + $ 200 = $ 1,700 |
| PERCENTAGE_MARKUP | Adds a percentage to the price | "15% markup" -> $ 1,500 + $ 225 = $ 1,725 |
| QUANTITY_BREAK | Discount when buying in bulk | "Buy 10+, get 5% off per unit" (only applied at checkout) |

### Which rule applies?

Same as custom pricing - the most specific rule wins:

```
1. SKU rule            (most specific)
2. PRODUCT rule
3. TAG / CATEGORY / BRAND / LABEL rule
4. LOCATION rule
5. ALL_PRODUCTS rule   (least specific)
```

Within the same level, higher priority wins. Only ONE pricing rule is applied per product.

### Time-Based Rules

Rules can have a start and end date. For example:
- "Black Friday Sale: 20% off all products, Nov 29 - Dec 1"
- Outside that date range, the rule is ignored

**Example:**
- Actual Price: $ 1,500
- Rule: PERCENTAGE_DISCOUNT of 10% on CATEGORY "Phones"
- Price After Pricing Rule = $ 1,500 - $ 150 = $ 1,350

---

## Step 5: Price After Tax (Final Price)

**What it is:** The final price after taxes are applied. This is what the customer pays.

**Where it comes from:** Tax Rules settings. You define which taxes apply to which products.

### Two Types of Tax

| Tax Type | How It Works | Example |
|---|---|---|
| **Inclusive** | Tax is already included in the price. The system extracts it for reporting, but the customer price stays the same. | Price is $ 1,350. VAT 15% is inclusive. Customer pays $ 1,350. Tax portion = $ 176.09 (for your records). |
| **Exclusive** | Tax is added on top of the price. The customer pays more. | Price is $ 1,350. Service tax 5% is exclusive. Customer pays $ 1,350 + $ 67.50 = $ 1,417.50 |

### Multiple Taxes Can Stack

Unlike pricing rules (where only one applies), ALL matching tax rules are applied together.

**Example with both inclusive and exclusive:**
- Price After Pricing Rule: $ 1,350
- VAT 15% (inclusive) - already in the $ 1,350
- Service Tax 2.5% (exclusive) - added on top
- Pre-tax base (extracting inclusive VAT): $ 1,350 / 1.15 = $ 1,173.91
- VAT amount: $ 1,173.91 x 15% = $ 176.09 (for records, not added)
- Service Tax amount: $ 1,350 x 2.5% = $ 33.75 (added to price)
- Final Price = $ 1,350 + $ 33.75 = $ 1,383.75

### Tax Conditions (At Checkout Only)

During checkout, the system can evaluate conditions before applying tax:

| Condition | Example |
|---|---|
| IF_ITEM_PRICE > 500 | "Only apply luxury tax if item costs more than $ 500" |
| IF_TOTAL_PRICE > 10000 | "Tax exemption if total purchase exceeds $ 10,000" |
| IF_ITEM_QTY > 100 | "Bulk purchase tax reduction for quantities over 100" |

Conditions can result in:
- **TAX_EXEMPTION** - Tax is not applied at all
- **TAX_REDUCTION** - Tax is reduced by a percentage or fixed amount

---

## Complete Example

Let's follow a product through the entire pipeline:

**Product:** Samsung Galaxy A15
**Customer:** Buying 1 unit from the Manhattan store

| Step | Description | Amount |
|---|---|---|
| 1. Cost Price | Paid to supplier | $ 1,200 |
| 2. Base Selling Price | Set when receiving | $ 1,500 |
| 3. Actual Price | LOCATION price for Manhattan | $ 1,600 |
| 4. Pricing Rule | 10% discount on "Phones" category | $ 1,600 - $ 160 = **$ 1,440** |
| 5a. VAT 15% (inclusive) | Already in the price | $ 187.83 (extracted) |
| 5b. Service Tax 2.5% (exclusive) | Added on top | $ 1,440 x 2.5% = $ 36.00 |
| **Final Price** | **What customer pays** | **$ 1,476.00** |

**Gross Profit:** $ 1,440 - $ 1,200 = $ 240 per unit

---

## Summary: Where to Configure Each Step

| Step | Where to Configure | Menu Location |
|---|---|---|
| Cost Price | Purchase Orders -> Receive Goods | Set when receiving stock |
| Base Selling Price | Purchase Orders -> Receive Goods | Set when receiving stock |
| Actual Price | Settings -> Product Prices | Custom prices per product |
| Pricing Rules | Settings -> Pricing Rules | Discounts, markups, bulk pricing |
| Tax Rules | Settings -> Tax Rules | Which taxes apply to what |
| Taxes | Settings -> Taxes | Define tax rates (VAT, Sales Tax, Service Tax, etc.) |

---

## Key Rules to Remember

1. **Only ONE pricing rule applies per product** - the most specific one wins
2. **ALL matching tax rules apply** - taxes stack (VAT + Service Tax + etc.)
3. **Specificity always beats priority** - a product-specific rule at priority 0 beats an ALL_PRODUCTS rule at priority 100
4. **Within the same specificity level**, higher priority number wins
5. **Inclusive tax doesn't change the customer price** - it's already baked in
6. **Exclusive tax increases the customer price** - it's added on top
7. **Quantity-based pricing rules only apply at checkout** - they don't affect the display price when browsing products
8. **Time-based rules are automatic** - they activate and deactivate based on the dates you set
