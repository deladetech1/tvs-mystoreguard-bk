-- =====================================================================
-- Estimator feature — templates (per-domain blueprint) + estimates
-- Run this against the mystoreguard database before using /estimates
-- =====================================================================

-- ---------------------------------------------------------------------
-- Estimate templates: the reusable, per-domain blueprint.
-- line_item_defs and modifiers hold the dynamic field/formula definitions
-- as JSONB so any domain (curtains, plumbing, printing...) is data-driven.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS mystoreguard.msg_estimate_templates (
    id                  text        PRIMARY KEY,
    tenant_id           text        NOT NULL,
    org_id              text        NOT NULL,
    bus_id              text        NOT NULL,

    name                text        NOT NULL,                    -- e.g. 'Curtain Job'
    domain              text,                                    -- e.g. 'Curtains'
    description         text,
    version             integer     NOT NULL DEFAULT 1,          -- bumped when the definition changes

    line_item_defs      jsonb       NOT NULL DEFAULT '[]'::jsonb,
    modifiers           jsonb       NOT NULL DEFAULT '{}'::jsonb,

    delete_status       text        NOT NULL DEFAULT 'NOT_DELETED',
    is_active           boolean     NOT NULL DEFAULT TRUE,

    cdate               text,
    ctime               text,
    cdatetime           timestamptz,
    created_by          text,
    updated_by          text,
    deleted_by          text
);

CREATE INDEX IF NOT EXISTS idx_msg_estimate_templates_scope
    ON mystoreguard.msg_estimate_templates (tenant_id, org_id, bus_id);

CREATE INDEX IF NOT EXISTS idx_msg_estimate_templates_active
    ON mystoreguard.msg_estimate_templates (tenant_id, org_id, bus_id, is_active, delete_status);


-- ---------------------------------------------------------------------
-- Estimates: one filled-in instance for a client, created from a template.
-- template_snapshot freezes the template definition at creation time so the
-- estimate never re-prices when the template is later edited.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS mystoreguard.msg_estimates (
    id                  text        PRIMARY KEY,
    tenant_id           text        NOT NULL,
    org_id              text        NOT NULL,
    bus_id              text        NOT NULL,
    loc_id              text,
    estimate_number     text,                                    -- e.g. EST-20260627-001

    template_id         text        NOT NULL,
    template_version    integer     NOT NULL DEFAULT 1,
    template_snapshot   jsonb       NOT NULL DEFAULT '{}'::jsonb,

    customer_id         text,
    title               text,
    notes               text,

    status              text        NOT NULL DEFAULT 'DRAFT',    -- DRAFT|SENT|ACCEPTED|REJECTED|EXPIRED|CONVERTED
    currency            text,

    subtotal            numeric(18,2) NOT NULL DEFAULT 0,
    markup_amount       numeric(18,2) NOT NULL DEFAULT 0,
    discount_amount     numeric(18,2) NOT NULL DEFAULT 0,
    tax_amount          numeric(18,2) NOT NULL DEFAULT 0,
    grand_total         numeric(18,2) NOT NULL DEFAULT 0,
    quantity_totals     jsonb       NOT NULL DEFAULT '[]'::jsonb,   -- non-money rollups, e.g. total yards
    valid_until         date,

    delete_status       text        NOT NULL DEFAULT 'NOT_DELETED',

    cdate               text,
    ctime               text,
    cdatetime           timestamptz,
    created_by          text,
    updated_by          text,
    deleted_by          text
);

CREATE INDEX IF NOT EXISTS idx_msg_estimates_scope
    ON mystoreguard.msg_estimates (tenant_id, org_id, bus_id);

CREATE INDEX IF NOT EXISTS idx_msg_estimates_status
    ON mystoreguard.msg_estimates (tenant_id, org_id, bus_id, status, delete_status);

CREATE INDEX IF NOT EXISTS idx_msg_estimates_customer
    ON mystoreguard.msg_estimates (tenant_id, org_id, bus_id, customer_id);

CREATE INDEX IF NOT EXISTS idx_msg_estimates_template
    ON mystoreguard.msg_estimates (tenant_id, org_id, bus_id, template_id);


-- ---------------------------------------------------------------------
-- Estimate items: the captured, priced lines of an estimate.
-- field_values holds the on-site measurements as JSONB.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS mystoreguard.msg_estimate_items (
    id                  text        PRIMARY KEY,
    tenant_id           text        NOT NULL,
    org_id              text        NOT NULL,
    bus_id              text        NOT NULL,
    loc_id              text,
    estimate_id         text        NOT NULL,

    line_def_key        text        NOT NULL,                    -- which line_item_def priced this line
    name                text,                                    -- snapshot of the line def name
    label               text,                                    -- per-line label, e.g. 'Living room window'
    quantity            numeric(18,4) NOT NULL DEFAULT 1,
    field_values        jsonb       NOT NULL DEFAULT '{}'::jsonb,
    unit_amount         numeric(18,2) NOT NULL DEFAULT 0,        -- sum of money computations (per unit)
    computed_amount     numeric(18,2) NOT NULL DEFAULT 0,        -- unit_amount * quantity
    computed_values     jsonb       NOT NULL DEFAULT '[]'::jsonb, -- per-line breakdown (yards, material, labour...)

    cdate               text,
    ctime               text,
    cdatetime           timestamptz,
    created_by          text
);

CREATE INDEX IF NOT EXISTS idx_msg_estimate_items_estimate
    ON mystoreguard.msg_estimate_items (estimate_id, tenant_id);
