# Discord Server Booster & Token Manager

An automated Discord server boosting and token management tool featuring multi-threaded boosting, 24/7 token onliner with rich presence, and profile humanization.

---

## ⚡ Features

1. **Server Booster (`Option 1`)**:
   - Boost any Discord server using 1-month or 3-month Nitro tokens.
   - Automatically handles server joining, captcha bypass/solving (via CapSolver/HcOptcha), and boost assignment.
   - 2 boosts applied per Nitro token.

2. **Token Onliner (`Option 2`)**:
   - Keeps your tokens connected via the Discord Gateway websocket.
   - Displays custom rich presence (Playing, Streaming, Listening, Watching) configured in `config/onliner.json`.
   - Keeps accounts looking active and prevents offline detection.

3. **Token Humanizer (`Option 3`)**:
   - Automatically randomizes profiles for your tokens.
   - Sets random avatars, banners, bios, pronouns, and HypeSquad houses to make tokens appear authentic.

---

## 🚀 Setup & Installation

### 1. Requirements
- Python 3.10 or higher
- Git

### 2. Install Dependencies
Run the following in your terminal or command prompt:

```bash
pip install -r requirements.txt
```

*(On Windows, you can also simply double-click `install.bat`)*

If you plan to use the humanizer module directly:
```bash
pip install -r humanizer/requirements.txt
```

---

## ⚙️ Configuration

### 1. Add Your Tokens
Place your Discord user tokens inside the `data/` directory (one token per line):
- `data/1m.txt` — 1-Month Nitro tokens
- `data/3m.txt` — 3-Month Nitro tokens

### 2. Add Proxies (Optional but Recommended)
Add your proxies (HTTP or SOCKS5) to `data/proxies.txt`:
```text
ip:port
ip:port:username:password
```

### 3. Config (`config/config.yaml`)
Customize your logging and captcha solver settings:
```yaml
discord:
  webhook_url: "YOUR_DISCORD_WEBHOOK_URL"  # Optional: logs boosting results to a Discord channel

extras:
  use_log: true

  captcha_solver:
    solve_captcha: false                   # Set to true if servers enforce hCaptcha
    use: "capsolver"                       # capsolver / hcoptcha / csolver / dchcaptcha
    capsolver_api_key: ""
    hcoptcha_api_key: ""
    csolver_key: ""
    dchcaptcha_api_key: ""
    max_retries: 5
```

### 4. Onliner Settings (`config/onliner.json`)
Customize the activity status and rich presence for tokens kept online:
- Choose random statuses (`online`, `idle`, `dnd`)
- Custom activity types (`game`, `streaming`, `listening`, `watching`)

---

## 🛠️ Usage

### Option A: Local Console Tool
Run the main program:
```bash
python main.py
```
*(Or double-click `start.bat` on Windows)*

### Option C: 24/7 Cloud Hosting on Render (Use from Anywhere)
You can deploy this bot to **Render.com** so it runs 24/7 without needing your computer on:
1. Fork or push this repository to your GitHub.
2. Log into **[Render.com](https://render.com)** and click **New + ➔ Web Service**.
3. Select your repository `booster-`.
4. Render will automatically detect settings, or set:
   - **Environment**: `Python`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python bot.py`
5. In **Environment Variables**, add:
   - `BOT_TOKEN`: Your Discord Bot token
   - `OWNER_IDS`: Your Discord user ID (e.g. `123456789`)
   - `PREFIX`: `$` (optional)
   - `TOKENS_1M`: (optional) paste your 1m tokens here
6. Click **Deploy Web Service**.
7. Once deployed, Render gives you a URL (e.g. `https://booster-bot.onrender.com`).
   * Add this URL to a free uptime monitor (like **UptimeRobot.com** or **cron-job.org**) set to ping every 5-10 minutes to keep the free service awake 24/7!
8. Add new tokens anytime directly from Discord using:
   ```text
   $restock 1m your_token_here
   ```


Select one of the menu options:
- `[1] Boost a Server`:
  1. Enter server invite link (e.g. `discord.gg/yourinvite` or `yourinvite`).
  2. Enter the number of boosts (must be an even number, e.g., 2, 4, 14).
  3. Choose 1 or 3 for 1-month or 3-month tokens.
- `[2] Online all Tokens`:
  - Connects all tokens in `data/1m.txt` and `data/3m.txt` to the gateway and keeps them online until you press `CTRL+C`.
- `[3] Humanize Tokens`:
  - Automatically loads tokens into the profile humanizer to set avatars, bios, and nicknames.

---

## 📁 Project Structure

```
├── config/
│   ├── config.yaml          # Webhook & Captcha solver configuration
│   └── onliner.json         # Token Onliner presence settings
├── data/
│   ├── 1m.txt               # 1-month Nitro tokens
│   ├── 3m.txt               # 3-month Nitro tokens
│   ├── proxies.txt          # Proxies list
│   └── output/              # Boosting logs (success / failed / captcha)
├── humanizer/               # Profile customizer module (avatars, banners, bios)
├── authsystem.py            # Key generation / auth utilities
├── coderz.py                # Core booster & gateway logic
├── logger.py                # Console logger helper
├── main.py                  # Main CLI entry point
└── requirements.txt         # Required Python packages
```

---

## ⚠️ Disclaimer
This tool is intended for educational and testing purposes only. Automated interaction with Discord's API violates Discord's Terms of Service. Use responsibly.

