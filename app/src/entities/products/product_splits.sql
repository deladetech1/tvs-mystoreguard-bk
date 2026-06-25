-- =====================================================================
-- Product Split (break-bulk) feature
-- Run this against the mystoreguard database before using /products/split
-- =====================================================================

CREATE TABLE IF NOT EXISTS mystoreguard.msg_product_splits (
    id                  text        PRIMARY KEY,
    tenant_id           text        NOT NULL,
    org_id              text        NOT NULL,
    bus_id              text        NOT NULL,

    -- Source
    source_product_id   text        NOT NULL,
    source_qty_taken    integer     NOT NULL,
    divisor             integer     NOT NULL,
    source_scope        text        NOT NULL DEFAULT 'PRODUCT',  -- PRODUCT | STORE | WAREHOUSE
    location_type       text,                                    -- STORE | WAREHOUSE (location splits)
    loc_id              text,                                    -- location the split happened at
    split_batch_id      text,                                    -- groups items split together in one /split-batch call

    -- Derived (destination)
    derived_product_id  text        NOT NULL,
    derived_batch_id    text        NOT NULL,
    derived_qty         integer     NOT NULL,

    -- Pricing (per smaller unit)
    unit_cost_price     numeric(18,2),
    unit_selling_price  numeric(18,2),
    price_mode          text        NOT NULL DEFAULT 'AUTO',   -- AUTO | MANUAL
    currency_id         text,

    -- Which source batches were consumed and how much (for reversal):
    -- [{"batch_id","batch_number","batch_location_id","qty_taken","cost_price","base_selling_price"}, ...]
    source_batches      jsonb       NOT NULL DEFAULT '[]'::jsonb,
    description         text,                                    -- optional note/reason for the split

    status              text        NOT NULL DEFAULT 'ACTIVE',         -- ACTIVE | REVERSED
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

CREATE INDEX IF NOT EXISTS idx_msg_product_splits_source
    ON mystoreguard.msg_product_splits (tenant_id, org_id, bus_id, source_product_id);

CREATE INDEX IF NOT EXISTS idx_msg_product_splits_status
    ON mystoreguard.msg_product_splits (tenant_id, org_id, bus_id, status);

CREATE INDEX IF NOT EXISTS idx_msg_product_splits_derived_batch
    ON mystoreguard.msg_product_splits (derived_batch_id);

CREATE INDEX IF NOT EXISTS idx_msg_product_splits_batch_group
    ON mystoreguard.msg_product_splits (tenant_id, org_id, bus_id, split_batch_id);


-- =====================================================================
-- New permission (lives in the trovesuite core_platform DB).
-- Add it the same way other "permission-msg-products-*" rows are seeded,
-- then grant it to the roles that should be able to split products.
-- The exact table/columns belong to trovesuite; this is the key to register:
--
--     permission-msg-products-split
-- =====================================================================
