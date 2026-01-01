# Pre-Deployment Checklist

Use this checklist before deploying to Hostinger production.

## Code Preparation

- [ ] All code committed to Git
- [ ] No debug print statements
- [ ] No hardcoded credentials
- [ ] All environment variables in `.env.production.example`
- [ ] Error handling implemented
- [ ] Logging configured

## Configuration

- [ ] `DEBUG=False` in production `.env`
- [ ] Strong `SECRET_KEY` generated (32+ characters)
- [ ] Database URL configured for MySQL
- [ ] CORS origins set to production domains only
- [ ] Email SMTP credentials configured (if needed)
- [ ] Payment gateway credentials configured (if needed)

## Database

- [ ] MySQL database created in Hostinger
- [ ] Database user created with proper permissions
- [ ] Migration files tested locally
- [ ] Backup strategy planned

## Security

- [ ] `.env` file has 600 permissions
- [ ] No sensitive data in code
- [ ] API documentation disabled in production
- [ ] CORS properly configured
- [ ] SSL/HTTPS enabled
- [ ] Strong passwords for all services

## Testing

- [ ] All endpoints tested locally
- [ ] Database migrations tested
- [ ] Error handling tested
- [ ] Authentication flow tested
- [ ] File upload tested (if applicable)

## Server Setup

- [ ] Python 3.9+ available on Hostinger
- [ ] Virtual environment created
- [ ] All dependencies installed
- [ ] Required directories created (uploads, logs)
- [ ] File permissions set correctly

## Monitoring

- [ ] Logging configured
- [ ] Error tracking set up
- [ ] Health check endpoint working
- [ ] Monitoring tools configured (if any)

## Documentation

- [ ] API documentation updated
- [ ] Deployment guide reviewed
- [ ] Environment variables documented
- [ ] Troubleshooting guide ready

## Post-Deployment

- [ ] Health check endpoint tested
- [ ] Registration endpoint tested
- [ ] Login endpoint tested
- [ ] All critical endpoints verified
- [ ] Logs checked for errors
- [ ] Performance monitored

---

**Ready to deploy?** Follow `HOSTINGER_DEPLOYMENT.md` step by step.

