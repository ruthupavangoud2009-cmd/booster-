import os
import sys

def install_requirements():
    print(f"Installing required modules...")
    os.system(f"{sys.executable} -m pip install -r requirements.txt")
    os.system("cls" if os.name == "nt" else "clear")
import time
import re
import socket
import asyncio
import base64
from tls_client import Session
import httpx
import json
from datetime import datetime
from colorama import init, Fore, Style
from pystyle import Center, Colorate, Colors
from dateutil.parser import isoparse
from datetime import datetime, timezone
import random
import base64
import aiohttp
import websocket

init(autoreset=True)
sesh = Session(client_identifier="chrome_115", random_tls_extension_order=True)

config = {}
customization = {}
loaded_counts = {
    "Tokens": 0,
    "Pronouns": 0,
    "Bios": 0,
    "Global Names": 0,
    "Profile Pictures": 0,
    "Banners": 0
}

def clear_console():
    os.system('cls' if os.name == 'nt' else 'clear')

def set_console_title(title="humanizer :) | by Code Hub"):
    if os.name == 'nt':
        os.system(f"title {title}")
    else:
        print(f"\33]0;{title}\a", end='', flush=True)

def vg(lines, start_rgb=(0, 255, 200), end_rgb=(0, 100, 180)):
    total = len(lines)
    result = []
    for i, line in enumerate(lines):
        r = start_rgb[0] + (end_rgb[0] - start_rgb[0]) * i // max(1, total - 1)
        g = start_rgb[1] + (end_rgb[1] - start_rgb[1]) * i // max(1, total - 1)
        b = start_rgb[2] + (end_rgb[2] - start_rgb[2]) * i // max(1, total - 1)
        result.append(f'\033[38;2;{r};{g};{b}m{line}\033[0m')
    return result

# ── NEW: braille logo matching the screenshot ─────────────────────────────────

def animate_text(text, speed=0.03):
    lines = text.split('\n')
    for line in lines:
        print(line)
        time.sleep(speed)

def apply_gradient(lines, color_start=(255, 0, 255), color_end=(0, 255, 255)):
    total = len(lines)
    result = []
    for i, line in enumerate(lines):
        t = i / max(1, total - 1)
        r = int(color_start[0] + (color_end[0] - color_start[0]) * t)
        g = int(color_start[1] + (color_end[1] - color_start[1]) * t)
        b = int(color_start[2] + (color_end[2] - color_start[2]) * t)
        result.append(f'\033[38;2;{r};{g};{b}m{line}\033[0m')
    return result

def show_interface():
    logo = [
        "                      ⢀⣀⡀⣀⣤⣤⡄                                              ",
        "     ⣿⡟⠻⡆            ⢸⣿⡟⠿⣤⡄  ⣴⢶⠶⡆ ⠈⢷⡀  ⢀⣭⣫⠵⠥⠽⣄⣝⠵⢍⣘⣄⠳⣤⣀  ⢀⡤⠊⣽   ⠸⣇  ⢿  ",
        "     ⠛⢛⣿⠋            ⠸⢷⣴⣤⡤⠾⠇  ⣽⠋⠼⣷ ⠈⢷⡄⢀⣤⡶⠋  ⣀⡄⠤ ⡲⡆          ⠙⡄⠘⢮⢳⡴⠯⣀⢠⡏  ⢻  ⢸⠇",
        "     ⢠⡟⠁                    ⠙⠛⠋⠉⢀⣴⠟⠉⢯⡞⡠⢲⠉⣼     ⡰⠁⡇⢀⢷ ⣄⢵    ⡟⢄    ⠙⢷⣤⣤⣤⡿⢢⡿  ",
        "     ⠸⢷⣴                       ⣠⠟⠑⠊⠁⡼⣌⢠⢿⢸⢸⡀  ⢰⠁⡸⡇⡸⣸⢰⢈ ⠘⡄  ⢸  ⢣⡀    ⢮⢢⣏⣤⡾⠃   ",
        "                               ⢰⣯⣴⠞⡠⣼⠁⡘⣾⠏⣿⢇⣳⣸⣞⣀⢱⣧⣋⣞⡜⢳⡇  ⢸  ⢆⢧ ⠰⣄⢏⢧⣾⠁          ",
        "                               ⠈⢹⡏⢰⠁⡻  ⡟⡏⠉   ⣀        ⣀⠁    ⠉⠛⢽⠇  ⣼⡆  ⠈⡆⠃  ⡏⠻⣾⣽⣇⡀",
        "                                ⢸⠁⡇  ⡇⡄⣿⠷⠿⠿⠛              ⠛⠻⠿⠿⠿⡜⢀⡴⡟⢸⣸⡼     ⡇  ⡞⡆⢻⠙⢦",
        "                                ⢸⡶⢀⣼⣿⣬⣽⠧⠬⠇                  ⢞⣯⣭⢺⣔⣪⣾⣤⠺⡇⢳  ⢠⣧⡾⠃  ⠛⠻⠶⠞⠁",
        "                                ⠘⠷⢿⠟⠉⡀  ⠈⢦⡀    ⣠⠖⠒⠒⢤⡀  ⢀⡼⠿⢇⡣⢬⣶⠷⢿⣤⡾⠁                 ",
        "                                     ⠷⠾⠷⠖⠛⠛⠲⠶⠿⠤⣤⠤⢷⣶⠋       ⣱⠞⠁    ⠈⠉                  ",
        "                                                   ⠉⠛⠓⠒⠚⠋                               ",
    ]

    print('\n' * 2)
    styled_rows = apply_gradient(logo, color_start=(255, 0, 255), color_end=(0, 255, 255))
    centered_logo = '\n'.join([Center.XCenter(row) for row in styled_rows])
    animate_text(centered_logo, speed=0.05)
    print('\n')
    disclaimer = f"{Fore.LIGHTBLACK_EX}[{Fore.CYAN}i{Fore.LIGHTBLACK_EX}]{Style.RESET_ALL} {Fore.BLUE}By using this humaniser you admit that .gg/coderz is the best vault oat{Style.RESET_ALL}"
    print(Center.XCenter(disclaimer))
    print('\n' * 2)

# ─────────────────────────────────────────────────────────────────────────────

def ascii_nig():
    clear_console()

    ascii_art = [

        " ███╗   ███╗ █████╗ ██╗   ██╗███████╗██╗███████╗██╗     ██████╗       ██╗    ██╗██╗  ",
        " ████╗ ████║██╔══██╗╚██╗ ██╔╝██╔════╝██║██╔════╝██║     ██╔══██╗     ██╔╝   ██╔╝╚██╗ ",
        " ██╔████╔██║███████║ ╚████╔╝ █████╗  ██║█████╗  ██║     ██║  ██║    ██╔╝   ██╔╝  ╚██╗",
        " ██║╚██╔╝██║██╔══██║  ╚██╔╝  ██╔══╝  ██║██╔══╝  ██║     ██║  ██║    ╚██╗  ██╔╝   ██╔╝",
        " ██║ ╚═╝ ██║██║  ██║   ██║   ██║     ██║███████╗███████╗██████╔╝     ╚██╗██╔╝   ██╔╝ ",
        " ╚═╝     ╚═╝╚═╝  ╚═╝   ╚═╝   ╚═╝     ╚═╝╚══════╝╚══════╝╚═════╝       ╚═╝╚═╝    ╚═╝  "
                                                                                    
]

    try:
        width = os.get_terminal_size().columns
    except:
        width = 80

    print('\n' * 2)
    colored_lines = vg(ascii_art, start_rgb=(0, 255, 255), end_rgb=(0, 100, 255))

    for line in colored_lines:
        print(Center.XCenter(line))

    print('\n' * 2)


