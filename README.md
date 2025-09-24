# MT5 Multi-Account Middleware (Complete)

A complete solution for managing multiple MT5 accounts with automated webhook-based trading signal distribution from TradingView and other platforms.

## ✨ Key Features

- **Multi-account MT5 instances** (portable mode)
- **Auto-create & launch MT5** from source profile when adding accounts
- **Webhook integration** with token security and rate limiting
- **Smart signal processing** - normalization + fuzzy symbol mapping
- **Real-time monitoring** - account status, logs, email alerts
- **Web management UI** - add/restart/stop/delete accounts
- **Health endpoint** for uptime monitoring (UptimeRobot compatible)
- **Basic Auth** with 15-minute idle timeout

## 🚀 Quick Start

```bash
# Setup environment
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# Configure
copy .env.example .env
# Edit .env: MT5 paths, SMTP settings, webhook token

# Run
python server.py
```

**Access:** http://127.0.0.1:5000 (Basic Auth required)

## 📁 Project Structure

```
MT5-Middleware/
├── server.py              # Main Flask application
├── requirements.txt       # Python dependencies  
├── .env.example          # Environment template
├── static/               # CSS, JS, assets
├── templates/            # HTML templates
├── instances/            # MT5 instances directory
│   └── ACCOUNT_123456/   # Individual account folders
│       └── MQL5/Files/signals/  # Signal files for EA
└── logs/                 # Application logs
```

## ⚙️ Configuration

Edit `.env` with your settings:

```env
# MT5 Configuration
MT5_PROFILE_SOURCE=C:/path/to/your/mt5/profile  # Source profile with EA
MT5_INSTANCES_DIR=./instances                   # Instances storage
MT5_EXECUTABLE=C:/Program Files/MetaTrader 5/terminal64.exe

# Security
SECRET_KEY=your-secret-key-here
WEBHOOK_TOKEN=your-webhook-token-here

# Email Alerts (Optional)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
ALERT_EMAIL=alerts@yourdomain.com
```

## 🔄 How It Works

### 1. Account Management Flow
1. **Add Account** → Enter account number + nickname in web UI
2. **Auto Instance Creation** → System copies `MT5_PROFILE_SOURCE` to new instance folder
3. **Auto Launch MT5** → Flask executes `terminal64.exe /portable /datapath:<instance>`
4. **Manual Login** → User logs in once in the launched MT5 instance
5. **Ready for Signals** → EA in default profile starts listening for signal files

### 2. Webhook Signal Flow
1. **TradingView Alert** → POST to `/webhook/<TOKEN>`
2. **Security Check** → Token validation + rate limiting
3. **Signal Normalization** → `LONG/SHORT` → `BUY/SELL`, validate payload
4. **Symbol Mapping** → Fuzzy match (≥60%) TradingView symbols to MT5 symbols
5. **Write Signal File** → JSON file to `<INSTANCE>/MQL5/Files/signals/`
6. **EA Execution** → Your EA reads signal and executes trade

### 3. Monitoring & Alerts
- **Background Monitor** → Checks MT5 process status (PID tracking)
- **Real-time Status** → Online/Offline indicator in web UI
- **Email Notifications** → Unauthorized access, errors, status changes
- **Log Viewer** → Last 200 entries (Webhook, Error, Email logs)

## 🔗 API Reference

### Webhook Endpoint
```http
POST /webhook/<TOKEN>
Content-Type: application/json

{
  "action": "BUY",           # BUY/SELL (LONG/SHORT auto-converted)
  "symbol": "XAUUSD",        # Auto-mapped with fuzzy matching
  "type": "MARKET",          # MARKET/LIMIT/STOP
  "price": 2000.00,          # Required for LIMIT/STOP
  "volume": 0.1,             # Lot size
  "account": "123456789"     # Optional: target specific account
}
```

### Management Endpoints
- `GET /health` → Health check (returns 200 OK)
- `GET /accounts` → List all accounts with status
- `POST /accounts` → Add new account
- `PUT /accounts/<id>` → Update account settings
- `DELETE /accounts/<id>` → Remove account from system

### Web UI Features
- **Account Dashboard** → View all accounts with real-time status
- **Add/Remove Accounts** → Simple form-based management
- **Instance Controls** → Open/Restart/Stop MT5 instances
- **Webhook URL Copy** → One-click copy for TradingView setup
- **Log Viewer** → Filter and search through system logs

## 💡 Usage Examples

