-- Community Benefits Navigator - Schema for Indian Welfare Schemes
-- Supports: PM-KISAN, Ayushman Bharat, PM Awas Yojana, Scholarships, Ujjwala, and similar schemes

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ─── Users ───────────────────────────────────────────────────────────────────

CREATE TYPE gender AS ENUM ('male', 'female', 'transgender');
CREATE TYPE caste_category AS ENUM ('general', 'obc', 'sc', 'st', 'ews');
CREATE TYPE bpl_status AS ENUM ('above_poverty_line', 'below_poverty_line', 'antyodaya');

CREATE TABLE users (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aadhaar_hash        TEXT UNIQUE,                -- SHA-256 hash, never store raw
    full_name           TEXT NOT NULL,
    date_of_birth       DATE NOT NULL,
    gender              gender,
    caste_category      caste_category,
    bpl_status          bpl_status,
    mobile              TEXT,
    -- Address
    address_line1       TEXT,
    address_line2       TEXT,
    city                TEXT,
    district            TEXT,
    state               TEXT,
    pincode             TEXT,
    -- Economic
    annual_income_cents BIGINT,                     -- annual income in paise (₹)
    land_holding_acres  DECIMAL(10, 2),             -- for PM-KISAN eligibility
    household_size      INT,
    -- Linked identifiers
    ration_card_number  TEXT,
    bank_account_number_hash TEXT,                  -- SHA-256 hash
    ifsc_code           TEXT,
    -- Meta
    preferred_language  TEXT DEFAULT 'hindi',
    created_at          TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_users_aadhaar ON users (aadhaar_hash);
CREATE INDEX idx_users_mobile ON users (mobile);
CREATE INDEX idx_users_district ON users (district, state);

-- ─── Government Schemes ───────────────────────────────────────────────────────

CREATE TYPE scheme_category AS ENUM (
    'agriculture',      -- PM-KISAN
    'healthcare',       -- Ayushman Bharat
    'housing',          -- PM Awas Yojana
    'education',        -- Scholarship schemes
    'energy',           -- Ujjwala
    'food_security',    -- NFSA, PDS
    'social_security',  -- old age pension, widow pension
    'employment',       -- MGNREGA
    'insurance',        -- PM Fasal Bima, PM Suraksha Bima
    'other'
);

CREATE TYPE benefit_type AS ENUM (
    'cash_transfer',        -- PM-KISAN (₹6000/yr), Scholarship (tuition)
    'insurance_coverage',   -- Ayushman Bharat (₹5L)
    'subsidy',              -- PM Awas (house subsidy), Ujjwala (LPG)
    'in_kind',              -- Food grains (PDS), free medicines
    'voucher',              -- Education voucher
    'service'               -- Free health checkup, training
);

CREATE TYPE application_channel AS ENUM (
    'common_service_centre',  -- CSC
    'seva_kendra',
    'umang_app',
    'state_portal',
    'central_portal',
    'offline',
    'agent_assisted'
);

CREATE TABLE schemes (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name                TEXT NOT NULL,               -- e.g. "PM-KISAN Samman Nidhi"
    short_name          TEXT NOT NULL,               -- e.g. "PM-KISAN"
    category            scheme_category NOT NULL,
    ministry            TEXT,                        -- e.g. "Ministry of Agriculture"
    level               TEXT NOT NULL CHECK (level IN ('central', 'state', 'central_state')),
    description         TEXT,
    benefit_type        benefit_type NOT NULL,
    benefit_amount      BIGINT,                      -- in paise (₹)
    benefit_details     JSONB,                       -- e.g. {"installments": 3, "per_installment": 200000}
    application_url     TEXT,
    application_channel application_channel[],
    is_active           BOOLEAN DEFAULT true,
    created_at          TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_schemes_category ON schemes (category);
CREATE INDEX idx_schemes_active ON schemes (is_active);

-- ═══════════════════════════════════════════════════════════════════════════════
-- Seed: Initial Schemes (PM-KISAN, Ayushman Bharat, PM Awas, Scholarship, Ujjwala)
-- ═══════════════════════════════════════════════════════════════════════════════

INSERT INTO schemes (name, short_name, category, ministry, level, benefit_type, benefit_amount, benefit_details, application_channel) VALUES
(
    'Pradhan Mantri Kisan Samman Nidhi',
    'PM-KISAN',
    'agriculture',
    'Ministry of Agriculture and Farmers Welfare',
    'central',
    'cash_transfer',
    600000, -- ₹6,000
    '{"installments": 3, "per_installment": 200000, "frequency": "every_4_months", "currency": "INR"}',
    ARRAY['common_service_centre', 'state_portal']
),
(
    'Ayushman Bharat Pradhan Mantri Jan Arogya Yojana',
    'Ayushman Bharat',
    'healthcare',
    'Ministry of Health and Family Welfare',
    'central_state',
    'insurance_coverage',
    50000000, -- ₹5,00,000
    '{"coverage_per_family": 50000000, "family_size": "up_to_5", "currency": "INR", "type": "family_floater"}',
    ARRAY['common_service_centre', 'seva_kendra', 'umang_app']
),
(
    'Pradhan Mantri Awas Yojana - Gramin',
    'PM Awas Yojana',
    'housing',
    'Ministry of Rural Development',
    'central',
    'subsidy',
    12000000, -- ₹1,20,000
    '{"unit_cost": 12000000, "installment_based": true, "currency": "INR", "type": "house_construction"}',
    ARRAY['common_service_centre', 'state_portal', 'offline']
),
(
    'National Scholarship Portal - Post Matric Scholarship',
    'Post Matric Scholarship',
    'education',
    'Ministry of Social Justice and Empowerment',
    'central_state',
    'cash_transfer',
    1000000, -- variable, ~₹10,000
    '{"type": "tuition_fee_and_maintenance", "variable": true, "currency": "INR"}',
    ARRAY['central_portal', 'umang_app']
),
(
    'Pradhan Mantri Ujjwala Yojana',
    'Ujjwala',
    'energy',
    'Ministry of Petroleum and Natural Gas',
    'central',
    'subsidy',
    160000, -- ₹1,600 (free LPG connection)
    '{"type": "free_lpg_connection", "includes_cylinder": true, "currency": "INR"}',
    ARRAY['common_service_centre', 'offline']
);

-- ─── Eligibility Rules ──────────────────────────────────────────────────────

CREATE TYPE eligibility_rule_type AS ENUM (
    'income_max',               -- annual income ≤ threshold
    'income_min',               -- annual income ≥ threshold
    'age_min',                  -- age ≥ X years
    'age_max',                  -- age ≤ X years
    'gender',                   -- specific gender(s)
    'caste_category_in',        -- eligible caste groups
    'bpl_status_in',            -- BPL/APL/Antyodaya
    'landholding_max',          -- land ≤ X acres (for PM-KISAN)
    'landholding_min',          -- land ≥ X acres
    'resident_of',              -- state or district list
    'household_size_max',       -- family size ≤ N
    'has_ration_card',          -- must possess ration card
    'has_aadhaar',              -- must have Aadhaar
    'has_bank_account',         -- must have bank account (DBT)
    'female_head_of_household', -- woman-headed household
    'no_pucca_house',           -- for housing schemes
    'no_lpg_connection',        -- for Ujjwala
    'ssec_deprivation',         -- SECC deprivation criteria
    'custom'                    -- JSONB for complex rules
);

CREATE TABLE eligibility_rules (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scheme_id       UUID NOT NULL REFERENCES schemes(id) ON DELETE CASCADE,
    rule_type       eligibility_rule_type NOT NULL,
    operator        TEXT NOT NULL DEFAULT 'eq',  -- eq, neq, lt, lte, gt, gte, in, not_in, between
    value           JSONB NOT NULL,              -- flexible: number, string, array, object
    priority        INT DEFAULT 0,              -- evaluation order (lower = evaluated first)
    logic_group     INT DEFAULT 1,              -- for AND/OR grouping within scheme
    description     TEXT,                        -- human-readable: "Must be a landholding farmer"
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_eligibility_scheme ON eligibility_rules (scheme_id);

-- ═══════════════════════════════════════════════════════════════════════════════
-- Seed: Eligibility Rules for Initial Schemes
-- ═══════════════════════════════════════════════════════════════════════════════

-- Helper: get scheme IDs (works within migration)
DO $$
DECLARE
    pm_kisan_id      UUID;
    ayushman_id      UUID;
    pm_awas_id       UUID;
    scholarship_id   UUID;
    ujjwala_id       UUID;
BEGIN
    SELECT id INTO pm_kisan_id    FROM schemes WHERE short_name = 'PM-KISAN';
    SELECT id INTO ayushman_id    FROM schemes WHERE short_name = 'Ayushman Bharat';
    SELECT id INTO pm_awas_id     FROM schemes WHERE short_name = 'PM Awas Yojana';
    SELECT id INTO scholarship_id FROM schemes WHERE short_name = 'Post Matric Scholarship';
    SELECT id INTO ujjwala_id     FROM schemes WHERE short_name = 'Ujjwala';

    -- ── PM-KISAN ──────────────────────────────────────────────────────────────
    INSERT INTO eligibility_rules (scheme_id, rule_type, operator, value, priority, logic_group, description) VALUES
    (pm_kisan_id, 'landholding_min', 'gte',  '0.01',      1, 1, 'Must be a landholding farmer'),
    (pm_kisan_id, 'landholding_max', 'lte',  '2.00',      1, 1, 'Small or marginal farmer (≤2 hectares)'),
    (pm_kisan_id, 'has_aadhaar',    'eq',   'true',       2, 1, 'Aadhaar is mandatory for DBT'),
    (pm_kisan_id, 'has_bank_account','eq',  'true',       2, 1, 'Bank account required for transfer'),
    (pm_kisan_id, 'income_max',      'lte', 'null',       3, 1, 'No upper income limit (all landholding farmers eligible)');

    -- ── Ayushman Bharat ───────────────────────────────────────────────────────
    INSERT INTO eligibility_rules (scheme_id, rule_type, operator, value, priority, logic_group, description) VALUES
    (ayushman_id, 'bpl_status_in',   'in',   '["below_poverty_line", "antyodaya"]', 1, 1, 'Must be BPL or Antyodaya family'),
    (ayushman_id, 'ssec_deprivation','eq',   'true',       2, 1, 'Must meet SECC 2011 deprivation criteria'),
    (ayushman_id, 'resident_of',     'in',   '["all_except_specified"]', 3, 1, 'Available in all states/UTs except those that opted out');

    -- ── PM Awas Yojana ────────────────────────────────────────────────────────
    INSERT INTO eligibility_rules (scheme_id, rule_type, operator, value, priority, logic_group, description) VALUES
    (pm_awas_id,  'income_max',      'lte',  '3000000',    1, 1, 'Annual income ≤ ₹3,00,000 (EWS/LIG)'),  -- 3L paise
    (pm_awas_id,  'no_pucca_house',  'eq',   'true',       1, 1, 'Household must not own a pucca house'),
    (pm_awas_id,  'bpl_status_in',   'in',   '["below_poverty_line", "antyodaya"]', 2, 1, 'Preference to BPL/Antyodaya families'),
    (pm_awas_id,  'resident_of',     'eq',   'rural',      3, 1, 'Rural areas (PMAY-G)');

    -- ── Post Matric Scholarship ───────────────────────────────────────────────
    INSERT INTO eligibility_rules (scheme_id, rule_type, operator, value, priority, logic_group, description) VALUES
    (scholarship_id, 'caste_category_in', 'in', '["sc", "st", "obc"]', 1, 1, 'SC/ST/OBC categories eligible'),
    (scholarship_id, 'income_max',  'lte',  '2500000',    2, 1, 'Family income ≤ ₹2,50,000'),
    (scholarship_id, 'age_max',     'lte',  '30',          3, 1, 'Age ≤ 30 years'),
    (scholarship_id, 'has_bank_account','eq','true',       4, 1, 'Bank account required');

    -- ── Ujjwala ───────────────────────────────────────────────────────────────
    INSERT INTO eligibility_rules (scheme_id, rule_type, operator, value, priority, logic_group, description) VALUES
    (ujjwala_id,   'female_head_of_household', 'eq', 'true', 1, 1, 'Woman-headed BPL household'),
    (ujjwala_id,   'bpl_status_in', 'in', '["below_poverty_line"]', 1, 1, 'Must be BPL'),
    (ujjwala_id,   'no_lpg_connection', 'eq', 'true', 2, 1, 'Household must not already have an LPG connection'),
    (ujjwala_id,   'age_min',       'gte', '18',           3, 1, 'Applicant must be ≥ 18 years');
END $$;

-- ─── Required Documents ───────────────────────────────────────────────────────

CREATE TYPE document_type AS ENUM (
    'aadhaar_card',
    'voter_id',
    'ration_card',
    'income_certificate',
    'caste_certificate',
    'domicile_certificate',
    'land_record',              -- for PM-KISAN
    'bank_passbook',
    'passport_photo',
    'mark_sheet',               -- for scholarships
    'admission_letter',         -- for scholarships
    'fee_receipt',              -- for scholarships
    'bpl_certificate',
    'death_certificate',        -- for widow pension
    'age_certificate',
    'disability_certificate',
    'marriage_certificate',
    'property_document',        -- for PM Awas
    'gas_agency_declaration',   -- for Ujjwala
    'self_declaration',
    'other'
);

CREATE TABLE required_documents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scheme_id       UUID NOT NULL REFERENCES schemes(id) ON DELETE CASCADE,
    document_type   document_type NOT NULL,
    description     TEXT,
    is_mandatory    BOOLEAN DEFAULT true,
    can_upload_later BOOLEAN DEFAULT false,       -- application can be submitted, upload later
    sort_order      INT DEFAULT 0
);

CREATE INDEX idx_required_docs_scheme ON required_documents (scheme_id);

-- ═══════════════════════════════════════════════════════════════════════════════
-- Seed: Required Documents for Initial Schemes
-- ═══════════════════════════════════════════════════════════════════════════════

DO $$
DECLARE
    pm_kisan_id      UUID;
    ayushman_id      UUID;
    pm_awas_id       UUID;
    scholarship_id   UUID;
    ujjwala_id       UUID;
BEGIN
    SELECT id INTO pm_kisan_id    FROM schemes WHERE short_name = 'PM-KISAN';
    SELECT id INTO ayushman_id    FROM schemes WHERE short_name = 'Ayushman Bharat';
    SELECT id INTO pm_awas_id     FROM schemes WHERE short_name = 'PM Awas Yojana';
    SELECT id INTO scholarship_id FROM schemes WHERE short_name = 'Post Matric Scholarship';
    SELECT id INTO ujjwala_id     FROM schemes WHERE short_name = 'Ujjwala';

    -- PM-KISAN
    INSERT INTO required_documents (scheme_id, document_type, description, sort_order) VALUES
    (pm_kisan_id, 'aadhaar_card',       'Aadhaar card for identity verification',      1),
    (pm_kisan_id, 'land_record',        'Land records / Khatauni (7/12 or similar)',   2),
    (pm_kisan_id, 'bank_passbook',      'Bank passbook for DBT transfer',              3);

    -- Ayushman Bharat
    INSERT INTO required_documents (scheme_id, document_type, description, sort_order) VALUES
    (ayushman_id, 'aadhaar_card',       'Aadhaar of all family members',                1),
    (ayushman_id, 'ration_card',        'Ration card / BPL certificate',                2),
    (ayushman_id, 'income_certificate', 'Income certificate',                           3);

    -- PM Awas Yojana
    INSERT INTO required_documents (scheme_id, document_type, description, sort_order) VALUES
    (pm_awas_id,  'aadhaar_card',       'Aadhaar card',                                 1),
    (pm_awas_id,  'income_certificate', 'Income certificate (annual)',                  2),
    (pm_awas_id,  'property_document',  'Land ownership document',                      3),
    (pm_awas_id,  'domicile_certificate','Domicile / residence certificate',            4),
    (pm_awas_id,  'self_declaration',   'Self-declaration of no pucca house',           5);

    -- Post Matric Scholarship
    INSERT INTO required_documents (scheme_id, document_type, description, sort_order) VALUES
    (scholarship_id, 'aadhaar_card',      'Aadhaar card',                               1),
    (scholarship_id, 'caste_certificate', 'Caste certificate (SC/ST/OBC)',              2),
    (scholarship_id, 'income_certificate','Family income certificate',                   3),
    (scholarship_id, 'mark_sheet',        'Previous year mark sheet',                    4),
    (scholarship_id, 'admission_letter',  'Current year admission / bonafide letter',    5),
    (scholarship_id, 'fee_receipt',       'Tuition fee receipt',                         6),
    (scholarship_id, 'bank_passbook',     'Student''s bank account (Jan Dhan OK)',       7);

    -- Ujjwala
    INSERT INTO required_documents (scheme_id, document_type, description, sort_order) VALUES
    (ujjwala_id,   'aadhaar_card',       'Aadhaar card',                                1),
    (ujjwala_id,   'ration_card',        'BPL ration card',                             2),
    (ujjwala_id,   'gas_agency_declaration','Declaration from gas agency of no existing LPG', 3),
    (ujjwala_id,   'self_declaration',   'Self-declaration form',                       4);
END $$;

-- ─── Applications (User → Scheme) ─────────────────────────────────────────────

CREATE TYPE application_status AS ENUM (
    'draft',                -- user started but not submitted
    'eligibility_pending',  -- waiting for eligibility check
    'eligible',             -- meets criteria, ready for documents
    'not_eligible',         -- does not meet criteria
    'documents_pending',    -- submitted, waiting for user docs
    'submitted',            -- application sent to govt portal
    'under_review',         -- being processed by department
    'approved',             -- benefit granted
    'rejected',             -- application rejected
    'appealed',             -- user appealed rejection
    'disbursed'             -- benefit paid/delivered
);

CREATE TABLE applications (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    scheme_id           UUID NOT NULL REFERENCES schemes(id) ON DELETE CASCADE,
    status              application_status NOT NULL DEFAULT 'draft',
    eligibility_result  JSONB,               -- snapshot: {passed, failed_rules: [{rule_id, reason}]}
    eligibility_checked_at TIMESTAMPTZ,
    application_data    JSONB,               -- form responses (scheme-specific fields)
    external_tracking_id TEXT,               -- application ID from the actual govt portal
    submitted_at        TIMESTAMPTZ,
    approved_at         TIMESTAMPTZ,
    rejection_reason    TEXT,
    channel             application_channel,
    assigned_agent_id   UUID,                -- CSC/helper who assisted
    language            TEXT DEFAULT 'hindi',
    created_at          TIMESTAMPTZ DEFAULT now(),
    updated_at          TIMESTAMPTZ DEFAULT now(),

    UNIQUE (user_id, scheme_id, status)      -- one active app per user per scheme
);

CREATE INDEX idx_applications_user    ON applications (user_id);
CREATE INDEX idx_applications_scheme  ON applications (scheme_id);
CREATE INDEX idx_applications_status  ON applications (status);

-- ─── User Documents ───────────────────────────────────────────────────────────

CREATE TABLE user_documents (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    application_id      UUID REFERENCES applications(id) ON DELETE SET NULL,
    document_type       document_type NOT NULL,
    file_url            TEXT NOT NULL,          -- S3 / blob storage URL
    file_hash           TEXT,                   -- SHA-256 for integrity
    file_size_bytes     INT,
    verification_status TEXT DEFAULT 'pending' CHECK (verification_status IN ('pending', 'verified', 'rejected', 'expired')),
    verified_at         TIMESTAMPTZ,
    expiry_date         DATE,                   -- for certificates with expiry
    uploaded_at         TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_user_docs_user  ON user_documents (user_id);
CREATE INDEX idx_user_docs_app   ON user_documents (application_id);

-- ─── Benefits / Disbursement Tracking ────────────────────────────────────────

CREATE TYPE disbursement_status AS ENUM (
    'pending',
    'processing',
    'completed',
    'failed',
    'cancelled'
);

CREATE TABLE benefits (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id      UUID NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    scheme_id           UUID NOT NULL REFERENCES schemes(id) ON DELETE CASCADE,
    installment_number  INT,                     -- for multi-installment schemes (PM-KISAN)
    amount_cents        BIGINT NOT NULL,         -- in paise
    disbursement_status disbursement_status DEFAULT 'pending',
    transaction_ref     TEXT,                    -- UTR / reference number
    disbursed_at        TIMESTAMPTZ,
    expected_date       DATE,
    notes               TEXT,
    created_at          TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_benefits_application ON benefits (application_id);
CREATE INDEX idx_benefits_user        ON benefits (user_id);

-- ─── Eligibility Check Log (audit trail) ─────────────────────────────────────

CREATE TABLE eligibility_check_log (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    scheme_id       UUID NOT NULL REFERENCES schemes(id) ON DELETE CASCADE,
    rule_id         UUID REFERENCES eligibility_rules(id),
    passed          BOOLEAN NOT NULL,
    actual_value    JSONB,                    -- what the user has
    expected_value  JSONB,                    -- what the rule requires
    details         TEXT,
    checked_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_elig_log_user   ON eligibility_check_log (user_id);
CREATE INDEX idx_elig_log_scheme ON eligibility_check_log (scheme_id);

-- ─── Scheme Notifications / Updates ──────────────────────────────────────────

CREATE TABLE scheme_updates (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scheme_id       UUID NOT NULL REFERENCES schemes(id) ON DELETE CASCADE,
    title           TEXT NOT NULL,
    body            TEXT NOT NULL,
    notification_type TEXT DEFAULT 'update' CHECK (notification_type IN ('update', 'deadline', 'new_scheme', 'document_reminder', 'status_change')),
    related_link    TEXT,
    published_at    TIMESTAMPTZ DEFAULT now(),
    expires_at      TIMESTAMPTZ
);

CREATE INDEX idx_scheme_updates ON scheme_updates (scheme_id, published_at DESC);

-- ─── Application History / Timeline ──────────────────────────────────────────

CREATE TABLE application_events (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id  UUID NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    event_type      TEXT NOT NULL,            -- status_change, document_uploaded, note_added, etc.
    old_status      application_status,
    new_status      application_status,
    metadata        JSONB,                    -- event-specific data
    created_by      TEXT DEFAULT 'system',    -- 'user', 'system', 'agent', 'govt_portal'
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_app_events ON application_events (application_id, created_at DESC);