def current_time():
    return f"{Fore.LIGHTBLACK_EX}[{datetime.now().strftime('%H:%M:%S')}]{Style.RESET_ALL}"

def log(message_type, message, color=Fore.WHITE):
    type_styles = {
        "SUCCESS": f"{Fore.YELLOW}[{Fore.GREEN}SUC{Fore.YELLOW}]{Style.RESET_ALL}",
        "UPDATED": f"{Fore.YELLOW}[{Fore.CYAN}UPD{Fore.YELLOW}]{Style.RESET_ALL}",
        "ERROR":   f"{Fore.YELLOW}[{Fore.RED}ERR{Fore.YELLOW}]{Style.RESET_ALL}",
        "WARNING": f"{Fore.YELLOW}[{Fore.LIGHTYELLOW_EX}WRN{Fore.YELLOW}]{Style.RESET_ALL}",
        "INFO":    f"{Fore.YELLOW}[{Fore.CYAN}INF{Fore.YELLOW}]{Style.RESET_ALL}",
        "RETRY":   f"{Fore.YELLOW}[{Fore.MAGENTA}RTY{Fore.YELLOW}]{Style.RESET_ALL}",
        "SKIP":    f"{Fore.YELLOW}[{Fore.LIGHTYELLOW_EX}SKP{Fore.YELLOW}]{Style.RESET_ALL}",
        "INVALID": f"{Fore.YELLOW}[{Fore.RED}INV{Fore.YELLOW}]{Style.RESET_ALL}",
        "LOCKED":  f"{Fore.YELLOW}[{Fore.YELLOW}LOC{Fore.YELLOW}]{Style.RESET_ALL}",
        "SUMMARY": f"{Fore.YELLOW}[{Fore.CYAN}SUM{Fore.YELLOW}]{Style.RESET_ALL}",
    }

    styled_type = type_styles.get(message_type, f"{Fore.YELLOW}[{message_type[:3].upper()}{Fore.YELLOW}]{Style.RESET_ALL}")

    if message_type == "UPDATED" and "->" in message:
        parts = message.split("->")
        if len(parts) >= 2:
            label = parts[0].strip()
            value = parts[1].strip()
            rest = "->".join(parts[2:]).strip() if len(parts) > 2 else ""
            processed_message = (
                f"{Fore.WHITE}{label}{Style.RESET_ALL} "
                f"{Fore.LIGHTBLACK_EX}->{Style.RESET_ALL} "
                f"{Fore.LIGHTMAGENTA_EX}{value}{Style.RESET_ALL}"
            )
            if rest:
                processed_message += f" {Fore.LIGHTBLACK_EX}->{Style.RESET_ALL} {Fore.WHITE}{rest}{Style.RESET_ALL}"
        else:
            processed_message = message
    else:
        processed_message = message.replace("->", f"{Fore.LIGHTBLACK_EX}->{Style.RESET_ALL}")

    processed_message = re.sub(r"\[\s*([A-Za-z0-9]{8,12}\*{2,4})\s*\]",
                               lambda m: f"{Fore.LIGHTBLACK_EX}[ {Fore.WHITE}{m.group(1)}{Fore.LIGHTBLACK_EX} ]{Style.RESET_ALL}",
                               processed_message)

    if message_type == "UPDATED":
        processed_message = re.sub(r"\[\s*(\d{3}/\d{3})\s*\]",
                                   lambda m: f"{Fore.CYAN}[ {m.group(1)} ]{Style.RESET_ALL}",
                                   processed_message)

    print(f"{current_time()} {styled_type} {color}{processed_message}{Style.RESET_ALL}")

def load_config():
    global config, customization
    try:
        with open("config.json", "r", encoding="utf-8") as file:
            config = json.load(file)
            customization = config.get("CustomizationSettings", {})
            config["RetryLimit"] = spark(1, mayfield(config.get("RetryLimit", 1), 3))
        log("SUCCESS", "Successfully Loaded CONFIG", Fore.YELLOW)
    except Exception as error:
        log("ERROR", f"Failed to load config.json: {error}", Fore.RED)

def load_lines(filepath, label, color, enabled=True, store_key=None):
    if not enabled:
        return []
    try:
        with open(filepath, "r", encoding="utf-8") as file:
            lines = [line.strip() for line in file if line.strip()]
        log("SUCCESS", f"Loaded {label} + count= {len(lines)}", color)
        if store_key:
            loaded_counts[store_key] = len(lines)
        return lines
    except Exception as error:
        log("ERROR", f"Failed to load {label} from {filepath}: {error}", Fore.RED)
        return []

def load_tokens(filepath, label, color, enabled=True, store_key=None):
    if not enabled:
        return []
    try:
        with open(filepath, "r", encoding="utf-8") as file:
            lines = [line.strip() for line in file if line.strip()]
        
        processed_tokens = []
        for line in lines:
            if ':' in line and line.count(':') >= 2:
                parts = line.split(':')
                if len(parts) >= 3:
                    token = ':'.join(parts[2:])
                    processed_tokens.append(token)
                else:
                    processed_tokens.append(line)
            else:
                processed_tokens.append(line)
        
        log("SUCCESS", f"Found tokens + count= {len(processed_tokens)}", color)
        if store_key:
            loaded_counts[store_key] = len(processed_tokens)
        return processed_tokens
    except Exception as error:
        log("ERROR", f"Failed to load {label} from {filepath}: {error}", Fore.RED)
        return []

def load_images(folder, extensions, label, color, enabled=True, store_key=None):
    if not enabled:
        return []
    try:
        if not os.path.exists(folder):
            os.makedirs(folder)
        files = [f for f in os.listdir(folder) if f.lower().endswith(extensions)]
        log("SUCCESS", f"Loaded {label} + count= {len(files)}", color)
        if store_key:
            loaded_counts[store_key] = len(files)
        return files
    except Exception as error:
        log("ERROR", f"Failed to load {label} from {folder}: {error}", Fore.RED)
        return []

def go_online(token):
    try:
        ws = websocket.WebSocket()
        ws.connect('wss://gateway.discord.gg/?v=6&encoding=json')
        hello = json.loads(ws.recv())
        heartbeat_interval = hello['d']['heartbeat_interval'] / 1000

        status = random.choice(['online', 'dnd', 'idle'])
        activity_type = random.choice(['Playing', 'Streaming', 'Watching', 'Listening', ''])

        if activity_type == "Playing":
            gamejson = {"name": "max", "type": 0}
        elif activity_type == 'Streaming':
            gamejson = {"name": "max", "type": 1, "url": "https://twitch.tv/wallibear"}
        elif activity_type == "Listening":
            gamejson = {"name": random.choice(["max", "max"]), "type": 2}
        elif activity_type == "Watching":
            gamejson = {"name": "max", "type": 3}
        else:
            gamejson = None

        auth = {
            "op": 2,
            "d": {
                "token": token,
                "properties": {
                    "$os": "windows",
                    "$browser": "Chrome",
                    "$device": "Windows"
                },
                "presence": {
                    "activities": [gamejson] if gamejson else [],
                    "status": status,
                    "since": 0,
                    "afk": False
                }
            }
        }
        ws.send(json.dumps(auth))
        return ws, heartbeat_interval
    except Exception as e:
        log("ERROR", f"WebSocket Error: {e}", Fore.RED)
        return None, None

