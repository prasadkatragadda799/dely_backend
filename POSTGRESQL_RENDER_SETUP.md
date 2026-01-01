# PostgreSQL on Render - Configuration Guide

## ✅ Current Configuration

Your backend is now optimized for PostgreSQL on Render:

### 1. Database Connection
- ✅ `app/database.py` automatically converts `postgres://` to `postgresql://` (Render format)
- ✅ Connection pooling configured for PostgreSQL (pool_size=10, max_overflow=20)
- ✅ `pool_pre_ping=True` for connection health checks

### 2. Database Driver
- ✅ `psycopg2-binary==2.9.9` in requirements.txt (PostgreSQL adapter)
- ✅ Pre-compiled binary (no compilation needed)

### 3. Migrations
- ✅ `migrations/env.py` handles PostgreSQL URL conversion
- ✅ Migrations use proper UUID types for PostgreSQL
- ✅ Auto-runs during build: `alembic upgrade head`

### 4. Models
- ✅ All models use `UUID(as_uuid=True)` for PostgreSQL
- ✅ Proper foreign key relationships
- ✅ Indexes configured for performance

## 🚀 Render Configuration

### render.yaml
```yaml
databases:
  - name: dely-db
    databaseName: dely_db
    user: dely_user
    plan: free  # or paid for production

services:
  - type: web
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: dely-db
          property: connectionString  # Auto-connects to PostgreSQL
```

## 📋 Deployment Checklist

### Before Deploying:
- [x] `psycopg2-binary` in requirements.txt
- [x] Database connection handling in `app/database.py`
- [x] Migration auto-run in build command
- [x] PostgreSQL database configured in render.yaml

### After Deployment:
1. **Verify Database Connection**
   - Check service logs for connection success
   - No "connection refused" errors

2. **Verify Migrations**
   - Check build logs for "Running upgrade"
   - All tables should be created

3. **Test Database**
   - Create admin user: `python create_admin.py` (in Shell)
   - Test API endpoints that use database

## 🔧 PostgreSQL-Specific Features

### UUID Support
- PostgreSQL natively supports UUID type
- Models use `UUID(as_uuid=True)` for proper UUID handling
- No string conversion needed (unlike SQLite)

### Connection Pooling
- Configured for production use
- Handles concurrent requests efficiently
- Auto-reconnects on connection loss

### Performance
- Indexes on frequently queried columns
- Foreign key constraints for data integrity
- Proper data types (no string UUIDs)

## 🐛 Troubleshooting

### Connection Issues
**Error**: `connection to server at "localhost" failed`
- **Fix**: Ensure `DATABASE_URL` uses Render's internal database URL
- Check environment variables in Render dashboard

### Migration Errors
**Error**: `relation "table_name" does not exist`
- **Fix**: Run migrations manually in Shell:
  ```bash
  alembic upgrade head
  ```

### UUID Type Errors
**Error**: `can't adapt type 'UUID'`
- **Fix**: Already handled - models use proper UUID types
- PostgreSQL natively supports UUID

### Pool Exhaustion
**Error**: `QueuePool limit of size X overflow Y reached`
- **Fix**: Increase pool size in `app/database.py`:
  ```python
  pool_size=20,  # Increase from 10
  max_overflow=40  # Increase from 20
  ```

## 📊 Database Management

### View Database in Render
1. Go to your database service
2. Click "Connect" → "External Connection"
3. Use connection string with pgAdmin or psql

### Backup Database
Render automatically backs up PostgreSQL databases:
- Free tier: Daily backups (7 days retention)
- Paid tier: More frequent backups

### Monitor Database
- View metrics in Render dashboard
- Connection count, query performance
- Storage usage

## 🔐 Security Notes

1. **Internal URL**: Always use internal database URL (faster, free)
2. **Connection String**: Automatically set by Render (secure)
3. **No Public Access**: Database is private by default
4. **SSL**: Connections are encrypted automatically

## 📈 Performance Tips

1. **Indexes**: Already configured on key columns
2. **Connection Pooling**: Configured for optimal performance
3. **Query Optimization**: Use `joinedload` for relationships
4. **Database Size**: Monitor in Render dashboard

## ✅ Your Setup is Ready!

Everything is configured for PostgreSQL on Render. Just:
1. Push your code to GitHub
2. Deploy using Render Blueprint (render.yaml)
3. Render will automatically:
   - Create PostgreSQL database
   - Connect web service to database
   - Run migrations
   - Start your API

No additional configuration needed! 🎉

