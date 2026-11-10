# Discord Server Booster & Token Manager

An automated Discord server boosting and token management tool featuring multi-threaded boosting, 24/7 token onliner with rich presence, and profile humanization.

---

## ⚡ Features

1. **Auto-Shop & Litecoin (LTC) Payment System**:
   - Buyers can purchase boost credits with LTC using `$buy <1m|3m> <boosts>`.
   - Generates dynamic invoice with interactive `[Check Payment]` button.
   - Automatically monitors the Litecoin blockchain and confirms transactions, crediting users automatically.

2. **Credits-Based Boosting**:
   - Buyers spend their boost credits to boost any server (`$boost <invite> <amount> <months>`).
   - Designated Owners (`1505515188991033409` and `1521774957065928734`) have **unlimited boosts**.

3. **Bulk Restock (Text & File Upload)**:
   - Restock tokens in bulk by pasting or simply attaching a `.txt` file to `$restock <1m|3m>`.
   - Automatically filters out duplicates against current stock.

4. **Used Account Archiving**:
   - As soon as accounts are used for boosting, they are automatically moved out of stock and saved to `data/used_tokens.txt` with timestamps and server links.

5. **Token Onliner & Humanizer**:
   - Keeps accounts online 24/7 with custom rich presence, and randomizes avatars, bios, and badges.


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