def set_offline(ws):
    try:
        if ws:
            offline_payload = {
                "op": 3,
                "d": {
                    "status": "invisible",
                    "since": 0,
                    "activities": [],
                    "afk": False
                }
            }
            ws.send(json.dumps(offline_payload))
            time.sleep(1)
    except Exception as e:
        log("ERROR", f"Error setting offline: {e}", Fore.RED)

async def check_token(session, token):
    headers = {
        "Authorization": token,
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
        "X-Super-Properties": "eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiQ2hyb21lIiwiZGV2aWNlIjoiIiwic3lzdGVtX2xvY2FsZSI6ImVuLVVTIiwiYnJvd3Nlcl91c2VyX2FnZW50IjoiTW96aWxsYS81LjAgKFdpbmRvd3MgTlQgMTAuMDsgV2luNjQ7IHg2NCkgQXBwbGVXZWJLaXQvNTM3LjM2IChLSFRNTCwgbGlrZSBHZWNrbykgQ2hyb21lLzExNi4wLjAuMCBTYWZhcmkvNTM3LjM2IiwiYnJvd3Nlcl92ZXJzaW9uIjoiMTE2LjAuMC4wIiwib3NfdmVyc2lvbiI6IjEwLjAiLCJyZWZlcnJlciI6IiIsInJlZmVycmluZ19kb21haW4iOiIiLCJyZWZlcnJlcl9jdXJyZW50IjoiIiwicmVmZXJyaW5nX2RvbWFpbl9jdXJyZW50IjoiIiwicmVsZWFzZV9jaGFubmVsIjoic3RhYmxlIiwiY2xpZW50X2J1aWxkX251bWJlciI6MjUxNDQxLCJjbGllbnRfZXZlbnRfc291cmNlIjpudWxsfQ=="
    }
    try:
        async with session.get("https://discord.com/api/v9/users/@me", headers=headers) as resp:
            if resp.status == 200:
                return True
            else:
                error = await resp.text()
                log("INVALID", f"token= MTQ4NDc*** + status= Invalid Token", Fore.RED)
                return False
    except Exception as e:
        log("ERROR", f"Token Check Exception -> [ {token[:12]}*** ] -> [ {str(e)} ]", Fore.RED)
        return False

async def update_hypesquad(session, token, retry_count=0):
    house_ids = {"bravery": 1, "brilliance": 2, "balance": 3}
    house = random.choice(list(house_ids.keys()))
    payload = {"house_id": house_ids[house]}
    headers = {
        "Authorization": token,
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
        "X-Super-Properties": "eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiQ2hyb21lIiwiZGV2aWNlIjoiIiwic3lzdGVtX2xvY2FsZSI6ImVuLVVTIiwiYnJvd3Nlcl91c2VyX2FnZW50IjoiTW96aWxsYS81LjAgKFdpbmRvd3MgTlQgMTAuMDsgV2luNjQ7IHg2NCkgQXBwbGVXZWJLaXQvNTM3LjM2IChLSFRNTCwgbGlrZSBHZWNrbykgQ2hyb21lLzExNi40LjAuMCBTYWZhcmkvNTM3LjM2IiwiYnJvd3Nlcl92ZXJzaW9uIjoiMTE2LjAuMC4wIiwib3NfdmVyc2lvbiI6IjEwLjAiLCJyZWZlcnJlciI6IiIsInJlZmVycmluZ19kb21haW4iOiIiLCJyZWZlcnJlcl9jdXJyZW50IjoiIiwicmVmZXJyaW5nX2RvbWFpbl9jdXJyZW50IjoiIiwicmVsZWFzZV9jaGFubmVsIjoic3RhYmxlIiwiY2xpZW50X2J1aWxkX251bWJlciI6MjUxNDQxLCJjbGllbnRfZXZlbnRfc291cmNlIjpudWxsfQ=="
    }
    url = "https://discord.com/api/v9/hypesquad/online"
    try:
        async with session.post(url, headers=headers, json=payload) as resp:
            if resp.status == 204:
                log("UPDATED", f"HypeSquad Badge -> {house.capitalize()} -> [ {token[:12]}** ]", Fore.GREEN)
                return True
            else:
                error = await resp.text()
                if retry_count < config.get("RetryLimit", 1):
                    log("RETRY", f"Retrying HypeSquad ({retry_count + 1}/{config.get('RetryLimit', 1)}) -> [ {token[:12]}** ]", Fore.MAGENTA)
                    await asyncio.sleep(random.uniform(1.0, 2.0))
                    return await update_hypesquad(session, token, retry_count + 1)
                log("ERROR", f"Failed HypeSquad -> [ {token[:12]}** ] -> [ {resp.status} ] - {error}", Fore.RED)
                return False
    except Exception as e:
        if retry_count < config.get("RetryLimit", 1):
            log("RETRY", f"Retrying HypeSquad ({retry_count + 1}/{config.get('RetryLimit', 1)}) -> [ {token[:12]}** ]", Fore.MAGENTA)
            await asyncio.sleep(random.uniform(1.0, 2.0))
            return await update_hypesquad(session, token, retry_count + 1)
        log("ERROR", f"Exception updating HypeSquad: {str(e)}", Fore.RED)
        return False

