-- ==============================================================================
-- CIPHERGUARD: Production Database Schema (Supabase PostgreSQL)
-- NITDA/ICSC Track G Challenge: "Watching What Third Party Integrations Really Do"
-- ==============================================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ------------------------------------------------------------------------------
-- 1. Organizations (Multi-Tenancy Foundation)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    plan VARCHAR(50) NOT NULL DEFAULT 'enterprise',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ------------------------------------------------------------------------------
-- 2. User Profiles & RBAC
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.user_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    role VARCHAR(50) NOT NULL DEFAULT 'security_analyst' CHECK (role IN ('admin', 'security_analyst', 'auditor', 'viewer')),
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_profiles_org_email ON public.user_profiles (organization_id, email);

-- ------------------------------------------------------------------------------
-- 3. Third-Party Integrations Inventory
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.integrations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    slug VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL DEFAULT 'Shipping' CHECK (category IN ('Shipping', 'Payments', 'Messaging', 'AI', 'Analytics', 'Authentication', 'Cloud', 'Other')),
    upstream_url TEXT,
    base_url TEXT,
    auth_type VARCHAR(50) NOT NULL DEFAULT 'none' CHECK (auth_type IN ('none', 'api_key', 'bearer_token', 'basic_auth')),
    auth_header_name VARCHAR(100) DEFAULT 'Authorization',
    auth_credential TEXT,
    status VARCHAR(50) NOT NULL DEFAULT 'monitoring' CHECK (status IN ('active', 'monitoring', 'restricted', 'paused')),
    risk_score INTEGER NOT NULL DEFAULT 15 CHECK (risk_score >= 0 AND risk_score <= 100),
    risk_level VARCHAR(20) NOT NULL DEFAULT 'low' CHECK (risk_level IN ('low', 'medium', 'high', 'critical')),
    description TEXT,
    metadata JSONB DEFAULT '{}'::JSONB,
    observed_endpoints_count INTEGER NOT NULL DEFAULT 0,
    last_activity_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_org_integration_slug UNIQUE (organization_id, slug)
);

CREATE INDEX IF NOT EXISTS idx_integrations_org_status ON public.integrations (organization_id, status);
CREATE INDEX IF NOT EXISTS idx_integrations_org_risk ON public.integrations (organization_id, risk_score DESC);

