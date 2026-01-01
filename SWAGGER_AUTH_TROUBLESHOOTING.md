# Swagger Authorization Troubleshooting

## Common Issues and Solutions

### Issue 1: "401 Unauthorized" After Adding Token

**Symptoms:**
- Token is valid (can decode it)
- Added token in Swagger Authorize button
- Still getting 401 Unauthorized

**Possible Causes & Solutions:**

#### 1. Token Format Issue
**Problem:** Token not being sent correctly

**Solution:**
- In Swagger's Authorize dialog, enter ONLY the token (without "Bearer" prefix)
- Example: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`
- Swagger will automatically add "Bearer " prefix

#### 2. Token Expired
**Problem:** Token has expired

**Solution:**
- Check token expiration: `exp` field in JWT payload
- Get a new token from login endpoint
- Update token in Swagger Authorize dialog

#### 3. Wrong Token Type
**Problem:** Using refresh token instead of access token

**Solution:**
- Use `token` (access token), NOT `refreshToken`
- Access token is used for API requests
- Refresh token is only for getting new access tokens

#### 4. Admin Not Found in Database
**Problem:** Admin ID in token doesn't match database

**Solution:**
- Verify admin exists: Check database
- Token contains: `adminId: "3526b6e5-1173-4805-8969-fed7ced70691"`
- Make sure this admin exists and is active

#### 5. UUID Type Mismatch (Fixed)
**Problem:** String UUID vs UUID object mismatch

**Solution:**
- This has been fixed in `app/api/admin_deps.py`
- Token string UUID is now converted to UUID object before querying

### Issue 2: Token Not Being Sent

**Symptoms:**
- Authorized in Swagger
- Request doesn't include Authorization header

**Solution:**
1. Click "Authorize" button again
2. Verify token is in the "Authorized" list
3. Check "Authorize" button shows a lock icon (not open)
4. Try the request again

### Issue 3: 403 Forbidden

**Symptoms:**
- Getting 403 instead of 401
- Token is valid

**Solution:**
- Check your admin role
- Endpoint might require higher role (e.g., Super Admin)
- Your role: Check in token payload (`role` field)
- Required role: Check endpoint documentation

### Issue 4: Can't See Authorize Button

**Symptoms:**
- No "Authorize" button in Swagger UI

**Solution:**
- Make sure `DEBUG=True` in your config
- Docs are disabled when `DEBUG=False`
- Restart server after changing config

## Step-by-Step Debugging

### 1. Verify Token is Valid
```python
from jose import jwt
from app.config import settings

token = "your-token-here"
try:
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    print("Token valid:", payload)
    print("Admin ID:", payload.get("adminId"))
    print("Role:", payload.get("role"))
except Exception as e:
    print("Token invalid:", e)
```

### 2. Verify Admin Exists
```python
from app.database import SessionLocal
from app.models.admin import Admin
from uuid import UUID

db = SessionLocal()
admin_id = UUID("3526b6e5-1173-4805-8969-fed7ced70691")
admin = db.query(Admin).filter(Admin.id == admin_id).first()
print("Admin exists:", admin is not None)
print("Admin active:", admin.is_active if admin else None)
```

### 3. Test Authorization Manually
```python
from app.api.admin_deps import get_current_admin
from app.database import get_db

# This should work if token is valid
# (Run in FastAPI request context)
```

## Quick Fix Checklist

- [ ] Token is from `POST /admin/auth/login` (not refresh token)
- [ ] Token is not expired (check `exp` in payload)
- [ ] Entered token in Swagger Authorize dialog
- [ ] Clicked "Authorize" and "Close" buttons
- [ ] Admin exists in database
- [ ] Admin is active (`is_active = True`)
- [ ] Admin role matches endpoint requirements
- [ ] Server restarted after code changes
- [ ] `DEBUG=True` in config (for Swagger UI)

## Testing Authorization

### Using curl
```bash
curl -X GET "http://localhost:8000/admin/auth/me" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### Using Python requests
```python
import requests

token = "your-token-here"
headers = {"Authorization": f"Bearer {token}"}
response = requests.get("http://localhost:8000/admin/auth/me", headers=headers)
print(response.json())
```

## Still Not Working?

1. **Check server logs** - Look for error messages
2. **Verify SECRET_KEY** - Must match the one used to create token
3. **Check database connection** - Admin query might be failing
4. **Verify endpoint requires auth** - Some endpoints might be public
5. **Check CORS settings** - Might be blocking requests

## Common Error Messages

| Error | Meaning | Solution |
|-------|---------|----------|
| "Could not validate credentials" | Token invalid/expired | Get new token |
| "Admin account is inactive" | Admin disabled | Activate admin |
| "Access denied" | Wrong role | Check role requirements |
| "Not authenticated" | No token sent | Add token in Swagger |

