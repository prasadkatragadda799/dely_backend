-- Fix kycstatus enum to include lowercase values
-- This script adds the lowercase enum values that are missing from the database
-- Run this on your PostgreSQL database

-- Add lowercase enum values if they don't already exist
DO $$
BEGIN
    -- Add 'pending' if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM pg_enum 
        WHERE enumlabel = 'pending' 
        AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'kycstatus')
    ) THEN
        ALTER TYPE kycstatus ADD VALUE 'pending';
    END IF;
    
    -- Add 'verified' if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM pg_enum 
        WHERE enumlabel = 'verified' 
        AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'kycstatus')
    ) THEN
        ALTER TYPE kycstatus ADD VALUE 'verified';
    END IF;
    
    -- Add 'rejected' if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM pg_enum 
        WHERE enumlabel = 'rejected' 
        AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'kycstatus')
    ) THEN
        ALTER TYPE kycstatus ADD VALUE 'rejected';
    END IF;
    
    -- Add 'not_verified' if it doesn't exist (should already exist from previous migration)
    IF NOT EXISTS (
        SELECT 1 FROM pg_enum 
        WHERE enumlabel = 'not_verified' 
        AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'kycstatus')
    ) THEN
        ALTER TYPE kycstatus ADD VALUE 'not_verified';
    END IF;
END $$;

-- Update existing records to use lowercase enum values
-- This converts uppercase values (PENDING, VERIFIED, REJECTED) to lowercase (pending, verified, rejected)
UPDATE users 
SET kyc_status = LOWER(kyc_status::text)::kycstatus
WHERE kyc_status::text != LOWER(kyc_status::text);

-- Update KYC records to use lowercase enum values
UPDATE kycs 
SET status = LOWER(status::text)::kycstatus
WHERE status::text != LOWER(status::text);

