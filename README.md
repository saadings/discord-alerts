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

---

## Files

| File | What it does |
|------|--------------|
| `main.py` | The main script that listens and sends emails |
| `test_discord.py` | Test script to verify Discord connection works |
| `.env` | Your secret configuration (don't share this!) |
| `requirements.txt` | Python packages needed |

---

## License

MIT - Do whatever you want with it.