-- ------------------------------------------------------------------------------
-- 4. Integration Security Policies
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.integration_policies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    integration_id UUID NOT NULL REFERENCES public.integrations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    allowed_methods TEXT[] NOT NULL DEFAULT ARRAY['GET'],
    allowed_endpoints TEXT[] NOT NULL DEFAULT ARRAY['/*'],
    blocked_endpoints TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    rate_limit_rpm INTEGER DEFAULT 120,
    is_active BOOLEAN NOT NULL DEFAULT true,
    action_on_violation VARCHAR(50) NOT NULL DEFAULT 'alert' CHECK (action_on_violation IN ('alert', 'block', 'log')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_policies_org_integration ON public.integration_policies (organization_id, integration_id);

-- ------------------------------------------------------------------------------
-- 5. Integration Telemetry Events
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.integration_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES public.organizations(id) ON DELETE CASCADE,
    integration_id UUID REFERENCES public.integrations(id) ON DELETE SET NULL,
    integration_name VARCHAR(100) NOT NULL,
    method VARCHAR(10) NOT NULL,
    endpoint TEXT NOT NULL,
    action VARCHAR(100),
    resource VARCHAR(100),
    status_code INTEGER NOT NULL,
    latency_ms INTEGER DEFAULT 45,
    decision VARCHAR(20) NOT NULL DEFAULT 'ALLOW' CHECK (decision IN ('ALLOW', 'BLOCK', 'FLAG')),
    matched_policies TEXT[] DEFAULT ARRAY[]::TEXT[],
    reason TEXT,
    threat_classification VARCHAR(100),
    client_ip VARCHAR(50),
    risk_score INTEGER DEFAULT 0,
    risk_level VARCHAR(20) NOT NULL DEFAULT 'low' CHECK (risk_level IN ('low', 'medium', 'high', 'critical')),
    is_violation BOOLEAN NOT NULL DEFAULT false,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Idempotent Column Additions for existing Supabase databases
ALTER TABLE public.integration_events ADD COLUMN IF NOT EXISTS decision VARCHAR(20) DEFAULT 'ALLOW';
ALTER TABLE public.integration_events ADD COLUMN IF NOT EXISTS matched_policies TEXT[] DEFAULT ARRAY[]::TEXT[];
ALTER TABLE public.integration_events ADD COLUMN IF NOT EXISTS reason TEXT;
ALTER TABLE public.integration_events ADD COLUMN IF NOT EXISTS threat_classification VARCHAR(100);
ALTER TABLE public.integration_events ADD COLUMN IF NOT EXISTS client_ip VARCHAR(50);
ALTER TABLE public.integration_events ADD COLUMN IF NOT EXISTS risk_score INTEGER DEFAULT 0;

CREATE INDEX IF NOT EXISTS idx_events_org_integration ON public.integration_events (organization_id, integration_name, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON public.integration_events (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_events_violations ON public.integration_events (organization_id, is_violation) WHERE is_violation = true;
CREATE INDEX IF NOT EXISTS idx_events_decision ON public.integration_events (organization_id, decision);

-- ------------------------------------------------------------------------------
-- 6. Security Alerts & Anomaly Violations
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    integration_id UUID REFERENCES public.integrations(id) ON DELETE CASCADE,
    event_id UUID REFERENCES public.integration_events(id) ON DELETE SET NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    severity VARCHAR(20) NOT NULL DEFAULT 'medium' CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    category VARCHAR(50) NOT NULL DEFAULT 'policy_violation' CHECK (category IN ('policy_violation', 'anomaly', 'unauthorized_endpoint', 'unusual_volume', 'sensitive_data_exposure', 'server_error_spike')),
    status VARCHAR(30) NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'investigating', 'resolved', 'dismissed')),
    rule_violated TEXT,
    remediation TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_alerts_org_status ON public.alerts (organization_id, status, severity);

-- ------------------------------------------------------------------------------
-- 7. Security Scans & Integration Audits
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.scans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    integration_id UUID REFERENCES public.integrations(id) ON DELETE SET NULL,
    target_name VARCHAR(255) NOT NULL,
    target_url TEXT NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    findings_count INTEGER DEFAULT 0,
    score INTEGER DEFAULT 100,
    summary JSONB DEFAULT '{}'::jsonb,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_scans_org_status ON public.scans (organization_id, status, created_at DESC);

-- ------------------------------------------------------------------------------
-- Row Level Security (RLS) Configuration
-- ------------------------------------------------------------------------------
ALTER TABLE public.organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.integrations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.integration_policies ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.integration_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.scans ENABLE ROW LEVEL SECURITY;

-- Permissive development & service-role policies (Allows API server using service_role or authenticated key full control)
CREATE POLICY "Allow public/service read organizations" ON public.organizations FOR SELECT USING (true);
CREATE POLICY "Allow public/service insert organizations" ON public.organizations FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow public/service update organizations" ON public.organizations FOR UPDATE USING (true);

CREATE POLICY "Allow public/service read user_profiles" ON public.user_profiles FOR SELECT USING (true);
CREATE POLICY "Allow public/service insert user_profiles" ON public.user_profiles FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow public/service update user_profiles" ON public.user_profiles FOR UPDATE USING (true);

CREATE POLICY "Allow public/service read integrations" ON public.integrations FOR SELECT USING (true);
CREATE POLICY "Allow public/service insert integrations" ON public.integrations FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow public/service update integrations" ON public.integrations FOR UPDATE USING (true);
CREATE POLICY "Allow public/service delete integrations" ON public.integrations FOR DELETE USING (true);

CREATE POLICY "Allow public/service read policies" ON public.integration_policies FOR SELECT USING (true);
CREATE POLICY "Allow public/service insert policies" ON public.integration_policies FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow public/service update policies" ON public.integration_policies FOR UPDATE USING (true);
CREATE POLICY "Allow public/service delete policies" ON public.integration_policies FOR DELETE USING (true);

CREATE POLICY "Allow public/service read events" ON public.integration_events FOR SELECT USING (true);
CREATE POLICY "Allow public/service insert events" ON public.integration_events FOR INSERT WITH CHECK (true);

CREATE POLICY "Allow public/service read alerts" ON public.alerts FOR SELECT USING (true);
CREATE POLICY "Allow public/service insert alerts" ON public.alerts FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow public/service update alerts" ON public.alerts FOR UPDATE USING (true);

CREATE POLICY "Allow public/service read scans" ON public.scans FOR SELECT USING (true);
CREATE POLICY "Allow public/service insert scans" ON public.scans FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow public/service update scans" ON public.scans FOR UPDATE USING (true);

-- ------------------------------------------------------------------------------
-- Seed Default Organization & Baseline Integrations (Demo Data)
-- ------------------------------------------------------------------------------
DO $$
DECLARE
    default_org_id UUID := 'a0000000-0000-0000-0000-000000000001';
    shipfast_int_id UUID := 'b0000000-0000-0000-0000-000000000001';
    payflex_int_id UUID := 'b0000000-0000-0000-0000-000000000002';
    twilio_int_id UUID := 'b0000000-0000-0000-0000-000000000003';
BEGIN
    -- 1. Insert Default Organization
    INSERT INTO public.organizations (id, name, slug, plan)
    VALUES (default_org_id, 'NITDA Defense Corp', 'nitda-defense', 'enterprise')
    ON CONFLICT (id) DO NOTHING;

    -- 2. Insert Default Admin Profile
    INSERT INTO public.user_profiles (id, organization_id, email, full_name, role)
    VALUES (
        'c0000000-0000-0000-0000-000000000001',
        default_org_id,
        'security@cipherguard.io',
        'Lead SecOps Engineer',
        'admin'
    ) ON CONFLICT (id) DO NOTHING;

    -- 3. Insert Baseline Integrations (Logistics & Payments)
    INSERT INTO public.integrations (id, organization_id, name, slug, category, upstream_url, base_url, auth_type, auth_header_name, auth_credential, status, risk_score, risk_level, description, observed_endpoints_count)
    VALUES 
        (shipfast_int_id, default_org_id, 'ShipFast Logistics', 'shipfast', 'Shipping', 'http://shipfast-api:8000', 'http://shipfast-api:8000', 'none', 'Authorization', NULL, 'active', 15, 'low', 'Simulated third-party delivery partner API for package tracking and dispatch.', 2),
        (payflex_int_id, default_org_id, 'PayFlex Payments', 'payflex', 'Payments', 'http://payflex-api:8000', 'http://payflex-api:8000', 'api_key', 'X-API-Key', 'pf_live_sec_demo12345', 'active', 12, 'low', 'Simulated third-party payment gateway integration.', 3),
        (twilio_int_id, default_org_id, 'Twilio Communications', 'twilio', 'Messaging', 'https://api.twilio.com', 'https://api.twilio.com', 'bearer_token', 'Authorization', 'tw_token_secret', 'monitoring', 35, 'medium', 'SMS & WhatsApp dispatch integration.', 3)
    ON CONFLICT (id) DO NOTHING;

    -- 4. Insert Security Policy for ShipFast (Blocks /admin/*)
    INSERT INTO public.integration_policies (
        organization_id, integration_id, name, description, 
        allowed_methods, allowed_endpoints, blocked_endpoints, rate_limit_rpm, is_active, action_on_violation
    )
    VALUES (
        default_org_id,
        shipfast_int_id,
        'ShipFast Strict Read Policy',
        'Restricts ShipFast integration to read-only queries on orders and customer shipping addresses. Blocks administrative and export endpoints.',
        ARRAY['GET', 'POST'],
        ARRAY['/orders', '/orders/*', '/customers/*/address'],
        ARRAY['/admin/*', '/export/*', '/billing/*', '/internal/*'],
        120,
        true,
        'block'
    )
    ON CONFLICT DO NOTHING;

    -- 5. Insert Security Policy for PayFlex (Blocks /admin/*, /vault/*)
    INSERT INTO public.integration_policies (
        organization_id, integration_id, name, description, 
        allowed_methods, allowed_endpoints, blocked_endpoints, rate_limit_rpm, is_active, action_on_violation
    )
    VALUES (
        default_org_id,
        payflex_int_id,
        'PayFlex Transaction Safety Policy',
        'Restricts PayFlex payment integration to authorized checkout and charge endpoints. Blocks internal key vault and administrative routes.',
        ARRAY['GET', 'POST'],
        ARRAY['/payments', '/payments/*', '/charge', '/health'],
        ARRAY['/admin/*', '/vault/*', '/keys/*'],
        120,
        true,
        'block'
    )
    ON CONFLICT DO NOTHING;

END $$;

