-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Tenants Table
CREATE TABLE tenants (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Properties Table - FIXED
CREATE TABLE properties (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,  -- Use UUID, no more duplicate IDs!
    tenant_id TEXT NOT NULL REFERENCES tenants(id),
    property_code TEXT NOT NULL,  -- Store the original "101" as a code, not as ID
    name TEXT NOT NULL,
    timezone TEXT NOT NULL DEFAULT 'UTC',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(tenant_id, property_code)  -- Ensure uniqueness per tenant
);

-- Reservations Table - FIXED
CREATE TABLE reservations (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    property_id UUID NOT NULL REFERENCES properties(id),
    tenant_id TEXT NOT NULL REFERENCES tenants(id),
    check_in_date TIMESTAMP WITH TIME ZONE NOT NULL,
    check_out_date TIMESTAMP WITH TIME ZONE NOT NULL,
    total_amount NUMERIC(10, 2) NOT NULL,  -- CHANGED to 2 decimal places!
    currency TEXT DEFAULT 'USD',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add indexes for performance
CREATE INDEX idx_reservations_tenant_id ON reservations(tenant_id);
CREATE INDEX idx_reservations_property_id ON reservations(property_id);
CREATE INDEX idx_reservations_dates ON reservations(check_in_date, check_out_date);

-- RLS Policies (Simulation)
ALTER TABLE properties ENABLE ROW LEVEL SECURITY;
ALTER TABLE reservations ENABLE ROW LEVEL SECURITY;

-- Create policy to ensure tenant isolation
CREATE POLICY tenant_isolation_properties ON properties
    USING (tenant_id = current_setting('app.current_tenant')::TEXT);

CREATE POLICY tenant_isolation_reservations ON reservations
    USING (tenant_id = current_setting('app.current_tenant')::TEXT);