async def update_name(session, token, name, retry_count=0):
    headers = {
        "authority": "discord.com",
        "method": "PATCH",
        "scheme": "https",
        "accept": "/",
        "accept-encoding": "gzip, deflate, br",
        "accept-language": "en-US",
        "authorization": token,
        "origin": "https://discord.com/",
        "sec-ch-ua": '"Not/A)Brand";v="99", "Brave";v="115", "Chromium";v="115"',
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) discord/1.0.9020 Chrome/108.0.5359.215 Electron/22.3.26 Safari/537.36",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "X-Debug-Options": "bugReporterEnabled",
        "X-Discord-Locale": "en-US",
        "X-Discord-Timezone": "Asia/Calcutta",
        "Content-Type": "application/json",
        "X-Super-Properties": "eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiRGlzY29yZCBDbGllbnQiLCJyZWxlYXNlX2NoYW5uZWwiOiJzdGFibGUiLCJjbGllbnRfdmVyc2lvbiI6IjEuMC45MDIwIiwib3NfdmVyc2lvbiI6IjEwLjAuMTkwNDUiLCJvc19hcmNoIjoieDY0IiwiYXBwX2FyY2giOiJpYTMyIiwiY3lzdGVtX2xvY2FsZSI6ImVuLVVTIiwiYnJvd3Nlcl91c2VyX2FnZW50IjoiTW96aWxsYS81LjAgKFdpbmRvd3MgTlQgMTAuMDsgV09XNjQpIEFwcGxlV2ViS2l0LzUzNy4zNiAoS0hUTUwsIGxpa2UgR2Vja28pIGRpc2NvcmQvMS4wLjkwMjAgQ2hyb21lLzEwOC4wLjUzNTkuMjE1IEVsZWN0cm9uLzIyLjMuMjYgU2FmYXJpLzUzNy4zNiIsImJyb3dzZXJfdmVyc2lvbiI6IjIyLjMuMjYiLCJjbGllbnRfYnVpbGRfbnVtYmVyIjoyNDAyMzcsIm5hdGl2ZV9idWlsZF9udW1iZXIiOjM4NTE3LCJjbGllbnRfZXZlbnRfc291cmNlIjpudWxsLCJkZXNpZ25faWQiOjB9"
    }

    payload = {
        "global_name": name
    }

    try:
        response = sesh.patch("https://discord.com/api/v9/users/@me", json=payload, headers=headers)
        
        if response.status_code == 200:
            log("UPDATED", f"Display Name -> {name} -> [ {token[:12]}** ] -> [ 200/200 ]", Fore.GREEN)
            return True
        else:
            if retry_count < config.get("RetryLimit", 1):
                log("RETRY", f"Retrying Name ({retry_count + 1}/{config.get('RetryLimit', 1)}) -> [ {token[:12]}** ]", Fore.MAGENTA)
                await asyncio.sleep(random.uniform(1.0, 2.0))
                return await update_name(session, token, name, retry_count + 1)
            error = response.text
            log("ERROR", f"Failed Name -> [ {token[:12]}** ] -> [ {response.status_code} ] - {error}", Fore.RED)
            return False
    except Exception as e:
        if retry_count < config.get("RetryLimit", 1):
            log("RETRY", f"Retrying Name ({retry_count + 1}/{config.get('RetryLimit', 1)}) -> [ {token[:12]}** ]", Fore.MAGENTA)
            await asyncio.sleep(random.uniform(1.0, 2.0))
            return await update_name(session, token, name, retry_count + 1)
        log("ERROR", f"Exception updating name: {str(e)}", Fore.RED)
        return False

async def update_pronoun(session, token, pronoun, retry_count=0):
    headers = {
        "authority": "discord.com",
        "accept": "*/*",
        "accept-language": "en-US,en;q=0.9",
        "authorization": token,
        "content-type": "application/json",
        "origin": "https://discord.com",
        "referer": "https://discord.com/channels/@me",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
        "x-debug-options": "bugReporterEnabled",
        "x-discord-locale": "en-US",
        "x-super-properties": "eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiQ2hyb21lIiwiZGV2aWNlIjoiIiwic3lzdGVtX2xvY2FsZSI6ImVuLVVTIiwiYnJvd3Nlcl91c2VyX2FnZW50IjoiTW96aWxsYS81LjAgKFdpbmRvd3MgTlQgMTAuMDsgV2luNjQ7IHg2NCkgQXBwbGVXZWJLaXQvNTM3LjM2IChLSFRNTCwgbGlrZSBHZWNrbykgQ2hyb21lLzExNi4wLjAuMCBTYWZhcmkvNTM3LjM2IiwiYnJvd3Nlcl92ZXJzaW9uIjoiMTE2LjAuMC4wIiwib3NfdmVyc2lvbiI6IjEwLjAiLCJyZWZlcnJlciI6IiIsInJlZmVycmluZ19kb21haW4iOiIiLCJyZWZlcnJlcl9jdXJyZW50IjoiIiwicmVmZXJyaW5nX2RvbWFpbl9jdXJyZW50IjoiIiwicmVsZWFzZV9jaGFubmVsIjoic3RhYmxlIiwiY2xpZW50X2J1aWxkX251bWJlciI6MjUxNDQxLCJjbGllbnRfZXZlbnRfc291cmNlIjpudWxsfQ=="
    }
    payload = {"pronouns": pronoun}
    url = "https://discord.com/api/v9/users/@me/profile"
    try:
        async with session.patch(url, headers=headers, json=payload) as resp:
            if resp.status == 200:
                log("UPDATED", f"Pronouns -> {pronoun} -> [ {token[:12]}** ]", Fore.GREEN)
                return True
            else:
                if retry_count < config.get("RetryLimit", 1):
                    log("RETRY", f"Retrying Pronoun ({retry_count + 1}/{config.get('RetryLimit', 1)}) -> [ {token[:12]}** ]", Fore.MAGENTA)
                    await asyncio.sleep(random.uniform(1.0, 2.0))
                    return await update_pronoun(session, token, pronoun, retry_count + 1)
                error = await resp.text()
                log("ERROR", f"Failed Pronoun -> [ {token[:12]}** ] -> [ {resp.status} ] - {error}", Fore.RED)
                return False
    except Exception as e:
        if retry_count < config.get("RetryLimit", 1):
            log("RETRY", f"Retrying Pronoun ({retry_count + 1}/{config.get('RetryLimit', 1)}) -> [ {token[:12]}** ]", Fore.MAGENTA)
            await asyncio.sleep(random.uniform(1.0, 2.0))
            return await update_pronoun(session, token, pronoun, retry_count + 1)
        log("ERROR", f"Exception updating pronoun: {str(e)}", Fore.RED)
        return False

async def update_bio(session, token, bio, retry_count=0):
    headers = {
        "authority": "discord.com",
        "accept": "*/*",
        "accept-language": "en-US,en;q=0.9",
        "authorization": token,
        "content-type": "application/json",
        "origin": "https://discord.com",
        "referer": "https://discord.com/channels/@me",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
        "x-debug-options": "bugReporterEnabled",
        "x-discord-locale": "en-US",
        "x-super-properties": "eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiQ2hyb21lIiwiZGV2aWNlIjoiIiwic3lzdGVtX2xvY2FsZSI6ImVuLVVTIiwiYnJvd3Nlcl91c2VyX2FnZW50IjoiTW96aWxsYS81LjAgKFdpbmRvd3MgTlQgMTAuMDsgV2luNjQ7IHg2NCkgQXBwbGVXZWJLaXQvNTM3LjM2IChLSFRNTCwgbGlrZSBHZWNrbykgQ2hyb21lLzExNi4wLjAuMCBTYWZhcmkvNTM3LjM2IiwiYnJvd3Nlcl92ZXJzaW9uIjoiMTE2LjAuMC4wIiwib3NfdmVyc2lvbiI6IjEwLjAiLCJyZWZlcnJlciI6IiIsInJlZmVycmluZ19kb21haW4iOiIiLCJyZWZlcnJlcl9jdXJyZW50IjoiIiwicmVmZXJyaW5nX2RvbWFpbl9jdXJyZW50IjoiIiwicmVsZWFzZV9jaGFubmVsIjoic3RhYmxlIiwiY2xpZW50X2J1aWxkX251bWJlciI6MjUxNDQxLCJjbGllbnRfZXZlbnRfc291cmNlIjpudWxsfQ=="
    }
    payload = {"bio": bio}
    url = "https://discord.com/api/v9/users/@me/profile"
    try:
        async with session.patch(url, headers=headers, json=payload) as resp:
            if resp.status == 200:
                log("UPDATED", f"Bio -> {bio} -> [ {token[:12]}** ]", Fore.GREEN)
                return True
            else:
                if retry_count < config.get("RetryLimit", 1):
                    log("RETRY", f"Retrying Bio ({retry_count + 1}/{config.get('RetryLimit', 1)}) -> [ {token[:12]}** ]", Fore.MAGENTA)
                    await asyncio.sleep(random.uniform(1.0, 2.0))
                    return await update_bio(session, token, bio, retry_count + 1)
                error = await resp.text()
                log("ERROR", f"Failed Bio -> [ {token[:12]}** ] -> [ {resp.status} ] - {error}", Fore.RED)
                return False
    except Exception as e:
        if retry_count < config.get("RetryLimit", 1):
            log("RETRY", f"Retrying Bio ({retry_count + 1}/{config.get('RetryLimit', 1)}) -> [ {token[:12]}** ]", Fore.MAGENTA)
            await asyncio.sleep(random.uniform(1.0, 2.0))
            return await update_bio(session, token, bio, retry_count + 1)
        log("ERROR", f"Exception updating bio: {str(e)}", Fore.RED)
        return False

