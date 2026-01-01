# Admin Credentials via Environment Variables

## Overview
The backend now supports creating the first admin user automatically using environment variables. This is especially useful for Render deployment where you can't run interactive scripts.

## Environment Variables

Add these to your Render service environment variables:

```
ADMIN_EMAIL=admin@dely.com
ADMIN_PASSWORD=your_secure_password_here
ADMIN_NAME=Admin User
ADMIN_ROLE=super_admin
```

### Variable Details

- **ADMIN_EMAIL** (required): Email address for the admin user
- **ADMIN_PASSWORD** (required): Password (minimum 6 characters)
- **ADMIN_NAME** (optional): Name of the admin user (defaults to "Admin")
- **ADMIN_ROLE** (optional): Role for the admin user. Options:
  - `super_admin` (default) - Full access
  - `admin` - All CRUD except admin management
  - `manager` - Product, Order, KYC management
  - `support` - View only, order status updates

## How It Works

1. **During Startup**: The `start.sh` script checks if `ADMIN_EMAIL` and `ADMIN_PASSWORD` are set
2. **Auto-Creation**: If credentials are provided and no admin exists, it automatically creates the admin user
3. **Safety**: If an admin with that email already exists, it skips creation

## Setting Up on Render

### Step 1: Add Environment Variables

1. Go to Render Dashboard → Your Web Service
2. Go to **Environment** tab
3. Click **"Add Environment Variable"**
4. Add each variable:
   - Key: `ADMIN_EMAIL`, Value: `admin@dely.com`
   - Key: `ADMIN_PASSWORD`, Value: `your_secure_password`
   - Key: `ADMIN_NAME`, Value: `Admin User` (optional)
   - Key: `ADMIN_ROLE`, Value: `super_admin` (optional)

### Step 2: Deploy

After adding the variables, the admin will be created automatically on the next deployment.

## Manual Creation (Alternative)

If you prefer to create the admin manually:

1. Go to Render Dashboard → Your Web Service
2. Go to **Shell** tab
3. Run:
   ```bash
   python create_admin.py
   ```
4. Enter credentials when prompted

## Security Notes

⚠️ **Important Security Considerations:**

1. **Strong Password**: Use a strong, unique password for production
2. **Change After First Login**: Consider changing the password after first login
3. **Don't Commit Secrets**: Never commit `.env` files with admin credentials to Git
4. **Render Secrets**: Render environment variables are encrypted at rest
5. **Rotate Regularly**: Change admin passwords periodically

## Local Development

For local development, create a `.env` file:

```env
ADMIN_EMAIL=admin@dely.com
ADMIN_PASSWORD=admin123
ADMIN_NAME=Local Admin
ADMIN_ROLE=super_admin
```

Then run:
```bash
python create_admin.py
```

The script will automatically use environment variables if available, or prompt for input if not.

## Verification

After deployment, verify the admin was created:

1. Test login at: `POST /admin/auth/login`
2. Use the credentials you set in environment variables
3. You should receive a JWT token on successful login

## Troubleshooting

**Admin not created?**
- Check that `ADMIN_EMAIL` and `ADMIN_PASSWORD` are set correctly
- Check deployment logs for any errors
- Verify database migrations ran successfully
- Check if an admin with that email already exists

**Want to create additional admins?**
- Use the admin panel after logging in
- Or run `python create_admin.py` in the Shell

