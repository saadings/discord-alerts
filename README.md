# Discord Alerts to Email

Never miss a Discord message again! This script watches specific Discord channels and emails you when new messages arrive.

---

## ⚠️ Warning

This uses your personal Discord account token, use at your own risk.

---

## Quick Start

### Step 1: Install

```bash
cd discord-alerts
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Step 2: Configure

Create a file called `.env` in the project folder:

```env
DISCORD_TOKEN=your_token_here
CHANNEL_IDS=811253468772958222
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASS=your_gmail_app_password
EMAIL_FROM=your_email@gmail.com
EMAIL_TO=your_email@gmail.com

# Optional: VoIP Call Alerts (free SIP-to-SIP calls)
VOIP_ENABLED=false
VOIP_SIP_USER=your_linphone_username
VOIP_SIP_PASS=your_linphone_password
VOIP_SIP_DOMAIN=sip.linphone.org
VOIP_CALL_TARGET=sip:youruser@sip.linphone.org
VOIP_COOLDOWN_SECONDS=60
VOIP_CLI_PATH=baresip
VOIP_CALL_DURATION=15
```

### Step 3: Run

```bash
python main.py
```

That's it! You'll get an email whenever someone posts in your monitored channel.

---

## How to Get Each Value

### Discord Token

1. Open **discord.com** in Chrome/Firefox (not the app)
2. Press `F12` to open Developer Tools
3. Go to **Network** tab
4. Send any message in Discord
5. Click any request → **Headers** → find `authorization:`
6. Copy that value (looks like: `NzIwNz...abc123`)

### Channel ID

1. In Discord: **Settings** → **Advanced** → Enable **Developer Mode**
2. Right-click the channel you want to monitor
3. Click **Copy Channel ID**

### Gmail App Password

1. Go to [Google Account Security](https://myaccount.google.com/security)
2. Turn on **2-Step Verification**
3. Go to **App passwords**
4. Create one for "Mail"
5. Use that 16-character password (without spaces) as `SMTP_PASS`

### VoIP Call Alerts (Optional)

Get a phone call when Discord messages arrive! This uses free SIP-to-SIP calling (no PSTN/WhatsApp - those require paid services).

**Note:** WhatsApp and regular phone calls (PSTN) are not available for free. This feature uses SIP protocol for app-to-app calls only.

#### Step 1: Create a Free SIP Account

1. Download [Linphone](https://www.linphone.org/getting-started) on your phone/computer
2. Create a free account at [sip.linphone.org](https://www.linphone.org/freesip/home)
3. Note your username and password

#### Step 2: Install the SIP CLI Tool (baresip)

**macOS:**
```bash
brew install baresip
```

**Ubuntu/Debian:**
```bash
sudo apt install baresip
```

#### Step 3: Update .env

```env
VOIP_ENABLED=true
VOIP_SIP_USER=your_linphone_username
VOIP_SIP_PASS=your_linphone_password
VOIP_SIP_DOMAIN=sip.linphone.org
VOIP_CALL_TARGET=sip:youruser@sip.linphone.org
VOIP_COOLDOWN_SECONDS=60
VOIP_CLI_PATH=baresip
VOIP_CALL_DURATION=15
```

- `VOIP_CALL_TARGET`: The SIP address to call (your phone with Linphone app)
- `VOIP_COOLDOWN_SECONDS`: Minimum time between calls (prevents spam)
- `VOIP_CALL_DURATION`: How long the call rings before hanging up

#### Test Your VoIP Setup

```bash
python test_voip.py
```

---

## Running in Background

To keep it running after you close the terminal:

```bash
nohup python main.py > alerts.log 2>&1 &
```

### Check if it's running

```bash
ps aux | grep main.py
```

### Stop it

```bash
pkill -f "python main.py"
```

### View logs

```bash
tail -f alerts.log
```

---

## Monitor Multiple Channels

Just add more channel IDs separated by commas:

```env
CHANNEL_IDS=811253468772958222,123456789012345678,987654321098765432
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| "Invalid token" | Your token expired. Get a new one from browser DevTools. |
| "SMTP auth failed" | Wrong email/password. For Gmail, use an App Password. |
| No emails arriving | Check spam folder. Verify channel ID is correct. |
| Script stops randomly | Discord may have detected unusual activity. Wait and restart. |
| VoIP call not working | Try `python test_voip.py` to debug. Check SIP credentials. |
| "baresip not found" | Install with `brew install baresip` or set `VOIP_CLI_PATH` to full path. |
| Call doesn't ring | Ensure Linphone app is open and logged in on your phone. |

---

## Files

| File | What it does |
|------|--------------|
| `main.py` | The main script that listens and sends emails/calls |
| `test_discord.py` | Test script to verify Discord connection works |
| `test_voip.py` | Test script to verify VoIP call setup works |
| `.env` | Your secret configuration (don't share this!) |
| `requirements.txt` | Python packages needed |

---

## License

MIT - Do whatever you want with it.
