# How to Authorize in Swagger UI

## 🔐 Quick Guide

### Step 1: Get Your Access Token

1. **For Admin Endpoints:**
   - Go to `POST /admin/auth/login` in Swagger UI
   - Click "Try it out"
   - Enter your admin credentials:
     ```json
     {
       "email": "your-admin@email.com",
       "password": "your-password"
     }
   - Click "Execute"
   - Copy the `token` from the response

2. **For User Endpoints:**
   - Go to `POST /api/v1/auth/login` in Swagger UI
   - Click "Try it out"
   - Enter your user credentials
   - Click "Execute"
   - Copy the `token` from the response

### Step 2: Authorize in Swagger UI

1. **Click the "Authorize" button** (🔒 lock icon) at the top right of Swagger UI

2. **In the Authorization modal:**
   - Find the "Bearer" security scheme
   - In the "Value" field, enter: `Bearer <your-token>`
   - Or just enter the token without "Bearer" prefix (it will be added automatically)
   
   Example:
   ```
   eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhZG1pbklkIjoiMTIzNCIsImVtYWlsIjoiYWRtaW5AZGVseS5jb20iLCJyb2xlIjoic3VwZXJfYWRtaW4ifQ...
   ```

3. **Click "Authorize"**

4. **Click "Close"**

### Step 3: Test Protected Endpoints

Now you can test any protected endpoint:
- All admin endpoints (`/admin/*`) will use your admin token
- All user endpoints (`/api/v1/*`) will use your user token
- The lock icon (🔒) next to endpoints indicates they require authentication

## 📝 Detailed Steps with Screenshots

### For Admin Panel Endpoints

1. **Login to get admin token:**
   ```
   POST /admin/auth/login
   {
     "email": "admin@dely.com",
     "password": "your-password"
   }
   ```

2. **Response will contain:**
   ```json
   {
     "success": true,
     "data": {
       "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
       "refreshToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
       "admin": { ... }
     }
   }
   ```

3. **Copy the `token` value**

4. **Click "Authorize" button** (top right)

5. **Paste token in the "Value" field**

6. **Click "Authorize" and "Close"**

7. **Now test any admin endpoint** - it will automatically include the token!

### For User Endpoints

Same process, but use:
```
POST /api/v1/auth/login
```

## 🔄 Token Refresh

If your token expires:

1. Use `POST /admin/auth/refresh-token` (for admin) or `POST /api/v1/auth/refresh-token` (for users)
2. Send your `refreshToken` from the login response
3. Get a new `token`
4. Update the token in Swagger's Authorize dialog

## ⚠️ Important Notes

1. **Token Format**: 
   - You can enter just the token: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`
   - Or with Bearer prefix: `Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`
   - Swagger will handle both formats

2. **Token Expiration**:
   - Admin tokens expire in 24 hours (1440 minutes)
   - User tokens expire in 24 hours
   - Refresh tokens expire in 7 days

3. **Different Tokens for Different Endpoints**:
   - Admin endpoints require admin token (from `/admin/auth/login`)
   - User endpoints require user token (from `/api/v1/auth/login`)
   - You can have both authorized at the same time in Swagger

4. **Logout**:
   - Use `POST /admin/auth/logout` or `POST /api/v1/auth/logout` to invalidate tokens

## 🎯 Quick Reference

| Endpoint Type | Login Endpoint | Token Type |
|--------------|----------------|------------|
| Admin | `POST /admin/auth/login` | Admin JWT |
| User | `POST /api/v1/auth/login` | User JWT |

## 🐛 Troubleshooting

### Problem: "401 Unauthorized" even after authorizing

**Possible causes:**
1. **Token expired** - Check token expiration time
   - Solution: Get a new token from login endpoint
   
2. **Wrong token format** - Token not being sent correctly
   - Solution: In Swagger Authorize dialog, enter ONLY the token (without "Bearer")
   - Example: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`
   - Swagger automatically adds "Bearer " prefix
   
3. **Using refresh token instead of access token**
   - Solution: Use `token` from login response, NOT `refreshToken`
   - Access token is for API requests
   - Refresh token is only for getting new tokens

4. **Admin not found or inactive**
   - Solution: Verify admin exists in database and is active
   - Check: `is_active = True` for your admin account

5. **UUID conversion issue** (Fixed in latest code)
   - Solution: This has been fixed. Restart your server if you see this error.

**Quick fix checklist:**
- [ ] Token is from `POST /admin/auth/login` (not refresh token)
- [ ] Token is not expired (check `exp` in JWT payload)
- [ ] Entered token in Swagger Authorize dialog (without "Bearer" prefix)
- [ ] Clicked "Authorize" and "Close" buttons
- [ ] Admin exists in database and is active
- [ ] Server restarted after code changes

### Problem: "403 Forbidden" 
- **Solution**: Your role doesn't have permission. Check role requirements for the endpoint.
- **Check your role**: Look at `role` field in token payload
- **Required role**: Check endpoint documentation or source code

### Problem: Can't see "Authorize" button
- **Solution**: Make sure `DEBUG=True` in your config (docs are disabled in production)
- **Check**: `app/config.py` - `DEBUG: bool = True`
- **Restart**: Server after changing config

### Problem: Token not being sent
- **Solution**: 
  1. Click "Authorize" button again
  2. Verify token is in the "Authorized" list
  3. Check "Authorize" button shows a lock icon (not open)
  4. Try the request again

### Testing Authorization Manually

**Using curl:**
```bash
curl -X GET "http://localhost:8000/admin/auth/me" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

**Using Python:**
```python
import requests

token = "your-token-here"
headers = {"Authorization": f"Bearer {token}"}
response = requests.get("http://localhost:8000/admin/auth/me", headers=headers)
print(response.json())
```

## 💡 Pro Tips

1. **Bookmark the token**: Keep your token handy for quick testing
2. **Use different browsers/tabs**: Test with different user roles simultaneously
3. **Check token in Network tab**: Verify the Authorization header is being sent
4. **Use Postman/Insomnia**: For more advanced testing, these tools also support Bearer tokens

