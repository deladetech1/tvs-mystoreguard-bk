-- =====================================================================
-- Product Split (break-bulk) feature — header + line items
-- Run this against the mystoreguard database before using /products/split
-- =====================================================================

-- ---------------------------------------------------------------------
-- Header: one row per split operation (the thing you "open")
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS mystoreguard.msg_product_splits (
    id                  text        PRIMARY KEY,
    split_number        text,                                    -- e.g. SPL-20260625-001
    tenant_id           text        NOT NULL,
    org_id              text        NOT NULL,
    bus_id              text        NOT NULL,

    description         text,                                    -- optional note/reason for the whole split
    source_scope        text        NOT NULL DEFAULT 'PRODUCT',  -- PRODUCT | STORE | WAREHOUSE
    location_type       text,                                    -- STORE | WAREHOUSE (location splits)
    loc_id              text,                                    -- location the split happened at

    status              text        NOT NULL DEFAULT 'ACTIVE',   -- ACTIVE | PARTIALLY_REVERSED | REVERSED
    delete_status       text        NOT NULL DEFAULT 'NOT_DELETED',

    cdate               text,
    ctime               text,
    cdatetime           timestamptz,
    created_by          text,
    updated_by          text,
    reversed_by         text,
    reversed_at         timestamptz
);

CREATE INDEX IF NOT EXISTS idx_msg_product_splits_scope
    ON mystoreguard.msg_product_splits (tenant_id, org_id, bus_id);

CREATE INDEX IF NOT EXISTS idx_msg_product_splits_loc
    ON mystoreguard.msg_product_splits (tenant_id, org_id, bus_id, loc_id);

CREATE INDEX IF NOT EXISTS idx_msg_product_splits_status
    ON mystoreguard.msg_product_splits (tenant_id, org_id, bus_id, status);


-- ---------------------------------------------------------------------
-- Items: one row per product line within a split (independently reversible)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS mystoreguard.msg_product_split_items (
    id                  text        PRIMARY KEY,
    split_id            text        NOT NULL,                    -- FK -> msg_product_splits.id
    tenant_id           text        NOT NULL,
    org_id              text        NOT NULL,
    bus_id              text        NOT NULL,

    source_product_id   text        NOT NULL,
    source_qty_taken    integer     NOT NULL,
    divisor             integer     NOT NULL,

    derived_product_id  text        NOT NULL,
    derived_batch_id    text        NOT NULL,
    derived_qty         integer     NOT NULL,

    unit_cost_price     numeric(18,2),
    unit_selling_price  numeric(18,2),
    price_mode          text        NOT NULL DEFAULT 'AUTO',     -- AUTO | MANUAL
    currency_id         text,

    -- Which source batches were consumed and how much (for reversal):
    -- [{"batch_id","batch_number","batch_location_id","qty_taken","cost_price","base_selling_price"}, ...]
    source_batches      jsonb       NOT NULL DEFAULT '[]'::jsonb,

    status              text        NOT NULL DEFAULT 'ACTIVE',   -- ACTIVE | REVERSED
    delete_status       text        NOT NULL DEFAULT 'NOT_DELETED',

    cdate               text,
    ctime               text,
    cdatetime           timestamptz,
    created_by          text,
    updated_by          text,
    reversed_by         text,
    reversed_at         timestamptz
);

CREATE INDEX IF NOT EXISTS idx_msg_product_split_items_split
    ON mystoreguard.msg_product_split_items (split_id);

CREATE INDEX IF NOT EXISTS idx_msg_product_split_items_scope
    ON mystoreguard.msg_product_split_items (tenant_id, org_id, bus_id, status);

CREATE INDEX IF NOT EXISTS idx_msg_product_split_items_source
    ON mystoreguard.msg_product_split_items (tenant_id, org_id, bus_id, source_product_id);

CREATE INDEX IF NOT EXISTS idx_msg_product_split_items_derived_batch
    ON mystoreguard.msg_product_split_items (derived_batch_id);


-- =====================================================================
-- New permission (lives in the trovesuite core_platform DB).
-- Register it the same way other "permission-msg-products-*" rows are
-- seeded, then grant it to the roles that should split products:
--
--     permission-msg-products-split
-- =====================================================================
