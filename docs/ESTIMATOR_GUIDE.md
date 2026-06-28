# Estimator Guide

The estimator lets any business build a **per-domain estimate template** once, then
stamp out **estimates for clients** from it. It is fully data-driven: curtains,
plumbing, printing, catering — the domain knowledge lives in template data, not code.

## Two layers

| Layer | Table | What it is |
|---|---|---|
| **Estimate Template** | `msg_estimate_templates` | The reusable blueprint for one domain: what to capture + how to price it |
| **Estimate** | `msg_estimates` + `msg_estimate_items` | One filled-in instance for a client, priced from a template |

This mirrors the existing `workflow_templates → tasks` pattern.

## Template anatomy

A template holds `line_item_defs` (JSONB) and `modifiers` (JSONB).

- **Line item def** — a kind of thing you charge for (a "Window", "Labour"). Has:
  - `key` — unique key, used as the formula namespace (e.g. `window`)
  - `fields` — the inputs the estimator captures on site
  - `computations` — one or more **named, ordered** computed values (see below).
    A single `formula` string is also accepted as a shortcut and is auto-wrapped
    into one `money` computation.
- **Field** — one input with a `data_type`:
  - `number` / `dimension` → numeric variable under its `key`
  - `boolean` → `1.0` / `0.0` under its `key`
  - `select` → the chosen value under `key`, **and** the chosen option's `rate`
    under `<key>_rate`
  - `text` → the raw text under its `key` (usable in `==` / `!=` only)
- **Modifiers** — `markup_percent`, `discount_percent`, `tax_percent`,
  `min_charge`, `valid_days`, `currency`.

### Computations (multiple named outputs)

A line item runs an **ordered list** of computations. Each has a `key`, `label`,
`formula`, optional `unit`, and a `kind`:

