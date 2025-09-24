# MT5 Multi-Account Middleware (Complete Guide)

This project transforms **your computer into a server** that can:
* Receive **Webhooks from TradingView (or other sources)**
* Manage **multiple MT5 accounts simultaneously** (Multi-Instance)
* Provide a **Web UI** for adding/deleting/restarting/stopping accounts with real-time status monitoring
* Secure with **Basic Auth + Webhook Token + Rate-limiting + Cloudflare Tunnel**
* Send **Email Alerts** (Online/Offline/Error/Unauthorized)
* Include **Log Viewer** and **Health Check Endpoint** (compatible with UptimeRobot)

## ✨ Key Features

### **Multi-Account MT5**
- Creates separate portable instances per account
- Uses Default Profile with pre-configured EA
- Control buttons: Open / Restart / Stop / Delete

### **Webhook Receiver**
- Endpoint: `/webhook/<TOKEN>`
- Supports Actions: `BUY, SELL, BUY_LIMIT, SELL_LIMIT, BUY_STOP, SELL_STOP, LONG, SHORT`
- Auto-Symbol Mapping with fuzzy matching (60-70% accuracy)
- Writes signals as JSON to `MQL5/Files/signals/*.json` (for EA consumption)

### **Security**
- Basic Authentication for UI access
- Idle timeout (e.g., 15 minutes inactivity → re-login required)
- Webhook token validation + rate limiting
- Cloudflare Firewall integration (recommended)

### **Monitoring**
- Email alerts when accounts go Online/Offline
- Email notifications for Unauthorized access / Payload errors / Signal write errors
- `/health` endpoint for UptimeRobot monitoring

### **UI Features**
- Add Account (enter account number + nickname)
- Accounts Table: Real-time Online/Offline status, PID display, action buttons
- Webhook URL display with copy button
- Log Viewer (Webhook logs, Error logs, Email logs)

## ⚙️ Installation (Step by Step)

### 1) Prepare Your System
- Windows or Linux with MetaTrader 5 installed
- Python 3.10+
- Install Cloudflared

### 2) Install Project

```bash
git clone <repository-url>
cd 4609
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux:
source venv/bin/activate
pip install -r requirements.txt
```

### 3) Configure Environment Variables

Copy the example file:
```bash
# Windows
copy .env.example .env
# Linux
cp .env.example .env
```

Edit `.env` with your settings:

```env
# Basic Authentication
BASIC_USER=admin
BASIC_PASS=yourpassword

# Webhook Security
WEBHOOK_TOKEN=your-long-random-token-here
EXTERNAL_BASE_URL=https://webhook.yourdomain.com

# MT5 Configuration
MT5_MAIN_PATH=C:\Program Files\MetaTrader 5\terminal64.exe
MT5_INSTANCES_DIR=C:\MT5\instances
MT5_PROFILE_SOURCE=C:\Users\YOUR_USERNAME\AppData\Roaming\MetaQuotes\Terminal\<TERMINAL_ID>

# Email Configuration (SMTP)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-app-password
SMTP_FROM=alerts@yourdomain.com
SMTP_TO=recipient@gmail.com

# Optional: Rate Limiting
RATE_LIMIT_PER_MINUTE=60
IDLE_TIMEOUT_MINUTES=15
```

## ▶️ Local Usage

### 1. Start the Server:
```bash
python server.py
```

### 2. Access Web Interface:
- Open browser to: `http://127.0.0.1:5000`
- Login with your `BASIC_USER` / `BASIC_PASS`
- Click **Add Account** → System creates portable MT5 instance and launches MT5 automatically

## 🌍 Production Deployment (via Cloudflare Tunnel)

### 1. **Login to Cloudflare**
```bash
cloudflared tunnel login
```

### 2. **Create Tunnel**
```bash
cloudflared tunnel create mt5-tunnel
```

### 3. **Create config.yml**
```yaml
tunnel: <YOUR_TUNNEL_UUID>
credentials-file: C:\Users\YOUR_USERNAME\.cloudflared\<UUID>.json

ingress:
  - hostname: webhook.yourdomain.com
    service: http://127.0.0.1:5000
  - service: http_status:404
```

### 4. **Configure DNS**
```bash
cloudflared tunnel route dns mt5-tunnel webhook.yourdomain.com
```

### 5. **Run Tunnel**
```bash
cloudflared tunnel run mt5-tunnel
```

## 📡 TradingView Configuration

### Webhook URL:
```
https://webhook.yourdomain.com/webhook/<YOUR_WEBHOOK_TOKEN>
```

### Example JSON Payload:
```json
{
  "account_number": "123456",
  "symbol": "XAUUSDm",
  "action": "BUY",
  "volume": 0.1,
  "take_profit": 2000.0,
  "stop_loss": 1995.0
}
```

The system will auto-map `"XAUUSDm"` → `"XAUUSD"` (fuzzy matching) and create JSON signal files for EA consumption.