### TradingView Setup
1. Create alert in TradingView
2. Set webhook URL: `http://yourserver.com:5000/webhook/YOUR_TOKEN`
3. Message template:
```json
{
  "action": "{{strategy.order.action}}",
  "symbol": "{{ticker}}",
  "type": "MARKET",
  "volume": 0.1
}
```

### Adding Your First Account
1. Navigate to http://127.0.0.1:5000
2. Login with Basic Auth credentials
3. Click "Add Account" button
4. Enter MT5 account number and friendly nickname
5. MT5 will auto-launch → login manually in the new MT5 window
6. Verify your EA is running and enabled
7. Test with a webhook call

### Symbol Mapping Examples
- `XAUUSDM` (TradingView) → `XAUUSD` (MT5)
- `EURUSD.forex` → `EURUSD`
- `US30` → `US30Cash` or `US30`
- Custom mappings can be added via fuzzy matching algorithm

## 🔧 Architecture Details

### Backend (Flask/Python)
- **REST API** for account management and webhook handling
- **SQLite Database** for account storage and configuration
- **Background Tasks** for MT5 process monitoring
- **Email Service** for alerts and notifications
- **Session Management** with Basic Auth + timeout

### Frontend (HTML/JS/CSS)
- **Responsive Web UI** for account management
- **Real-time Status Updates** via AJAX polling
- **Interactive Log Viewer** with filtering
- **Copy-to-Clipboard** webhook URLs
- **Mobile-friendly** design

### MT5 Integration
- **Portable Mode** → Each account gets isolated instance
- **Profile Cloning** → Copies EA and settings from source
- **Process Management** → Start/stop/restart MT5 instances
- **Signal File Interface** → JSON files in MQL5/Files/signals/
- **Symbol Auto-Discovery** → Fetches available symbols from MT5

## 🔒 Security Features

- **Token-based Webhook Access** → Prevents unauthorized signals
- **Basic Authentication** → Web UI protection
- **Session Timeout** → 15-minute idle logout
- **Rate Limiting** → Prevents webhook spam
- **Input Validation** → Sanitizes all incoming data
- **Error Logging** → Tracks suspicious activities

## 📊 Monitoring & Logging

### Log Categories
- **Webhook Logs** → All incoming signals and processing results
- **Error Logs** → System errors, exceptions, failures
- **Email Logs** → Notification delivery status
- **Account Logs** → MT5 instance management activities

### Monitoring Features
- **Health Endpoint** → `/health` returns 200 OK for uptime monitoring
- **Process Tracking** → Monitors MT5 instance PIDs
- **Email Alerts** → Configurable notifications for events
- **Web Log Viewer** → Real-time log streaming in browser

## 🔍 Troubleshooting

### Common Issues

**MT5 Won't Launch**
- Check `MT5_EXECUTABLE` path in `.env`
- Verify MT5 installation and permissions
- Ensure source profile exists and contains EA

**Webhook Not Working**
- Verify `WEBHOOK_TOKEN` matches TradingView setup
- Check webhook URL format and accessibility
- Review webhook logs for error details

**Symbols Not Found**
- Check fuzzy matching threshold (default 60%)
- Verify symbol exists in MT5 Market Watch
- Add custom symbol mapping if needed

**EA Not Trading**
- Ensure EA is enabled in MT5 instance
- Check signal files are being created in MQL5/Files/signals/
- Verify EA has proper permissions and settings

### Debug Steps
1. Check web UI logs for error messages
2. Verify MT5 instance is running (check Process column)
3. Test webhook with simple curl command
4. Check email alerts for system notifications
5. Review EA logs in MT5 Expert tab

## 📋 Requirements

- **Python 3.8+**
- **MetaTrader 5** terminal installed
- **Windows OS** (for MT5 portable mode)
- **Your Custom EA** in the source profile
- **SMTP Server** (optional, for email alerts)

## 🚀 Production Deployment

### Recommended Setup
- Use **reverse proxy** (nginx) for SSL termination
- Set up **process manager** (PM2, supervisor) for auto-restart
- Configure **firewall rules** to restrict webhook access
- Enable **log rotation** to prevent disk space issues
- Set up **uptime monitoring** using the `/health` endpoint

### Performance Tuning
- Adjust **rate limiting** based on signal frequency
- Optimize **fuzzy matching** threshold for your symbols
- Configure **log retention** based on disk space
- Monitor **memory usage** with multiple MT5 instances

---

**MT5 Multi-Account Middleware** - Complete, production-ready solution for automated MT5 trading signal distribution with multi-account support, real-time monitoring, and comprehensive management tools.