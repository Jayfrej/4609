# 🚀 MT5 Middleware Production Deployment Guide

Complete step-by-step guide to deploy your MT5 Multi-Account Middleware to production using **Cloudflare Tunnel** with a real domain.

## ✨ Overview

Transform your local MT5 middleware into a production-ready system accessible via your own domain, secured with Cloudflare's enterprise-grade protection.

**What you'll achieve:**
- 🌐 **Public Access** via your domain (e.g., `webhook.yourdomain.com`)
- 🔒 **Enterprise Security** with Cloudflare WAF, DDoS protection, SSL
- 📊 **Production Monitoring** with health checks and uptime tracking
- 🚀 **Zero Server Costs** - runs from your local machine through secure tunnel

## 🔹 Step 1: Prepare Your Local System

### 1.1 Verify Local Environment
```bash
# Activate environment and start Flask
venv\Scripts\activate
python server.py
```
✅ Server should start at `http://127.0.0.1:5000`

### 1.2 Test Core Functionality
Before going public, ensure everything works locally:

- ✅ **Basic Auth** login at http://127.0.0.1:5000
- ✅ **Add Account** creates MT5 instance and launches terminal
- ✅ **Webhook Token** validation works
- ✅ **Test webhook** with curl:

```bash
curl -X POST http://127.0.0.1:5000/webhook/YOUR_TOKEN \
  -H "Content-Type: application/json" \
  -d '{
    "action": "BUY",
    "symbol": "EURUSD", 
    "volume": 0.1,
    "type": "MARKET"
  }'
```

Expected response: `{"status": "success", "message": "Signal processed"}`

## 🔹 Step 2: Install & Setup Cloudflared

### 2.1 Download Cloudflared

