# How to Connect to Render Database and Run SQL

## Step 1: Get Your Connection String

1. In Render dashboard, click the **"Connect"** button
2. You'll see two tabs: **"Internal"** and **"External"**
3. For local connection, use **"External"** tab (if available)
4. Copy the connection string - it looks like:
   ```
   postgresql://dely_backend_user:password@host:port/database
   ```

## Step 2: Choose Your Method

### Method A: Using pgAdmin (Easiest - GUI) ⭐ Recommended

1. **Download pgAdmin**: https://www.pgadmin.org/download/
2. **Install and open pgAdmin**
3. **Add Server**:
   - Right-click "Servers" → "Register" → "Server"
   - **General Tab**: Name = "Render dely_backend"
   - **Connection Tab**:
     - **Host**: Extract from connection string (e.g., `dpg-d5b7cnf5r7bs73a75ss0-a.singapore-postgres.render.com`)
     - **Port**: `5432` (or check your connection string)
     - **Database**: `dely_backend` (or the database name in connection string)
     - **Username**: `dely_backend_user`
     - **Password**: The password from your connection string
   - Click "Save"
4. **Run SQL**:
   - Expand "Servers" → "Render dely_backend" → "Databases" → "dely_backend"
   - Right-click "dely_backend" → "Query Tool"
   - Paste the SQL from `render_fix_simple.sql`
   - Click "Execute" (or press F5)

### Method B: Using psql (Command Line)

**Windows (PowerShell):**
```powershell
# Install PostgreSQL client tools first if needed
# Then connect:
psql "postgresql://dely_backend_user:YOUR_PASSWORD@HOST:5432/dely_backend"

# Or set environment variable:
$env:PGPASSWORD="YOUR_PASSWORD"
psql -h HOST -U dely_backend_user -d dely_backend
```

**After connecting, paste the SQL commands from `render_fix_simple.sql`**

### Method C: Using DBeaver (Free GUI Tool)

1. **Download DBeaver**: https://dbeaver.io/download/
2. **Install and open DBeaver**
3. **New Database Connection**:
   - Click "New Database Connection" icon
   - Select "PostgreSQL"
   - Enter connection details from your Render connection string
   - Test connection
   - Click "Finish"
4. **Run SQL**:
   - Right-click your database → "SQL Editor" → "New SQL Script"
   - Paste SQL from `render_fix_simple.sql`
   - Click "Execute" button

### Method D: Using Online PostgreSQL Client

1. Go to https://adminer.org/ or https://www.elephantsql.com/ (if they support external connections)
2. Enter your Render connection details
3. Run the SQL

## Step 3: Extract Connection Details from Connection String

Your connection string format:
```
postgresql://USERNAME:PASSWORD@HOST:PORT/DATABASE
```

Example:
```
postgresql://dely_backend_user:HFunSem51X20W7u8XZ63G@dpg-d5b7cnf5r7bs73a75ss0-a.singapore-postgres.render.com:5432/dely_backend
```

Breakdown:
- **Username**: `dely_backend_user`
- **Password**: `HFunSem51X20W7u8XZ63G` (the part after the colon)
- **Host**: `dpg-d5b7cnf5r7bs73a75ss0-a.singapore-postgres.render.com`
- **Port**: `5432` (usually)
- **Database**: `dely_backend`

## Step 4: Run the SQL Fix

Once connected, copy and paste this SQL:

```sql
-- Step 1: Add lowercase enum values
DO $$
BEGIN
    BEGIN
        ALTER TYPE kycstatus ADD VALUE 'pending';
    EXCEPTION WHEN duplicate_object THEN
        NULL;
    END;
    
    BEGIN
        ALTER TYPE kycstatus ADD VALUE 'verified';
    EXCEPTION WHEN duplicate_object THEN
        NULL;
    END;
    
    BEGIN
        ALTER TYPE kycstatus ADD VALUE 'rejected';
    EXCEPTION WHEN duplicate_object THEN
        NULL;
    END;
    
    BEGIN
        ALTER TYPE kycstatus ADD VALUE 'not_verified';
    EXCEPTION WHEN duplicate_object THEN
        NULL;
    END;
END $$;

-- Step 2: Update existing records to lowercase
UPDATE users 
SET kyc_status = LOWER(kyc_status::text)::kycstatus
WHERE kyc_status::text != LOWER(kyc_status::text);

UPDATE kycs 
SET status = LOWER(status::text)::kycstatus
WHERE status::text != LOWER(status::text);
```

## Step 5: Verify It Worked

Run this query to check:

```sql
-- Check enum values
SELECT enumlabel FROM pg_enum 
WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'kycstatus')
ORDER BY enumlabel;
```

You should see: `not_verified`, `pending`, `verified`, `rejected` (and possibly uppercase versions).

## Troubleshooting

**Can't connect?**
- Make sure you're using the **External** connection string (not Internal)
- Check if your IP needs to be whitelisted (Render might require this)
- Verify the password is correct (copy the full connection string)

**Connection timeout?**
- Render free tier databases might have connection limits
- Try connecting during off-peak hours
- Check if the database is "Available" in the dashboard

**Permission denied?**
- Make sure you're using the database owner credentials
- The connection string should have full access