async def update_profile_fields(session, token, name, pronoun=None, bio=None, hypesquad=True, retry_count=0):

    headers = {
        "Authorization": token,
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
        "X-Super-Properties": "eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiQ2hyb21lIiwiZGV2aWNlIjoiIiwic3lzdGVtX2xvY2FsZSI6ImVuLVVTIiwiYnJvd3Nlcl91c2VyX2FnZW50IjoiTW96aWxsYS81LjAgKFdpbmRvd3MgTlQgMTAuMDsgV2luNjQ7IHg2NCkgQXBwbGVXZWJLaXQvNTM3LjM2IChLSFRNTCwgbGlrZSBHZWNrbykgQ2hyb21lLzExNi4wLjAuMCBTYWZhcmkvNTM3LjM2IiwiYnJvd3Nlcl92ZXJzaW9uIjoiMTE2LjAuMC4wIiwib3NfdmVyc2lvbiI6IjEwLjAiLCJyZWZlcnJlciI6IiIsInJlZmVycmluZ19kb21haW4iOiIiLCJyZWZlcnJlcl9jdXJyZW50IjoiIiwicmVmZXJyaW5nX2RvbWFpbl9jdXJyZW50IjoiIiwicmVsZWFzZV9jaGFubmVsIjoic3RhYmxlIiwiY2xpZW50X2J1aWxkX251bWJlciI6MjUxNDQxLCJjbGllbnRfZXZlbnRfc291cmNlIjpudWxsfQ=="
    }
    
    results = {
        'name': False,
        'pronouns': None if pronoun is None else False,
        'bio': None if bio is None else False,
        'hypesquad': False
    }
    
    try:
        name_payload = {"global_name": name}
        try:
            response = sesh.patch(
                "https://discord.com/api/v9/users/@me",
                headers=headers,
                json=name_payload
            )
            if response.status_code == 200:
                results['name'] = True
                log("UPDATED", f"Display Name -> {name} -> [ {token[:12]}** ]", Fore.GREEN)
            else:
                error = response.text
                log("ERROR", f"Name update failed -> [ {token[:12]}** ]: {error}", Fore.RED)
        except Exception as e:
            log("ERROR", f"Name update exception -> [ {token[:12]}** ]: {str(e)}", Fore.RED)

        if pronoun or bio:
            profile_payload = {}
            if pronoun:
                profile_payload["pronouns"] = pronoun
            if bio:
                profile_payload["bio"] = bio
            
            try:
                async with session.patch(
                    "https://discord.com/api/v9/users/@me/profile",
                    headers=headers,
                    json=profile_payload
                ) as resp:
                    if resp.status == 200:
                        if pronoun:
                            results['pronouns'] = True
                            log("UPDATED", f"Pronouns -> {pronoun} -> [ {token[:12]}** ]", Fore.GREEN)
                        if bio:
                            results['bio'] = True
                            log("UPDATED", f"Bio -> {bio} -> [ {token[:12]}** ]", Fore.GREEN)
                    else:
                        error = await resp.text()
                        log("ERROR", f"Profile update failed -> [ {token[:12]}** ]: {error}", Fore.RED)
            except Exception as e:
                log("ERROR", f"Profile update exception -> [ {token[:12]}** ]: {str(e)}", Fore.RED)

        house = random.choice(["bravery", "brilliance", "balance"])
        hypesquad_payload = {"house_id": {"bravery": 1, "brilliance": 2, "balance": 3}[house]}
        
        try:
            async with session.post(
                "https://discord.com/api/v9/hypesquad/online",
                headers=headers,
                json=hypesquad_payload
            ) as resp:
                if resp.status == 204:
                    results['hypesquad'] = True
                    log("UPDATED", f"HypeSquad -> {house.capitalize()} -> [ {token[:12]}** ]", Fore.GREEN)
                else:
                    error = await resp.text()
                    log("ERROR", f"HypeSquad update failed -> [ {token[:12]}** ]: {error}", Fore.RED)
        except Exception as e:
            log("ERROR", f"HypeSquad update exception -> [ {token[:12]}** ]: {str(e)}", Fore.RED)
        
        mandatory_failures = [
            k for k in ['name', 'hypesquad'] 
            if results[k] is False
        ]
        
        optional_failures = [
            k for k in ['pronouns', 'bio'] 
            if results[k] is False
        ]
        
        if (mandatory_failures or optional_failures) and retry_count < config.get("RetryLimit", 1):
            log("RETRY", f"Retrying failed updates -> Mandatory: {mandatory_failures} | Optional: {optional_failures} -> [ {token[:12]}** ] (Attempt {retry_count + 1}/{config.get('RetryLimit', 1)})", Fore.YELLOW)
            await asyncio.sleep(random.uniform(1.0, 2.0))
            return await update_profile_fields(
                session, token,
                name=name,
                pronoun=pronoun if 'pronouns' in optional_failures else None,
                bio=bio if 'bio' in optional_failures else None,
                hypesquad=True,
                retry_count=retry_count + 1
            )
        
        if mandatory_failures:
            log("ERROR", f"Mandatory updates failed after retries -> [ {token[:12]}** ]: {', '.join(mandatory_failures)}", Fore.RED)
            return False
        
        if optional_failures:
            log("WARNING", f"Optional updates failed -> [ {token[:12]}** ]: {', '.join(optional_failures)}", Fore.YELLOW)
        
        return True
        
    except Exception as e:
        log("ERROR", f"Profile update exception -> [ {token[:12]}** ]: {str(e)}", Fore.RED)
        if retry_count < config.get("RetryLimit", 1):
            log("RETRY", f"Retrying due to exception -> [ {token[:12]}** ] (Attempt {retry_count + 1}/{config.get('RetryLimit', 1)})", Fore.YELLOW)
            await asyncio.sleep(random.uniform(1.0, 2.0))
            return await update_profile_fields(
                session, token,
                name=name,
                pronoun=pronoun,
                bio=bio,
                hypesquad=True,
                retry_count=retry_count + 1
            )
        return False