## 📋 Supported Actions

| Action | Description |
|--------|-------------|
| `BUY` | Market buy order |
| `SELL` | Market sell order |
| `BUY_LIMIT` | Buy limit order |
| `SELL_LIMIT` | Sell limit order |
| `BUY_STOP` | Buy stop order |
| `SELL_STOP` | Sell stop order |
| `LONG` | Alias for BUY |
| `SHORT` | Alias for SELL |

## 🔐 Security Features

- **Basic Authentication**: Protects web interface access
- **Webhook Token Validation**: Prevents unauthorized signal submission
- **Rate Limiting**: Configurable requests per minute limit
- **Idle Timeout**: Automatic session expiration
- **Cloudflare Integration**: Additional DDoS protection and firewall rules

## 📊 Monitoring & Alerts

### Email Notifications:
- Account status changes (Online → Offline, Offline → Online)
- Unauthorized webhook attempts
- Payload validation errors
- Signal file write errors

### Health Check Endpoint:
- Access: `GET /health`
- Returns JSON with system status
- Compatible with UptimeRobot and other monitoring services

### Log Viewer:
- Webhook activity logs
- Error logs with timestamps
- Email delivery logs
- Real-time log streaming in web interface

## 🛠 Troubleshooting

### **MT5 Shows "Open Account Wizard"**
- Verify `MT5_PROFILE_SOURCE` path is correct
- Ensure the profile contains `config/servers.dat` file
- Check that the source profile has been used with MT5 at least once

### **Webhook Returns "Unauthorized"**
- Verify the token in webhook URL matches `WEBHOOK_TOKEN` in `.env`
- Check for trailing spaces or hidden characters in token

### **EA Not Executing Trades**
- Confirm signal files are written to correct `MQL5/Files/signals/` directory of the instance
- Verify EA is installed and configured to read signal files
- Check EA logs in MT5 for any errors

### **Email Alerts Not Sending**
- Verify SMTP configuration in `.env`
- For Gmail: Use App Password instead of regular password
- Check firewall settings for SMTP port (usually 587 or 465)

### **Instance Creation Fails**
- Ensure `MT5_INSTANCES_DIR` exists and is writable
- Verify `MT5_MAIN_PATH` points to correct MT5 executable
- Check Windows permissions for directory access

## 🔧 Configuration Options

### Environment Variables Reference:

| Variable | Description | Required | Example |
|----------|-------------|----------|---------|
| `BASIC_USER` | Web interface username | Yes | `admin` |
| `BASIC_PASS` | Web interface password | Yes | `securepassword123` |
| `WEBHOOK_TOKEN` | Webhook security token | Yes | `abc123xyz789` |
| `EXTERNAL_BASE_URL` | Public webhook URL | Yes | `https://webhook.example.com` |
| `MT5_MAIN_PATH` | MT5 executable path | Yes | `C:\Program Files\MetaTrader 5\terminal64.exe` |
| `MT5_INSTANCES_DIR` | Instances storage directory | Yes | `C:\MT5\instances` |
| `MT5_PROFILE_SOURCE` | Source profile directory | Yes | `C:\Users\User\AppData\Roaming\MetaQuotes\Terminal\ABC123` |
| `SMTP_HOST` | Email server hostname | No | `smtp.gmail.com` |
| `SMTP_PORT` | Email server port | No | `587` |
| `SMTP_USER` | Email username | No | `user@gmail.com` |
| `SMTP_PASS` | Email password | No | `apppassword123` |
| `RATE_LIMIT_PER_MINUTE` | Webhook rate limit | No | `60` |
| `IDLE_TIMEOUT_MINUTES` | Session timeout | No | `15` |

## 📁 Directory Structure

```
mt5-middleware-complete/
├── server.py              # Main application
├── requirements.txt       # Python dependencies
├── .env.example          # Environment template
├── .env                  # Your configuration (create this)
├── static/               # Web UI assets
├── templates/            # HTML templates
├── logs/                 # Application logs
└── README.md            # This file
```

## 🚀 Quick Start (TL;DR)

1. Install Python 3.10+, Cloudflared, MT5
2. Clone repo and run: `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and configure MT5 paths, SMTP, tokens
4. Run: `python server.py` → Access web interface, Add Account → MT5 launches automatically
5. Setup Cloudflare Tunnel → Use real domain for TradingView webhooks
6. Configure TradingView webhook with your domain and token
7. Monitor via web interface and email alerts

## 📞 Support

For issues and questions:
1. Check the troubleshooting section above
2. Review logs via the web interface Log Viewer
3. Verify your `.env` configuration matches the examples
4. Ensure all required services (MT5, SMTP, Cloudflare) are properly configured

---

**Note**: This middleware acts as a bridge between TradingView signals and MT5. Ensure your EA is properly configured to read signal files from the `MQL5/Files/signals/` directory of each instance.