**Windows:**
1. Download `cloudflared.exe` from [GitHub Releases](https://github.com/cloudflare/cloudflared/releases)
2. Place in folder and add to PATH, or use directly
3. Verify: `cloudflared --version`

**Linux:**
```bash
# Ubuntu/Debian
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared-linux-amd64.deb

# Or via apt
sudo apt update && sudo apt install cloudflared
```

### 2.2 Authenticate with Cloudflare
```bash
cloudflared tunnel login
```
- Browser opens → Select your domain from Cloudflare account
- Authorization file saved to `~/.cloudflared/cert.pem`

## 🔹 Step 3: Create Production Tunnel

### 3.1 Create Named Tunnel
```bash
cloudflared tunnel create mt5-production
```
📝 **Save the UUID** returned (e.g., `12345678-1234-1234-1234-123456789abc`)

### 3.2 Create Configuration File

**Windows:** `C:\Users\{USERNAME}\.cloudflared\config.yml`  
**Linux:** `~/.cloudflared/config.yml`

```yaml
tunnel: 12345678-1234-1234-1234-123456789abc
credentials-file: /path/to/.cloudflared/12345678-1234-1234-1234-123456789abc.json

ingress:
  # Main webhook domain
  - hostname: webhook.yourdomain.com
    service: http://127.0.0.1:5000
    originRequest:
      httpHostHeader: localhost
      
  # Optional: Separate admin subdomain for security
  - hostname: mt5-admin.yourdomain.com
    service: http://127.0.0.1:5000
    originRequest:
      httpHostHeader: localhost
      
  # Health monitoring endpoint
  - hostname: mt5-health.yourdomain.com
    service: http://127.0.0.1:5000
    originRequest:
      httpHostHeader: localhost
      
  # Catch-all fallback
  - service: http_status:404

# Production logging
logDirectory: ./logs
loglevel: info
metrics: 127.0.0.1:8081
```

### 3.3 Setup DNS Records
```bash
# Create DNS routes for your subdomains
cloudflared tunnel route dns mt5-production webhook.yourdomain.com
cloudflared tunnel route dns mt5-production mt5-admin.yourdomain.com  
cloudflared tunnel route dns mt5-production mt5-health.yourdomain.com
```

### 3.4 Verify DNS Propagation
```bash
# Wait 1-2 minutes then check
nslookup webhook.yourdomain.com
# Should show Cloudflare IPs
```

## 🔹 Step 4: Configure Cloudflare Security

### 4.1 SSL/TLS Settings (Cloudflare Dashboard)
Navigate to **SSL/TLS > Overview**:
- **SSL/TLS Mode:** Full (Strict) 
- **Always Use HTTPS:** On
- **HSTS:** Enable with 6 months max-age
- **TLS Version:** 1.2 minimum

### 4.2 Firewall Rules (Security > WAF)

**Rule 1: Protect Admin Interface**
```
Rule Name: Block Admin Access
Field: Hostname
Operator: equals  
Value: mt5-admin.yourdomain.com
Action: Block
```
Add exception for your IP: **IP Source Address** equals `YOUR_STATIC_IP`

**Rule 2: Webhook Rate Limiting**
```
Rule Name: Webhook Rate Limit
Field: URI Path
Operator: starts with
Value: /webhook/
Action: Rate Limit
Rate: 10 requests per minute per IP
```

**Rule 3: Block Invalid Webhook Tokens**
```
Rule Name: Invalid Webhook Tokens
Field: URI Path  
Operator: matches regex
Value: ^/webhook/(?!YOUR_ACTUAL_TOKEN$)[^/]*/?$
Action: Block
Response: 404 (hide endpoint existence)
```

### 4.3 Bot Protection
- **Bot Fight Mode:** On
- **Super Bot Fight Mode:** On (if Pro+ plan)
- **Challenge Passage:** 30 minutes

### 4.4 Access Rules (Optional)
Block entire countries or allow only specific regions based on your trading requirements.

## 🔹 Step 5: Update Application for Production

### 5.1 Update .env Configuration
```env
# Production Environment
ENVIRONMENT=production
EXTERNAL_BASE_URL=https://webhook.yourdomain.com

# Enhanced Security
SESSION_TIMEOUT=900  # 15 minutes
FORCE_HTTPS=true
WEBHOOK_RATE_LIMIT=50  # per minute

# Production Logging
LOG_LEVEL=INFO
LOG_TO_FILE=true
LOG_MAX_SIZE=10485760  # 10MB
LOG_BACKUP_COUNT=5

# Email Alerts (Highly Recommended)
ENABLE_EMAIL_ALERTS=true
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=alerts@yourdomain.com
SMTP_PASSWORD=your-app-password
ALERT_EMAIL=admin@yourdomain.com

# Alert Settings
ALERT_ON_UNAUTHORIZED_ACCESS=true
ALERT_ON_SYSTEM_ERRORS=true
ALERT_ON_ACCOUNT_STATUS_CHANGE=true

# Health Check Settings
HEALTH_CHECK_INTERVAL=60  # seconds
HEALTH_CHECK_TIMEOUT=10   # seconds
```

### 5.2 Add Production Enhancements to server.py

Add these imports and configurations to your Flask app:

```python
import os
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Configure for production behind Cloudflare
if os.getenv('ENVIRONMENT') == 'production':
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# Rate limiting
limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["1000 per day", "100 per hour"]
)

# Force HTTPS in production
@app.before_request
def force_https():
    if os.getenv('FORCE_HTTPS') == 'true':
        if not request.is_secure and request.headers.get('X-Forwarded-Proto') != 'https':
            return redirect(request.url.replace('http://', 'https://'))

# Enhanced webhook rate limiting
@app.route('/webhook/<token>', methods=['POST'])
@limiter.limit("30 per minute")
def webhook_endpoint(token):
    # Your existing webhook logic
    pass

# Production health check with more details
@app.route('/health')
def health_check():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "environment": os.getenv('ENVIRONMENT', 'development'),
        "uptime": time.time() - start_time
    })
```

## 🔹 Step 6: Launch Production System

### 6.1 Start Flask Application
```bash
# Production mode with optimizations
venv\Scripts\activate

# Set production environment
set ENVIRONMENT=production  # Windows
export ENVIRONMENT=production  # Linux

# Start with production settings
python server.py
```

### 6.2 Start Cloudflared Tunnel

**Option A: Manual Start (for testing)**
```bash
cloudflared tunnel run mt5-production
```

**Option B: Windows Service (Recommended)**
```cmd
# Install as Windows service
cloudflared service install

# Start service
sc start cloudflared

# Set to auto-start
sc config cloudflared start= auto
```

**Option C: Linux Systemd Service (Recommended)**
```bash
# Install systemd service
sudo cloudflared service install

# Start and enable
sudo systemctl start cloudflared
sudo systemctl enable cloudflared

# Check status
sudo systemctl status cloudflared
```

### 6.3 Verify Production Deployment

**Test Public Access:**
```bash
# Health check
curl https://webhook.yourdomain.com/health

# Should return JSON with status: healthy
```

**Test Security:**
```bash
# Invalid token should be blocked
curl -X POST https://webhook.yourdomain.com/webhook/INVALID_TOKEN

# Valid token should work
curl -X POST https://webhook.yourdomain.com/webhook/YOUR_REAL_TOKEN \
  -H "Content-Type: application/json" \
  -d '{"action":"BUY","symbol":"EURUSD","volume":0.01,"type":"MARKET"}'
```

**Test Admin Interface:**
- Navigate to `https://mt5-admin.yourdomain.com`
- Should be blocked unless accessing from your whitelisted IP
- Login with Basic Auth credentials when allowed

## 🔹 Step 7: TradingView Integration

### 7.1 Configure TradingView Alerts

**Webhook URL:** `https://webhook.yourdomain.com/webhook/YOUR_TOKEN`

**Message Templates:**

**Basic Market Order:**
```json
{
  "action": "{{strategy.order.action}}",
  "symbol": "{{ticker}}",
  "type": "MARKET",
  "volume": 0.1
}
```

**Advanced with SL/TP:**
```json
{
  "action": "{{strategy.order.action}}",
  "symbol": "{{ticker}}",
  "type": "MARKET", 
  "volume": {{strategy.position_size}},
  "stop_loss": {{strategy.order.sl}},
  "take_profit": {{strategy.order.tp}},
  "account": "123456789"
}
```

**Limit/Stop Orders:**
```json
{
  "action": "BUY",
  "symbol": "{{ticker}}",
  "type": "LIMIT",
  "price": {{close}},
  "volume": 0.1,
  "expiry": "GTC"
}
```

### 7.2 Testing TradingView Integration

1. **Create Test Alert** in TradingView
2. **Use Webhook URL** with your production domain
3. **Trigger Alert** manually to test
4. **Check Logs** in your web UI for successful signal processing
5. **Verify Trade** executed in MT5 terminal

## 🔹 Step 8: Monitoring & Maintenance

### 8.1 Setup Uptime Monitoring

**UptimeRobot Setup:**
- Monitor URL: `https://webhook.yourdomain.com/health`
- Check interval: 1 minute
- Alert contacts: Your email/SMS

**Pingdom/StatusCake Alternative:**
- HTTP(S) monitoring on health endpoint
- Response time alerts
- Multi-location checks

### 8.2 Log Monitoring

**Key Logs to Watch:**
```bash
# Webhook activity
tail -f logs/webhook.log

# System errors  
tail -f logs/error.log

# Email notifications
tail -f logs/email.log

# Cloudflared tunnel
tail -f logs/cloudflared.log
```

**Log Rotation Setup:**
```python
# In server.py - add log rotation
import logging.handlers

handler = logging.handlers.RotatingFileHandler(
    'logs/app.log', maxBytes=10485760, backupCount=5
)
```

### 8.3 Regular Maintenance Tasks

**Daily:**
- ✅ Check health endpoint status
- ✅ Review error logs for issues
- ✅ Verify MT5 instances are running

**Weekly:**
- ✅ Test webhook functionality end-to-end
- ✅ Review Cloudflare analytics
- ✅ Check disk space usage
- ✅ Backup configuration files

**Monthly:**
- ✅ Update dependencies (`pip list --outdated`)
- ✅ Review and rotate logs
- ✅ Test disaster recovery procedures
- ✅ Audit security settings

## 🔒 Security Best Practices

### 8.1 Token Management
- **Rotate webhook tokens** monthly
- **Use strong tokens** (32+ characters, alphanumeric + symbols)
- **Never log tokens** in plaintext
- **Separate tokens** for different signal sources

### 8.2 Access Control
- **Whitelist your IP** for admin access
- **Use VPN** when accessing from different locations
- **Enable 2FA** on your Cloudflare account
- **Regular password updates** for Basic Auth

### 8.3 Network Security
- **Keep Flask internal** (only accessible via tunnel)
- **Block direct IP access** in firewall
- **Monitor unusual traffic** in Cloudflare Analytics
- **Set up fail2ban** for repeated failed attempts

## 🚨 Troubleshooting Guide

### Common Issues & Solutions

**Tunnel Won't Connect:**
```bash
# Check tunnel status
cloudflared tunnel info mt5-production

# Verify config syntax  
cloudflared tunnel ingress validate

# Test local connection
cloudflared tunnel run --config /path/to/config.yml mt5-production
```

**Webhook Returns 502:**
- ✅ Flask server running on correct port
- ✅ No firewall blocking localhost:5000
- ✅ Config.yml service URL matches Flask port

**Basic Auth Not Working:**
- ✅ Check credentials in .env
- ✅ Session timeout not expired
- ✅ Clear browser cookies
- ✅ Verify ProxyFix configuration

**MT5 Instances Not Starting:**
- ✅ Check MT5_EXECUTABLE path
- ✅ Verify source profile exists
- ✅ Windows permissions for MT5 directory
- ✅ Antivirus not blocking terminal64.exe

**Signals Not Processing:**
```bash
# Check signal files created
ls instances/ACCOUNT_*/MQL5/Files/signals/

# Verify EA enabled in MT5
# Check Expert Advisors tab for errors

# Test manual signal file
echo '{"action":"BUY","symbol":"EURUSD","volume":0.01}' > instances/123456/MQL5/Files/signals/test.json
```

### Emergency Procedures

**If Tunnel Goes Down:**
1. Check cloudflared service status
2. Restart tunnel: `cloudflared tunnel run mt5-production`
3. Check Cloudflare status page
4. Use backup tunnel if configured

**If Flask Crashes:**
1. Check error logs: `tail -f logs/error.log`
2. Restart Flask server
3. Verify all MT5 instances reconnect
4. Test webhook functionality

**Security Incident:**
1. Immediately rotate webhook tokens
2. Check access logs for suspicious activity
3. Temporarily block traffic via Cloudflare
4. Update firewall rules
5. Notify users of any service disruption

## ✅ Production Checklist

Before going live, ensure:

### Pre-Launch
- [ ] Local system tested thoroughly
- [ ] .env configured for production
- [ ] Cloudflare tunnel configured and tested
- [ ] DNS records propagated
- [ ] SSL certificates active
- [ ] Firewall rules implemented
- [ ] Rate limiting configured
- [ ] Email alerts working
- [ ] Uptime monitoring setup
- [ ] Backup procedures documented

### Post-Launch  
- [ ] Health endpoint returning 200
- [ ] TradingView webhook integration tested
- [ ] MT5 instances launching correctly
- [ ] Signal processing working end-to-end
- [ ] Email notifications received
- [ ] Logs being generated correctly
- [ ] Performance metrics baseline established

### Ongoing Maintenance
- [ ] Daily health checks automated
- [ ] Weekly functionality tests scheduled  
- [ ] Monthly security reviews planned
- [ ] Quarterly disaster recovery tests
- [ ] Documentation kept up-to-date

---

## 🎯 Summary

Your MT5 Middleware is now production-ready with:

- 🌐 **Global Access** via your custom domain
- 🔒 **Enterprise Security** through Cloudflare
- 📊 **Professional Monitoring** and alerting
- 🚀 **Scalable Architecture** ready for growth
- 🛡️ **DDoS Protection** and WAF filtering
- ⚡ **High Performance** with edge caching
- 🔧 **Easy Maintenance** through web interface

**Your system can now handle:**
- Multiple trading accounts simultaneously
- High-frequency signals from TradingView
- Automated MT5 instance management
- Real-time monitoring and alerting
- Professional-grade security and reliability

Ready to revolutionize your automated trading setup! 🚀
