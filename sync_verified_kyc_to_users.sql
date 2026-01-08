-- Sync Verified KYC Submissions to User Profiles
-- Run this AFTER adding lowercase enum values
-- This updates users who have verified KYC submissions but their profile still shows "pending"

-- Step 1: Update users who have verified KYC submissions
UPDATE users u
SET 
    kyc_status = 'verified',
    kyc_verified_at = k.verified_at,
    kyc_verified_by = NULL  -- Set to NULL if you want to clear it, or keep existing value
FROM kycs k
WHERE 
    k.user_id::text = u.id::text
    AND k.status = 'verified'  -- or 'VERIFIED' if uppercase
    AND u.kyc_status != 'verified';  -- Only update if not already verified

-- Step 2: Update users who have rejected KYC submissions
UPDATE users u
SET 
    kyc_status = 'rejected'
FROM kycs k
WHERE 
    k.user_id::text = u.id::text
    AND k.status = 'rejected'  -- or 'REJECTED' if uppercase
    AND u.kyc_status != 'rejected';  -- Only update if not already rejected

-- Step 3: Verify the sync
SELECT 
    u.id,
    u.email,
    u.kyc_status as user_kyc_status,
    k.status as kyc_submission_status,
    k.verified_at
FROM users u
JOIN kycs k ON k.user_id::text = u.id::text
WHERE k.status = 'verified' OR k.status = 'VERIFIED'
ORDER BY k.verified_at DESC;

