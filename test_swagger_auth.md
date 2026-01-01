# Testing Swagger Authorization - Step by Step

## ✅ Backend is Working!
The curl test confirmed the backend authentication is working correctly.

## 🔍 Debugging Steps

### Step 1: Clear Browser Cache
1. Open Swagger UI: `http://localhost:8000/docs`
2. Press `Ctrl+Shift+R` (or `Cmd+Shift+R` on Mac) to hard refresh
3. This clears cached OpenAPI schema

### Step 2: Check Authorize Button
1. Look for the **"Authorize"** button (🔒 lock icon) at the top right
2. If you don't see it, check:
   - `DEBUG=True` in config
   - Server is running
   - Hard refresh the page

### Step 3: Enter Token Correctly
1. Click **"Authorize"** button
2. You should see a dialog with security schemes
3. Look for **"Bearer"** or **"OAuth2PasswordBearer"**
4. In the **Value** field, enter **ONLY the token** (without "Bearer"):
   ```
   eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhZG1pbklkIjoiMzUyNmI2ZTUtMTE3My00ODA1LTg5NjktZmVkN2NlZDcwNjkxIiwiZW1haWwiOiJhZG1pbkBkZWx5LmNvbSIsInJvbGUiOiJzdXBlcl9hZG1pbiIsImV4cCI6MTc2NzM1NzYxNiwiaWF0IjoxNzY3MjcxMjE2fQ.tKnxtIaSSwrnVTx_haJF5b-oCifzpPNDC317aK65fbo
   ```
5. **DO NOT** add "Bearer " prefix - Swagger adds it automatically
6. Click **"Authorize"**
7. Click **"Close"**

### Step 4: Test Endpoint
1. Find `GET /admin/auth/me` endpoint
2. Click **"Try it out"**
3. Click **"Execute"**
4. Check the response

### Step 5: Check Network Tab (if still failing)
1. Open browser DevTools (F12)
2. Go to **Network** tab
3. Try the request again
4. Click on the request to `/admin/auth/me`
5. Check **Headers** tab
6. Look for `Authorization` header
7. It should be: `Authorization: Bearer <your-token>`

## 🐛 Common Issues

### Issue: "401 Unauthorized" in Swagger but curl works
**Cause:** Token not being sent correctly from Swagger UI

**Solutions:**
1. Make sure you clicked "Authorize" and "Close"
2. Check if token has spaces or line breaks
3. Try copying token again from login response
4. Hard refresh Swagger UI (Ctrl+Shift+R)

### Issue: No "Authorize" button
**Cause:** Swagger UI not loading security schemes

**Solutions:**
1. Check `DEBUG=True` in `app/config.py`
2. Restart server
3. Clear browser cache
4. Check browser console for errors

### Issue: Token field is empty after authorizing
**Cause:** Token not saved in Swagger UI

**Solutions:**
1. Make sure you clicked "Authorize" (not just entered token)
2. Check if there are multiple security schemes - use the correct one
3. Try refreshing the page and re-authorizing

## 🧪 Manual Test (Alternative)

If Swagger UI continues to have issues, use these alternatives:

### Using curl:
```bash
curl -X GET "http://localhost:8000/admin/auth/me" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### Using Python:
```python
import requests

token = "your-token-here"
headers = {"Authorization": f"Bearer {token}"}
response = requests.get("http://localhost:8000/admin/auth/me", headers=headers)
print(response.json())
```

### Using Postman/Insomnia:
1. Create new request to `GET http://localhost:8000/admin/auth/me`
2. Go to **Authorization** tab
3. Select **Bearer Token**
4. Paste your token
5. Send request

## ✅ Verification

If everything works, you should see:
```json
{
  "success": true,
  "data": {
    "id": "3526b6e5-1173-4805-8969-fed7ced70691",
    "email": "admin@dely.com",
    "name": "Raju",
    "role": "super_admin",
    "avatar": null
  },
  "message": "Admin information retrieved successfully",
  "error": null
}
```