async def upd_pr(session, token, name, pronoun=None, bio=None, avatar_path=None, banner_path=None, retry_count=0):
    headers = {
        "Authorization": token,
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
        "X-Super-Properties": "eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiQ2hyb21lIiwiZGV2aWNlIjoiIiwic3lzdGVtX2xvY2FsZSI6ImVuLVVTIiwiYnJvd3Nlcl91c2VyX2FnZW50IjoiTW96aWxsYS81LjAgKFdpbmRvd3MgTlQgMTAuMDsgV2luNjQ7IHg2NCkgQXBwbGVXZWJLaXQvNTM3LjM2IChLSFRNTCwgbGlrZSBHZWNrbykgQ2hyb21lLzExNi4wLjAuMCBTYWZhcmkvNTM3LjM2IiwiYnJvd3Nlcl92ZXJzaW9uIjoiMTE2LjAuMC4wIiwib3NfdmVyc2lvbiI6IjEwLjAiLCJyZWZlcnJlciI6IiIsInJlZmVycmluZ19kb21haW4iOiIiLCJyZWZlcnJlcl9jdXJyZW50IjoiIiwicmVmZXJyaW5nX2RvbWFpbl9jdXJyZW50IjoiIiwicmVsZWFzZV9jaGFubmVsIjoic3RhYmxlIiwiY2xpZW50X2J1aWxkX251bWJlciI6MjUxNDQxLCJjbGllbnRfZXZlbnRfc291cmNlIjpudWxsfQ=="
    }
    
    results = {
        'name': False,
        'pronouns': None if pronoun is None else False,
        'bio': None if bio is None else False,
        'hypesquad': False,
        'avatar': None if avatar_path is None else False,
        'banner': None if banner_path is None else False
    }
    
    try:
        tasks = []
        
        name_payload = {"global_name": name}
        tasks.append(("name", sesh.patch("https://discord.com/api/v9/users/@me", headers=headers, json=name_payload)))
        
        if pronoun or bio:
            profile_payload = {}
            if pronoun:
                profile_payload["pronouns"] = pronoun
            if bio:
                profile_payload["bio"] = bio
            tasks.append(("profile", session.patch("https://discord.com/api/v9/users/@me/profile", headers=headers, json=profile_payload)))
        
        house = random.choice(["bravery", "brilliance", "balance"])
        hypesquad_payload = {"house_id": {"bravery": 1, "brilliance": 2, "balance": 3}[house]}
        tasks.append(("hypesquad", session.post("https://discord.com/api/v9/hypesquad/online", headers=headers, json=hypesquad_payload)))
        
        if avatar_path and os.path.exists(avatar_path):
            try:
                file_size = os.path.getsize(avatar_path) / (1024 * 1024)
                if file_size <= 10:
                    with open(avatar_path, "rb") as f:
                        img_data = f.read()
                        ext = os.path.splitext(avatar_path)[1].lower().replace('.', '')
                        mime_type = "image/gif" if ext == "gif" else f"image/{'jpeg' if ext == 'jpg' else ext}"
                        b64 = base64.b64encode(img_data).decode()
                        avatar_data = f"data:{mime_type};base64,{b64}"
                    
                    avatar_payload = {"avatar": avatar_data}
                    tasks.append(("avatar", sesh.patch("https://discord.com/api/v9/users/@me", headers=headers, json=avatar_payload)))
            except Exception as e:
                log("ERROR", f"Avatar preparation failed -> [ {token[:12]}** ]: {str(e)}", Fore.RED)
        
        if banner_path and os.path.exists(banner_path):
            try:
                profile_response = sesh.get("https://discord.com/api/v9/users/@me", headers=headers)
                if profile_response.status_code == 200:
                    profile_data = profile_response.json()
                    if profile_data.get("premium_type", 0):
                        with open(banner_path, "rb") as f:
                            img_data = f.read()
                            ext = os.path.splitext(banner_path)[1].lower().replace('.', '')
                            if ext == "jpg":
                                ext = "jpeg"
                            b64 = base64.b64encode(img_data).decode()
                            banner_data = f"data:image/{ext};base64,{b64}"
                        
                        banner_payload = {"banner": banner_data}
                        tasks.append(("banner", sesh.patch("https://discord.com/api/v9/users/@me", headers=headers, json=banner_payload)))
                    else:
                        log("SKIP", f"Account has no nitro -> [ {token[:12]}** ] - Skipping banner update", Fore.YELLOW)
            except Exception as e:
                log("ERROR", f"Banner failed -> [ {token[:12]}** ]: {str(e)}", Fore.RED)
        
        for task_name, task in tasks:
            try:
                if task_name == "profile" or task_name == "hypesquad":
                    async with task as resp:
                        if task_name == "profile":
                            if resp.status == 200:
                                if pronoun:
                                    results['pronouns'] = True
                                    log("UPDATED", f"Pronouns -> {pronoun} -> [ {token[:12]}** ]", Fore.GREEN)
                                if bio:
                                    results['bio'] = True
                                    log("UPDATED", f"Bio -> {bio} -> [ {token[:12]}** ]", Fore.GREEN)
                            else:
                                error = await resp.text()
                                log("ERROR", f"Profile update failed -> [ {token[:12]}** ]: {error}", Fore.RED)
                        elif task_name == "hypesquad":
                            if resp.status == 204:
                                results['hypesquad'] = True
                                log("UPDATED", f"HypeSquad -> {house.capitalize()} -> [ {token[:12]}** ]", Fore.GREEN)
                            else:
                                error = await resp.text()
                                log("ERROR", f"HypeSquad update failed -> [ {token[:12]}** ]: {error}", Fore.RED)
                else:
                    response = task
                    if task_name == "name":
                        if response.status_code == 200:
                            results['name'] = True
                            log("UPDATED", f"Display Name -> {name} -> [ {token[:12]}** ]", Fore.GREEN)
                        else:
                            error = response.text
                            log("ERROR", f"Name update failed -> [ {token[:12]}** ]: {error}", Fore.RED)
                    elif task_name == "avatar":
                        if response.status_code == 200:
                            results['avatar'] = True
                            log("UPDATED", f"Avatar -> {os.path.basename(avatar_path)} -> [ {token[:12]}** ]", Fore.GREEN)
                        else:
                            error = response.text
                            log("ERROR", f"Avatar update failed -> [ {token[:12]}** ]: {error}", Fore.RED)
                    elif task_name == "banner":
                        if response.status_code == 200:
                            results['banner'] = True
                            log("UPDATED", f"Banner -> {os.path.basename(banner_path)} -> [ {token[:12]}** ]", Fore.GREEN)
                        else:
                            error = response.text
                            log("ERROR", f"Banner update failed -> [ {token[:12]}** ]: {error}", Fore.RED)
            except Exception as e:
                log("ERROR", f"{task_name} update exception -> [ {token[:12]}** ]: {str(e)}", Fore.RED)
        
        mandatory_failures = [
            k for k in ['name', 'hypesquad'] 
            if results[k] is False
        ]
        
        optional_failures = [
            k for k in ['pronouns', 'bio', 'avatar', 'banner'] 
            if results[k] is False
        ]
        
        if (mandatory_failures or optional_failures) and retry_count < config.get("RetryLimit", 1):
            log("RETRY", f"Retrying failed updates -> Mandatory: {mandatory_failures} | Optional: {optional_failures} -> [ {token[:12]}** ] (Attempt {retry_count + 1}/{config.get('RetryLimit', 1)})", Fore.YELLOW)
            await asyncio.sleep(random.uniform(1.0, 2.0))
            return await upd_pr(
                session, token,
                name=name,
                pronoun=pronoun if 'pronouns' in optional_failures else None,
                bio=bio if 'bio' in optional_failures else None,
                avatar_path=avatar_path if 'avatar' in optional_failures else None,
                banner_path=banner_path if 'banner' in optional_failures else None,
                retry_count=retry_count + 1
            )
        
        if mandatory_failures:
            log("ERROR", f"Mandatory updates failed after retries -> [ {token[:12]}** ]: {', '.join(mandatory_failures)}", Fore.RED)
            return False
        
        if optional_failures:
            log("WARNING", f"Optional updates failed -> [ {token[:12]}** ]: {', '.join(optional_failures)}", Fore.YELLOW)
        
        return True
        
    except Exception as e:
        log("ERROR", f"Fast profile update exception -> [ {token[:12]}** ]: {str(e)}", Fore.RED)
        if retry_count < config.get("RetryLimit", 1):
            log("RETRY", f"Retrying due to exception -> [ {token[:12]}** ] (Attempt {retry_count + 1}/{config.get('RetryLimit', 1)})", Fore.YELLOW)
            await asyncio.sleep(random.uniform(1.0, 2.0))
            return await upd_pr(
                session, token,
                name=name,
                pronoun=pronoun,
                bio=bio,
                avatar_path=avatar_path,
                banner_path=banner_path,
                retry_count=retry_count + 1
            )
        return False