| `kind` | Meaning |
|---|---|
| `money` | adds to the line price (and the estimate's money total). A line needs ≥1. |
| `quantity` | rolled up into its own estimate-wide total by `key` (e.g. total yards) — never money |
| `display` | just shown on the line, not totalled anywhere |

Each computation can reference the fields **and any computation defined above it**,
so they chain: `yards` → `material_cost = yards * price_per_yard` → `line`. Order
matters; referencing a not-yet-defined key returns a clean validation error.

### Formula engine

Formulas are evaluated by `src/utils/formula_evaluator.py` — an AST-walking
**safe evaluator** (no `eval`/`exec`). Supported:

- arithmetic: `+ - * / // % **`, parentheses, unary `-`
- comparisons: `> >= < <= == !=` (`==`/`!=` also work on text; chained allowed)
- logic: `and` · `or` · `not`
- conditional: `ifelse(condition, value_if_true, value_if_false)` (and native `a if c else b`)
- functions: `min max round abs ceil floor sqrt area perimeter`

Comparisons/logic evaluate to `1.0`/`0.0`. Anything else (attribute access,
comprehensions, lambdas, unknown names/functions) is rejected at template-create
time and at pricing time.

```
ifelse(num_windows >= 5, material_cost * 0.9, material_cost)
ifelse(fabric == 'velvet', 90, 50)
```

## Pricing math

For each line, computations run top-to-bottom (each feeding the next):
- `unit_amount` = Σ of the `money` computations (per unit)
- `line_total` = `unit_amount × quantity`
- every `quantity` computation is summed across all lines into `quantity_totals`
  (e.g. total yards), kept separate from money.

Then the modifiers apply to the money side:

```
subtotal        = Σ line_total
markup_amount   = subtotal × markup_percent%
discount_amount = (subtotal + markup) × discount_percent%
tax_amount      = (subtotal + markup − discount) × tax_percent%
grand_total     = max(subtotal + markup − discount + tax, min_charge)
```

Each estimate item stores its full breakdown in `computed_values` (JSONB); the
estimate stores `quantity_totals` (JSONB).

## Versioning / snapshot

Each estimate stores a **`template_snapshot`** (frozen copy of the template at
creation). Editing the template later never re-prices existing estimates; edits to
an estimate re-price against its own snapshot, not the live template. Template
edits to the definition bump `version`.

## Lifecycle

`DRAFT → SENT → ACCEPTED → CONVERTED` (plus `REJECTED`, `EXPIRED`). Transitions are
guarded in the service.

### Turning an estimate into an invoice

The estimator does **not** create invoices — it stays a standalone quoting tool
with no dependency on the invoice module. Invoice creation is owned by the invoice
side: an invoice is created either *from scratch* or, in future, *seeded from an
estimate* (where each estimate line can be mapped to a real product or marked as a
non-stock/service line as part of the normal invoice flow).

> This separation is deliberate. The invoice system is product/inventory-centric
> and deducts stock when an invoice is paid, so service estimate lines (curtains,
> labour) need a non-stock/service-product concept to become a *payable* invoice.
> That work belongs in the invoice module and is a future feature.

## API

All under `/api/v1`, same auth/subscription/permission guards as other entities.

Templates (`permission-msg-estimate-templates-*`):
- `POST /estimate-templates/add`
- `PUT  /estimate-templates/update?template_id=`
- `GET  /estimate-templates/get?template_id=`
- `GET  /estimate-templates/list`
- `GET  /estimate-templates/statistics` (total / active / inactive / distinct domains)
- `DELETE /estimate-templates/delete`

Estimates (`permission-msg-estimates-*`):
- `POST  /estimates/add`
- `PUT   /estimates/update?estimate_id=` (re-prices when `items` supplied)
- `PATCH /estimates/status?estimate_id=`
- `GET   /estimates/get?estimate_id=`
- `GET   /estimates/list`
- `GET   /estimates/statistics` (status counts + total/accepted/pipeline value)
- `DELETE /estimates/delete`

## Worked example — curtain shop

Create the template once:

```jsonc
POST /api/v1/estimate-templates/add
{
  "name": "Curtain Job",
  "domain": "Curtains",
  "line_item_defs": [{
    "key": "window",
    "name": "Window",
    "unit": "window",
    "fields": [
      {"key": "height", "label": "Height", "data_type": "dimension", "unit": "m", "required": true},
      {"key": "width",  "label": "Width",  "data_type": "dimension", "unit": "m", "required": true},
      {"key": "fabric", "label": "Fabric", "data_type": "select",
        "options": [{"label": "Cotton", "value": "cotton", "rate": 40},
                    {"label": "Velvet", "value": "velvet", "rate": 80}]},
      {"key": "lining", "label": "Add lining?", "data_type": "boolean"},
      {"key": "labor",  "label": "Labour per window", "data_type": "number", "default": 150}
    ],
    "formula": "height * width * fabric_rate + labor + lining * 50"
  }],
  "modifiers": {"tax_percent": 15, "valid_days": 30, "currency": "GHS"}
}
```

Estimate for a client:

```jsonc
POST /api/v1/estimates/add
{
  "template_id": "estpl_...",
  "customer_id": "cus_...",
  "title": "Curtains for Mr. Mensah",
  "items": [
    {"line_def_key": "window", "label": "Living room", "quantity": 2,
     "field_values": {"height": 1.2, "width": 0.9, "fabric": "velvet", "lining": true}},
    {"line_def_key": "window", "label": "Bedroom", "quantity": 2,
     "field_values": {"height": 1.0, "width": 0.8, "fabric": "cotton", "lining": false}}
  ]
}
```

Each living-room window = `1.2·0.9·80 + 150 + 50 = 286.40`; the service computes
line totals, subtotal, 15% tax and `grand_total`, sets `valid_until` to +30 days,
and returns the estimate in `DRAFT`.

## Install

Run the DDL before first use:

```bash
psql "$DATABASE_URL" -f app/src/entities/estimates/estimates_schema.sql
```

Then register the `permission-msg-estimate-templates-*` and
`permission-msg-estimates-*` permissions for the relevant roles.