def update_avatar(token, image_path, retry_count=0):
    if not os.path.exists(image_path):
        if retry_count < config.get("RetryLimit", 1):
            log("RETRY", f"Retrying Avatar ({retry_count + 1}/{config.get('RetryLimit', 1)}) -> [ {token[:12]}** ]", Fore.MAGENTA)
            time.sleep(random.uniform(2.0, 3.0))
            return update_avatar(token, image_path, retry_count + 1)
        log("ERROR", f"Avatar image not found: {image_path}", Fore.RED)
        return False

    try:
        headers = {
            "authorization": token,
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        check_response = sesh.get(
            "https://discord.com/api/v9/users/@me",
            headers=headers
        )
        
        if check_response.status_code != 200:
            if retry_count < config.get("RetryLimit", 1):
                log("RETRY", f"Retrying Token Check ({retry_count + 1}/{config.get('RetryLimit', 1)}) -> [ {token[:12]}** ]", Fore.MAGENTA)
                time.sleep(random.uniform(3.0, 5.0))
                return update_avatar(token, image_path, retry_count + 1)
            log("ERROR", f"Invalid Token Session -> [ {token[:12]}** ] -> [ {check_response.status_code} ]", Fore.RED)
            return False

        file_size = os.path.getsize(image_path) / (1024 * 1024)
        if file_size > 10:
            log("ERROR", f"Avatar too large ({file_size:.2f}MB > 10MB limit)", Fore.RED)
            return False

        with open(image_path, "rb") as f:
            img_data = f.read()
            ext = os.path.splitext(image_path)[1].lower().replace('.', '')
            mime_type = "image/gif" if ext == "gif" else f"image/{'jpeg' if ext == 'jpg' else ext}"
            b64 = base64.b64encode(img_data).decode()
            avatar_data = f"data:{mime_type};base64,{b64}"

        headers.update({
            "content-type": "application/json",
            "x-super-properties": "eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiQ2hyb21lIiwiZGV2aWNlIjoiIiwic3lzdGVtX2xvY2FsZSI6ImVuLVVTIiwiYnJvd3Nlcl91c2VyX2FnZW50IjoiTW96aWxsYS81LjAgKFdpbmRvd3MgTlQgM10uMDsgV2luNjQ7IHg2NCkgQXBwbGVXZWJLaXQvNTM3LjM2IChLSFRNTCwgbGlrZSBHZWNrbykgQ2hyb21lLzEyMC4wLjAuMCBTYWZhcmkvNTM3LjM2IiwiYnJvd3Nlcl92ZXJzaW9uIjoiMTIwLjAuMC4wIiwib3NfdmVyc2lvbiI6IjEwLjAiLCJyZWZlcnJlciI6IiIsInJlZmVycmluZ19kb21haW4iOiIiLCJyZWZlcnJlcl9jdXJyZW50IjoiIiwicmVmZXJyaW5nX2RvbWFpbl9jdXJyZW50IjoiIiwicmVsZWFzZV9jaGFubmVsIjoic3RhYmxlIiwiY2xpZW50X2J1aWxkX251bWJlciI6MjUxNDQxLCJjbGllbnRfZXZlbnRfc291cmNlIjpudWxsfQ=="
        })

        payload = {"avatar": avatar_data}

        response = sesh.patch(
            "https://discord.com/api/v9/users/@me",
            headers=headers,
            json=payload
        )

        if response.status_code == 200:
            log("UPDATED", f"PFP -> {os.path.basename(image_path)} -> [ {token[:12]}** ]", Fore.GREEN)
            return True
        else:
            error = response.text
            if retry_count < config.get("RetryLimit", 1):
                log("RETRY", f"Retrying Avatar ({retry_count + 1}/{config.get('RetryLimit', 1)}) -> [ {token[:12]}** ]", Fore.MAGENTA)
                time.sleep(random.uniform(3.0, 5.0))
                return update_avatar(token, image_path, retry_count + 1)
            log("ERROR", f"PFP Fail -> [ {token[:12]}** ] -> [ {response.status_code} ] - {error}", Fore.RED)
            return False

    except Exception as e:
        if retry_count < config.get("RetryLimit", 1):
            log("RETRY", f"Retrying Avatar ({retry_count + 1}/{config.get('RetryLimit', 1)}) -> [ {token[:12]}** ]", Fore.MAGENTA)
            time.sleep(random.uniform(3.0, 5.0))
            return update_avatar(token, image_path, retry_count + 1)
        log("ERROR", f"Exception setting PFP: {str(e)}", Fore.RED)
        return False

def update_banner(token, image_path, retry_count=0):
    try:
        headers = {
            "authorization": token,
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        profile_response = sesh.get(
            "https://discord.com/api/v9/users/@me",
            headers=headers
        )
        
        if profile_response.status_code == 200:
            profile_data = profile_response.json()
            if not profile_data.get("premium_type", 0):
                log("SKIP", f"Account has no nitro -> [ {token[:12]}** ] - Skipping banner update", Fore.YELLOW)
                return False
        else:
            if retry_count < config.get("RetryLimit", 1):
                log("RETRY", f"Retrying Nitro Check ({retry_count + 1}/{config.get('RetryLimit', 1)}) -> [ {token[:12]}** ]", Fore.MAGENTA)
                time.sleep(random.uniform(1.0, 2.0))
                return update_banner(token, image_path, retry_count + 1)
            log("ERROR", f"Failed to check nitro status -> [ {token[:12]}** ] -> [ {profile_response.status_code} ]", Fore.RED)
            return False
            
    except Exception as e:
        if retry_count < config.get("RetryLimit", 1):
            log("RETRY", f"Retrying Nitro Check ({retry_count + 1}/{config.get('RetryLimit', 1)}) -> [ {token[:12]}** ]", Fore.MAGENTA)
            time.sleep(random.uniform(1.0, 2.0))
            return update_banner(token, image_path, retry_count + 1)
        log("ERROR", f"Exception checking nitro status: {str(e)}", Fore.RED)
        return False

    if not os.path.exists(image_path):
        if retry_count < config.get("RetryLimit", 1):
            log("RETRY", f"Retrying Banner ({retry_count + 1}/{config.get('RetryLimit', 1)}) -> [ {token[:12]}** ]", Fore.MAGENTA)
            time.sleep(random.uniform(1.0, 2.0))
            return update_banner(token, image_path, retry_count + 1)
        log("ERROR", f"Banner image not found: {image_path}", Fore.RED)
        return False

    try:
        with open(image_path, "rb") as f:
            img_data = f.read()
            ext = os.path.splitext(image_path)[1].lower().replace('.', '')
            if ext == "jpg":
                ext = "jpeg"
            b64 = base64.b64encode(img_data).decode()
            banner_data = f"data:image/{ext};base64,{b64}"

        headers = {
            "authorization": token,
            "content-type": "application/json",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "x-super-properties": "eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiQ2hyb21lIiwiZGV2aWNlIjoiIiwic3lzdGVtX2xvY2FsZSI6ImVuLVVTIiwiYnJvd3Nlcl91c2VyX2FnZW50IjoiTW96aWxsYS81LjAgKFdpbmRvd3MgTlQgMTAuMDsgV2luNjQ7IHg2NCkgQXBwbGVXZWJLaXQvNTM3LjM2IChLSFRNTCwgbGlrZSBHZWNrbykgQ2hyb21lLzEyMC4wLjAuMCBTYWZhcmkvNTM3LjM2IiwiYnJvd3Nlcl92ZXJzaW9uIjoiMTIwLjAuMC4wIiwib3NfdmVyc2lvbiI6IjEwLjAiLCJyZWZlcnJlciI6IiIsInJlZmVycmluZ19kb21haW4iOiIiLCJyZWZlcnJlcl9jdXJyZW50IjoiIiwicmVmZXJyaW5nX2RvbWFpbl9jdXJyZW50IjoiIiwicmVsZWFzZV9jaGFubmVsIjoic3RhYmxlIiwiY2xpZW50X2J1aWxkX251bWJlciI6MjUxNDQxLCJjbGllbnRfZXZlbnRfc291cmNlIjpudWxsfQ=="
        }

        payload = {"banner": banner_data}

        response = sesh.patch(
            "https://discord.com/api/v9/users/@me",
            headers=headers,
            json=payload
        )

        if response.status_code == 200:
            log("UPDATED", f"Banner -> {os.path.basename(image_path)} -> [ {token[:12]}** ]", Fore.GREEN)
            return True
        else:
            error = response.text
            if retry_count < config.get("RetryLimit", 1):
                log("RETRY", f"Retrying Banner ({retry_count + 1}/{config.get('RetryLimit', 1)}) -> [ {token[:12]}** ]", Fore.MAGENTA)
                time.sleep(random.uniform(1.0, 2.0))
                return update_banner(token, image_path, retry_count + 1)
            log("ERROR", f"Banner Fail -> [ {token[:12]}** ] -> [ {response.status_code} ] - {error}", Fore.RED)
            return False

    except Exception as e:
        if retry_count < config.get("RetryLimit", 1):
            log("RETRY", f"Retrying Banner ({retry_count + 1}/{config.get('RetryLimit', 1)}) -> [ {token[:12]}** ]", Fore.MAGENTA)
            time.sleep(random.uniform(1.0, 2.0))
            return update_banner(token, image_path, retry_count + 1)
        log("ERROR", f"Exception setting Banner: {str(e)}", Fore.RED)
        return False


async def main():
    # install_requirements()
    start_time = datetime.now()
    clear_console()
    set_console_title()
    show_interface()

    if not os.path.exists("config.json"):
        log("ERROR", "config.json not found")
        exit()

    load_config()

    tokens  = load_tokens("input/tokens.txt", "Tokens",   Fore.YELLOW, True, "Tokens")
    names   = load_lines("data/names.txt",    "names",    Fore.YELLOW, customization.get("DisplayName", False), "Global Names")
    pronouns= load_lines("data/pronouns.txt", "pronouns", Fore.YELLOW, customization.get("Pronouns", False),    "Pronouns")
    bios    = load_lines("data/bios.txt",     "Bids",     Fore.YELLOW, customization.get("Bio", False),         "Bios")
    avatars = load_images("avatar",   (".png", ".jpg", ".jpeg", ".webp"), "avatars", Fore.YELLOW, customization.get("Avatar", False),  "Profile Pictures")
    banners = load_images("banners",  (".png", ".jpg", ".jpeg", ".webp"), "banners", Fore.YELLOW, customization.get("Banner", False),  "Banners")

    # ── summary line matching the screenshot ─────────────────────────────────
    log("INFO", f"Humanizing Started", Fore.CYAN)

    success_count = 0
    fail_count    = 0
    locked_count  = 0

    if not tokens:
        log("ERROR", "No tokens loaded!", Fore.RED)
        return

    async with aiohttp.ClientSession() as session:
        for idx, token in enumerate(tokens):
            try:
                if idx > 0:
                    await asyncio.sleep(random.uniform(1.0, 2.0))

                ws, heartbeat_interval = go_online(token)
                if not ws:
                    log("ERROR", f"Failed to connect WebSocket for token -> [ {token[:12]}** ]", Fore.RED)
                    fail_count += 1
                    continue

                valid = await check_token(session, token)
                if not valid:
                    ws.close()
                    fail_count += 1
                    continue

                avatar_path = None
                banner_path = None
                
                if avatars:
                    avatar_path = os.path.join("avatar", random.choice(avatars))
                
                if banners:
                    banner_path = os.path.join("banners", random.choice(banners))
                
                result = await upd_pr(
                    session,
                    token,
                    name=random.choice(names) if names else "User",
                    pronoun=random.choice(pronouns) if pronouns else None,
                    bio=random.choice(bios) if bios else None,
                    avatar_path=avatar_path,
                    banner_path=banner_path
                )

                if result:
                    success_count += 1
                else:
                    fail_count += 1

            except Exception as e:
                log("ERROR", f"Exception for token {token[:12]}**: {e}", Fore.RED)
                fail_count += 1
            try:
                if 'ws' in locals():
                    ws.close()
            except:
                pass
        
        await asyncio.sleep(1)

    end_time       = datetime.now()
    execution_time = (end_time - start_time).total_seconds()

    log("INFO",    f"Humanizing Completed + elapsed= {execution_time:.1f}s", Fore.CYAN)
    log("INFO",    f"Total Processed + count= {len(tokens)}",                Fore.CYAN)
    log("SUMMARY", f"Successful + count= {success_count}",                   Fore.GREEN)
    log("SUMMARY", f"Failed + count= {fail_count}",                          Fore.RED)
    log("SUMMARY", f"Locked Tokens + count= {locked_count}",                 Fore.YELLOW)

if __name__ == "__main__":
    asyncio.run(main())
