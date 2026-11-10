import os
import re
import time
import random
import hashlib
import sys
import json
import base64
import threading
from typing import Dict, List, Optional, Tuple, Union
from enum import Enum, IntEnum
from concurrent.futures import ThreadPoolExecutor
from base64 import b64encode
import yaml
import requests
import httpx
import tls_client
import websocket
import pytz
import datetime
import discord
from discord.ui import Modal, TextInput
from discord_webhook import DiscordWebhook, DiscordEmbed
from pystyle import Colors, Colorate, Center
import authsystem
from logger import info, warn, fail, success, debug
import logger
from payment import archive_used_tokens

def create_folder(folder_path):
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

def create_file(file_path):
    if not os.path.exists(file_path):
        with open(file_path, 'w') as f:
            f.write('')

def create_session_folder():
    ist = pytz.timezone('Asia/Kolkata')
    current_time = datetime.datetime.now(ist)
    folder_name = current_time.strftime("%d-%m-%Y %H-%M")
    session_path = f"output/{folder_name}"
    if not os.path.exists(session_path):
        os.makedirs(session_path)
    return session_path

def setup_folders_and_files():
    paths = {
        'keys_folder': 'data/keys',
        'keys_file': 'data/keys/keys.json',
        'used_keys_file': 'data/keys/used_keys.json',
        'output_folder': 'data/output',
        'success_file': 'data/output/success.txt',
        'failed_boosts_file': 'data/output/failed_boosts.txt',
        'data_folder': 'data',
        'one_million_file': 'data/1m.txt',
        'three_month_file': 'data/3m.txt',
        'proxies_file': 'data/proxies.txt'
    }
    for folder in ['data', 'data/keys', 'data/output', 'output']:
        create_folder(folder)
    for file in paths.values():
        if '.' in os.path.basename(file):
            create_file(file)

setup_folders_and_files()
class Fore:
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    UNDERLINE = "\033[4m"
    RESET = "\033[0m"



with open("config/config.yaml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)
oconfig = json.load(open("config/onliner.json", encoding="utf-8"))

webhook_url = config['discord']['webhook_url']
use_log = config['extras']['use_log']
def send_webhook_message(webhook_url, content, embed):
    webhook = DiscordWebhook(url=webhook_url, content=content)
    webhook.add_embed(embed)
    response = webhook.execute()
    if response.status_code in [200, 201, 202, 203, 204, 205, 206, 207]:
        pass
    else:
        logger.error(f"Failed to send message. Status code: {response.status_code}")


def log_error(error_message):
    log_directory = "database"
    log_file = "errors.txt"
    if not os.path.exists(log_directory):
        os.makedirs(log_directory)
    with open(os.path.join(log_directory, log_file), "a") as file:
        file.write(error_message + "\n")

api_key = config['extras']['captcha_solver']['hcoptcha_api_key']
cs_api_key = config['extras']['captcha_solver']['capsolver_api_key']
csolver = config['extras']['captcha_solver']['capsolver_api_key']

h_proxy = None


class Status(Enum):
    ONLINE = "online" 
    DND = "dnd"  
    IDLE = "idle" 
    INVISIBLE = "invisible"  
    OFFLINE = "offline" 


class Activity(Enum):
    GAME = 0  
    STREAMING = 1  
    LISTENING = 2  
    WATCHING = 3  
    CUSTOM = 4  
    COMPETING = 5 


class OPCodes(Enum):
    Dispatch = 0  
    Heartbeat = 1
    Identify = 2 
    PresenceUpdate = 3
    VoiceStateUpdate = 4
    Resume = 6  
    Reconnect = 7  
    RequestGuildMembers = (
        8  
    )
    InvalidSession = 9  
    Hello = (
        10  
    )
    HeartbeatACK = 11 


class DiscordIntents(IntEnum):
    GUILDS = 1 << 0
    GUILD_MEMBERS = 1 << 1
    GUILD_MODERATION = 1 << 2
    GUILD_EMOJIS_AND_STICKERS = 1 << 3
    GUILD_INTEGRATIONS = 1 << 4
    GUILD_WEBHOOKS = 1 << 5
    GUILD_INVITES = 1 << 6
    GUILD_VOICE_STATES = 1 << 7
    GUILD_PRESENCES = 1 << 8
    GUILD_MESSAGES = 1 << 9
    GUILD_MESSAGE_REACTIONS = 1 << 10
    GUILD_MESSAGE_TYPING = 1 << 11
    DIRECT_MESSAGES = 1 << 12
    DIRECT_MESSAGE_REACTIONS = 1 << 13
    DIRECT_MESSAGE_TYPING = 1 << 14
    MESSAGE_CONTENT = 1 << 15
    GUILD_SCHEDULED_EVENTS = 1 << 16
    AUTO_MODERATION_CONFIGURATION = 1 << 20
    AUTO_MODERATION_EXECUTION = 1 << 21


class Presence:
    def __init__(self, online_status: Status) -> None:
        self.online_status: Status = online_status
        self.activities: List[Activity] = []

    def addActivity(
        self, name: str, activity_type: Activity, url: Optional[str]
    ) -> int:

        self.activities.append(
            {
                "name": name,
                "type": activity_type.value, 
                "url": url if activity_type == Activity.STREAMING else None,
            }
        )
        return len(self.activities) - 1

    def removeActivity(self, index: int) -> bool:
        if index < 0 or index >= len(self.activities):
            return False
        self.activities.pop(index)
        return True
import websocket

class AvatarSocket:
    def __init__(self) -> None:
        self.ws = websocket.create_connection("wss://gateway.discord.gg/?v=10&encoding=json")
        self.heartbeat_counter = 0

        self.username: str = None
        self.required_action: str = None
        self.heartbeat_interval: int = None
        self.last_heartbeat: float = None

    def get_heatbeat_interval(self) -> None:
        resp: Dict = json.loads(self.ws.recv())
        self.heartbeat_interval = resp["d"]["heartbeat_interval"]

    def authenticate(self, token: str, rich) -> Union[Dict, bool]:
        payload = {
            "op": OPCodes.Identify.value,
            "d": {
                "token": token,
                "intents": 513,  
                "properties": {
                    "os": "linux",  
                    "browser": "Brave",  
                    "device": "Desktop",
                },
                "presence": {
                    "activities": [activity for activity in rich.activities],  
                    "status": rich.online_status.value,  
                    "since": int(time.time()),  
                    "afk": False, 
                },
            }
        }
        self.ws.send(json.dumps(payload))
        try:
            resp = json.loads(self.ws.recv())
            self.username = resp["d"]["user"]["username"]
            self.required_action = resp["d"].get("required_action")
            self.heartbeat_counter += 1
            self.last_heartbeat = time.time()
            return resp
        except Exception:
            return False

    def send_heartbeat(self):
        self.ws.send(json.dumps({"op": OPCodes.Heartbeat.value, "d": None}))
        self.heartbeat_counter += 1
        self.last_heartbeat = time.time()
        return self.ws.recv()
    
    @staticmethod
    def avatar_socket(token: str, activity: Presence):
        try:
            socket = AvatarSocket()
            socket.get_heatbeat_interval()
        except Exception as e:
            return

        auth_resp = socket.authenticate(token, activity)
        if not auth_resp:
            return
            
        while True:
            try:
                if (time.time() - socket.last_heartbeat >= (socket.heartbeat_interval / 1000) - 5):  
                    socket.send_heartbeat()
                time.sleep(0.5)
            except Exception:
                pass

    def run_socket(self, token):
        try:
            with open("config/onliner.json", "r") as config_file:
                config: Dict[str, Union[List[str], Dict[str, List[str]]]] = json.loads(config_file.read())
        except Exception:
            # Fallback if someone deletes the config formatting
            config = {"choose_random_activity_type_from": ["game"], "choose_random_online_status_from": ["online"], "game": {"choose_random_game_from": ["Code Hub"]}}

        activity_types: List[Activity] = [Activity[x.upper()] for x in config.get("choose_random_activity_type_from", ["game"])]
        online_statuses: List[Status] = [Status[x.upper()] for x in config.get("choose_random_online_status_from", ["online"])]

        online_status = random.choice(online_statuses)
        chosen_activity_type = random.choice(activity_types)
        url = None
        name = "Code Hub Tool"

        if chosen_activity_type == Activity.GAME:
            name = random.choice(config.get("game", {}).get("choose_random_game_from", ["Code Hub"]))
        elif chosen_activity_type == Activity.STREAMING:
            name = random.choice(config.get("streaming", {}).get("choose_random_name_from", ["Code Hub"]))
            url = random.choice(config.get("streaming", {}).get("choose_random_url_from", ["https://twitch.tv/dev"]))
        elif chosen_activity_type == Activity.LISTENING:
            name = random.choice(config.get("listening", {}).get("choose_random_name_from", ["Code Hub"]))
        elif chosen_activity_type == Activity.WATCHING:
            name = random.choice(config.get("watching", {}).get("choose_random_name_from", ["Code Hub"]))
        elif chosen_activity_type == Activity.CUSTOM:
            name = random.choice(config.get("custom", {}).get("choose_random_name_from", ["Code Hub"]))

        activity = Presence(online_status)
        activity.addActivity(activity_type=chosen_activity_type, name=name, url=url)
        
        x = Thread(target=AvatarSocket.avatar_socket, args=(token, activity))
        x.daemon = True
        x.start()


try:
    h_proxy=random.choice(open("data/proxies.txt", "r").read().splitlines())
except:
    h_proxy=None
def h_captcha(sitekey, url, rqdata):
    p1 = {
	"task_type": "hcaptchaEnterprise",
	"api_key": f"{api_key}",
	"data": {
		"sitekey": sitekey,
		"url": url,
		"rqdata": rqdata ,
        "proxy": h_proxy
	}
    }
    h1 = {"Content-Type": "application/json"}

    r1 = requests.post("https://api.hcoptcha.online/api/createTask", headers=h1, json=p1)
    if r1.json()['error'] != True:
        try:    
            a = r1.json()['task_id']
            return a
        except:
            return False
    else:
        logger.error("Unable to create task")
        print(r1.json())       
        return False

def encoded(path: str):
        try:
            with open(path + random.choice(os.listdir(path)), "rb") as f:
                img = f.read()
            return f'data:image/png;base64,{b64encode(img).decode("ascii")}'
        except Exception as e:
            logger.error(f'Encoding Error: {str(e).capitalize()}')
            pass

def h_result(task_id):
    p2 = {
	"api_key": f"{api_key}",
	"task_id": task_id }
    h2 = {"Content-Type": "application/json"}
    r2 = requests.post("https://api.hcoptcha.com/api/getTaskData", headers=h2, json=p2)
    if 'captcha_key' in r2.text:
        try:    
            a = r2.json()
            return a
        except:
            return False
    else:
        if config['autobuy']['advance_mode']:
            logger.error(f"Unable to get solution : {r2.json()}")
        return False


def cs_captcha(sitekey, url, rqdata):
    p1 = {

	"clientKey": cs_api_key,
	"task": {
        	"type": "HCaptchaTaskProxyLess",
		"websiteKey": sitekey,
		"websiteURL": url,
		"enterprisePayload": {
      "rqdata": rqdata,
    },
	}
    }
    h1 = {"Content-Type": "application/json"}

    r1 = requests.post("https://api.capsolver.com/createTask", headers=h1, json=p1)
    if not r1.json()['errorId']:
        try:    
            a = r1.json()['taskId']
            return a
        except:
            return False
    else:
        logger.error("Unable to create task")
        if config['advance_mode'] == True:
            logger.error(f"Reason {r1.json()}")    
        return False

def cs_result(task_id):
    p2 = {
	"clientKey": cs_api_key,
	"taskId": task_id }
    h2 = {"Content-Type": "application/json"}
    r2 = requests.post("https://api.capsolver.com/getTaskResult", headers=h2, json=p2)
    if 'solution' in r2.text:
        try:    
            a = r2.json()
            return a
        except:
            a = r2.json()
            return False
            
    else:
        logger.error("Unable to solve captcha")
        if config['advance_mode'] == True:
            print(r2.json())       
        return False

class Booster:
    def __init__(self, session_folder=None) -> None:
        self.session_folder = session_folder or create_session_folder()
        self.proxy = self.getProxy()
        self.crome_v = f'Chrome_{str(random.randint(110, 118))}'
        self.client = tls_client.Session(
            client_identifier=self.crome_v,
            random_tls_extension_order=True,
            ja3_string='771,4865-4866-4867-49195-49199-49196-49200-52393-52392-49171-49172-156-157-47-53,18-23-45-11-27-10-0-5-13-65037-16-51-17513-43-35-65281-41,25497-29-23-24,0',            
        )
        self.locale = random.choice(["af", "af-NA", "af-ZA", "agq", "agq-CM", "ak", "ak-GH", "am", "am-ET", "ar", "ar-001", "ar-AE", "ar-BH", "ar-DJ", "ar-DZ", "ar-EG", "ar-EH", "ar-ER", "ar-IL", "ar-IQ", "ar-JO", "ar-KM", "ar-KW", "ar-LB", "ar-LY", "ar-MA", "ar-MR", "ar-OM", "ar-PS", "ar-QA", "ar-SA", "ar-SD", "ar-SO", "ar-SS", "ar-SY", "ar-TD", "ar-TN", "ar-YE", "as", "as-IN", "asa", "asa-TZ", "ast", "ast-ES", "az", "az-Cyrl", "az-Cyrl-AZ", "az-Latn", "az-Latn-AZ", "bas", "bas-CM", "be", "be-BY", "bem", "bem-ZM", "bez", "bez-TZ", "bg", "bg-BG", "bm", "bm-ML", "bn", "bn-BD", "bn-IN", "bo", "bo-CN", "bo-IN", "br", "br-FR", "brx", "brx-IN", "bs", "bs-Cyrl", "bs-Cyrl-BA", "bs-Latn", "bs-Latn-BA", "ca", "ca-AD", "ca-ES", "ca-FR", "ca-IT", "ccp", "ccp-BD", "ccp-IN", "ce", "ce-RU", "cgg", "cgg-UG", "chr", "chr-US", "ckb", "ckb-IQ", "ckb-IR", "cs", "cs-CZ", "cy", "cy-GB", "da", "da-DK", "da-GL", "dav", "dav-KE", "de", "de-AT", "de-BE", "de-CH", "de-DE", "de-IT", "de-LI", "de-LU", "dje", "dje-NE", "dsb", "dsb-DE", "dua", "dua-CM", "dyo", "dyo-SN", "dz", "dz-BT", "ebu", "ebu-KE", "ee", "ee-GH", "ee-TG", "el", "el-CY", "el-GR", "en", "en-001", "en-150", "en-AG", "en-AI", "en-AS", "en-AT", "en-AU", "en-BB", "en-BE", "en-BI", "en-BM", "en-BS", "en-BW", "en-BZ", "en-CA", "en-CC", "en-CH", "en-CK", "en-CM", "en-CX", "en-CY", "en-DE", "en-DG", "en-DK", "en-DM", "en-ER", "en-FI", "en-FJ", "en-FK", "en-FM", "en-GB", "en-GD", "en-GG"])

        self.useragent = f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) {self.crome_v}.0.0.0 Safari/537.36'
        self.failed = []
        self.success = []
        self.captcha = []
        self.getX()
        self.fingerprints()
        self.proxy = self.getProxy()

    def getX(self):
        properties = {
            "os": 'Windows',
            "browser": 'Chrome',
            "device": "",
            "system_locale": self.locale,
            "browser_user_agent": self.useragent,
            "browser_version": f'{self.crome_v}.0.0.0',
            "os_version": "10",
            "referrer": "",
            "referring_domain": "",
            "referrer_current": "",
            "referring_domain_current": "",
            "release_channel": "stable",
            "client_build_number": 236850,
            "client_event_source": None
        }

        self.x = b64encode(json.dumps(properties, separators=(',', ':')).encode("utf-8")).decode()

    def getProxy(self):
        try:
            proxy = random.choice(open("data/proxies.txt", "r").read().splitlines())
            return {"http": f"http://{proxy}", "https": f"http://{proxy}"}
        except Exception as e:
            return None

    def fingerprints(self):
        headers = {
            "authority": "discord.com",
            "method": "GET",
            "path": "/api/v9/experiments",
            "scheme": "https",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "max-age=0",
            "Priority": "u=0, i",
            "Sec-Ch-Ua": '"Not/A)Brand;v=8", "Chromium;v=126", "Brave;v=126"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": "Windows",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Sec-Gpc": "1",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": self.useragent
            }
        
        tries = 0
        while tries < 10:
            try:
                r = httpx.get(f'https://discord.com/api/v9/experiments', headers=headers)
                break
            except Exception as e:
                print(f'Failed to Execute Request getting fingerprints: ' + str(e).capitalize())
                tries += 1

                if tries == 10:
                    print(f'Max Reties Completed. Failed to Execute: ' + str(e).capitalize())
                    return
            
        if not (r.status_code in (200, 201)):
            logger.error(f'Failed to Fetch Cookies from discord.com. ' + str(r.text).capitalize())
            return ''
        
        self.fp = r.json()['fingerprint']
        self.ckis = f'locale=en-US; __dcfduid={r.cookies.get("__dcfduid")}; __sdcfduid={r.cookies.get("__sdcfduid")}; __cfruid={r.cookies.get("__cfruid")}; _cfuvid={r.cookies.get("_cfuvid")}'

    def boost(self, token, invite, guild):
        headers = {
            "authority": "discord.com",
            "scheme": "https",
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en-US,en;q=0.9",
            "Authorization": str(token),
            "Content-Type": "application/json",
            "Cookie": str(self.ckis),
            "Origin": "https://discord.com",
            "Priority": "u=1, i",
            "Referer": "https://discord.com/channels/@me",
            "Sec-Ch-Ua": '"Not/A)Brand;v=8", "Chromium;v=126", "Brave;v=126"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": "Windows",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Gpc": "1",
            "User-Agent": self.useragent,
            "X-Debug-Options": "bugReporterEnabled",
            "X-Discord-Locale": "en-US",
            "X-Discord-Timezone": "Asia/Calcutta",
            'X-fingerprint': self.fp,
            "X-Super-Properties": self.x
            }

        slots = self.client.get(
            "https://discord.com/api/v9/users/@me/guilds/premium/subscription-slots",
            headers=headers,
        )

        slot_json = slots.json()
        tkv = token

        if slots.status_code == 401:
            logger.error(f"{tkv} Invalid/No-Nitro")
            return
        
        elif slots.status_code != 200 or len(slot_json) == 0:
            logger.error(f"{tkv} Invalid/No-Nitro")
            return

        r = self.client.post(
            f"https://discord.com/api/v9/invites/{invite}", headers=headers, json={}
        )

        if r.status_code == 200:
            self.guild_id = r.json()["guild"]["id"]
            boostsList = []
            for boost in slot_json:
                boostsList.append(boost["id"])

            payload = {"user_premium_guild_subscription_slot_ids": boostsList}

            headers["method"] = "PUT"
            headers["path"] = f"/api/v9/guilds/{guild}/premium/subscriptions"

            boosted = self.client.put(
                f"https://discord.com/api/v9/guilds/{guild}/premium/subscriptions",
                json=payload,
                headers=headers,
            )

            if boosted.status_code == 201:
              self.success.append(token)
              with open(f"{self.session_folder}/success.txt", "a") as file:
                file.write(token + "\n")
                return True
            else:
             with open(f"{self.session_folder}/failed_boosts.txt", "a") as file:
                file.write(token + "\n")
             self.failed.append(token)

        elif r.status_code != 200:
            join_outcome = False
            max_retries = None
            solve_captcha = None
            tr = 1
            tr0 = 1
            try:
                solve_captcha = config['extras']['captcha_solver']['solve_captcha']
            except:
                solve_captcha = False    
            try:
                max_retries = config['extras']['captcha_solver']['max_retries']

            except:
                max_retries = 2
            cap_service = None
            try:
                if config['extras']['captcha_solver']['use'] == "hcoptcha":
                    cap_service = 1
                elif config['extras']['captcha_solver']['use'] == "capsolver":
                    cap_service = 2
                else:
                    cap_service = 3
            except:
                logger.error("Captcha service can be either hcoptcha or capsolver please update it in config file!")

            if "captcha" in r.text:
              logger.error(f"Captcha Detected : {tkv}")
              with open (f"{self.session_folder}/captcha.txt", "a") as f:
                  f.write(token + "\n")
                  self.captcha.append(token)
              if config['extras']['captcha_solver']['solve_captcha'] == True:
                retry = 0
                while join_outcome != True and retry < max_retries and cap_service != None:
                    r = self.client.post(
                f"https://discord.com/api/v9/invites/{invite}", headers=headers, json={}
            )
                    response = r.json()
                    if cap_service != 3:
                        if cap_service == 1:
                            s1 = h_captcha(response['captcha_sitekey'], f"https://discord.com/invite/{invite}", response['captcha_rqdata'])
                        elif cap_service == 2:
                            s1 = cs_captcha(response['captcha_sitekey'], f"https://discord.com/invite/{invite}", response['captcha_rqdata'])
                        task_id = s1
                        logger.info(f"Solving Captcha : {tkv}")
                        time.sleep(10)
                        if cap_service == 1:
                            s2 = h_result(task_id)
                        else:
                            s2 = cs_result(task_id)
                    s3 = None
                    try:
                        if cap_service == 1:
                            s3 = s2['task']['captcha_key']
                        elif cap_service == 2:
                            s3 = s2['solution']['gRecaptchaResponse']
                        else:
                            s3 = csolve(response['captcha_sitekey'], f"https://discord.com/invite/{invite}", response['captcha_rqdata'])
                    except:
                        pass
                    req2headers = headers
                    req2headers.pop("Content-Length", None)
                    try: 
                        req2headers["X-Captcha-Key"] = s3 
                        req2headers["X-Captcha-Rqtoken"] = response['captcha_rqtoken']
                    except:
                        pass
                    response = self.client.post(f'https://discord.com/api/v9/invites/{invite}', json={}, headers = req2headers)
                    if response.status_code in [200, 204]:
                        join_outcome = True
                        self.guild_id = response.json()["guild"]["id"]
                        logger.info(f"Captcha Solved : {tkv}")
                        boostsList = []
                        for boost in slot_json:
                            boostsList.append(boost["id"])

                        payload = {"user_premium_guild_subscription_slot_ids": boostsList}

                        headers["method"] = "PUT"
                        headers["path"] = f"/api/v9/guilds/{guild}/premium/subscriptions"

                        boosted = self.client.put(
                            f"https://discord.com/api/v9/guilds/{guild}/premium/subscriptions",
                            json=payload,
                            headers=headers, proxy=self.proxy
                        )

                        if boosted.status_code == 201:
                            self.success.append(token)
                            with open(f"{self.session_folder}/success.txt", "a") as file:
                                file.write(token + "\n")
                                logger.info(f"Boosts Successful : {tkv}")
                        else:
                            with open(f"{self.session_folder}/failed_boosts.txt", "a") as file:
                                file.write(token + "\n")
                                self.failed.append(token)
                                logger.error(f"Boosts Failed : {tkv}")
                        break
                    else:
                        if "10008" in response.text:
                            logger.error(f"Token Flagged [ Unable To Join Even After A Valid Captcha Solution ]: {tkv}")
                            self.failed.append(token)
                            break
                        retry += 1
                        logger.info(f"Retrying Solving Captcha : {tkv} [ {retry}/{max_retries} ]")
            elif not "captcha" in r.text:
                tkv = token[:-8] + "*" * 8

                boostsList = []
                for boost in slot_json:
                    boostsList.append(boost["id"])

                payload = {"user_premium_guild_subscription_slot_ids": boostsList}

                headers["method"] = "PUT"
                headers["path"] = f"/api/v9/guilds/{guild}/premium/subscriptions"

                boosted = self.client.put(
                    f"https://discord.com/api/v9/guilds/{guild}/premium/subscriptions",
                    json=payload,
                    headers=headers, proxy=self.proxy
                )

                if boosted.status_code == 201:
                    self.success.append(token)
                    with open(f"{self.session_folder}/success.txt", "a") as file:
                        file.write(token + "\n")
                        logger.info(f"Boosts Successful : {tkv}")
                        return True
                else:
                    with open(f"{self.session_folder}/failed_boosts.txt", "a") as file:
                        file.write(token + "\n")
                        self.failed.append(token)
                        logger.error(f"Boosts Failed : {tkv}")
                


    def humanizer(self, token, nickname=None, bio=None):
        if ':' in str(token):
            token = str(token).split(':')[2]

        else:
            token = token
        
        apiurl = 'https://discord.com/api/v9/guilds/' + self.guild_id + '/members/@me'
        ap = []
        headers = {
            "authority": "discord.com",
            "scheme": "https",
            'method': 'PATCH',
            'path': f'/api/v9/guilds/' + self.guild_id + '/members/@me',
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en-US,en;q=0.9",
            "Authorization": str(token),
            "Content-Type": "application/json",
            "Cookie": str(self.ckis),
            "Origin": "https://discord.com",
            "Priority": "u=1, i",
            "Referer": "https://discord.com/channels/@me",
            "Sec-Ch-Ua": '"Not/A)Brand;v=8", "Chromium;v=126", "Brave;v=126"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": "Windows",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Gpc": "1",
            "User-Agent": self.useragent,
            "X-Debug-Options": "bugReporterEnabled",
            "X-Discord-Locale": "en-US",
            "X-Discord-Timezone": "Asia/Calcutta",
            'X-fingerprint': self.fp,
            "X-Super-Properties": self.x
            }
        
        h = headers
        h['path'] = '/api/v9/users/@me/profile'


        user_bio = bio if bio and bio.strip() else config['customizations']['bio']
        if user_bio:
            tries = 0
            while tries < 10:
                try:
                    b = self.client.patch(
                        f'https://discord.com/api/v9/users/@me/profile',
                        headers=h,
                        json={"bio": str(user_bio)}
                        )
                    break
                except Exception as e:
                    logger.error(f'Failed to execute Requests: '+str(e).capitalize())
                    tries += 1
                    if tries == 10:
                        return
                    
            if b.status_code == 200:
                ap.append(f'bio')
                    

        user_nick = nickname if nickname and nickname.strip() else config['customizations']['nick']
        if user_nick:
            tries = 0
            while tries < 10:
                try:
                    b= self.client.patch(
                        apiurl,
                        headers=headers,
                        json={"nick": str(user_nick)}
                        )
                    break
                
                except Exception as e:
                    logger.error(f'Failed to execute Requests: '+str(e).capitalize())
                    tries += 1
                    if tries == 10:
                        return
            if b.status_code == 200:
                ap.append(f'nick')
        
        if config['customizations']['use_custom_pfp']:
            tries = 0
            while tries < 10:
                try:
                    b = self.client.patch(
                        apiurl,
                        headers=headers,
                        json={'avatar': encoded(f'data/avatar/')}
                        )
                    break
                
                except Exception as e:
                    logger.error(f'Failed to execute Requests: '+str(e).capitalize())
                    tries += 1
                    if tries == 10:
                        return
            if b.status_code == 200:
                ap.append(f'avatar')
        
        if config['customizations']['use_custom_banner']:
            tries = 0
            while tries < 10:
                try:
                    b = self.client.patch(
                        apiurl,
                        headers=headers,
                        json={'banner': (f'data/banner/')}
                        )
                    break
                
                except Exception as e:
                    logger.error(f'Failed to execute Requests: '+str(e).capitalize())
                    tries += 1
                    if tries == 10:
                        return
            
            if b.status_code == 200:
                ap.append(f'banner')
        
        if len(ap) in (1,2,3,4):
            logger.info(f'Successfully Humanized. {ap}')
        else:
            logger.error(f'Failed to Humanized.')
            return
    
    def humanizerthread(self, tokens, nickname=None, bio=None):
        try:
            threads = []
            thr = len(tokens)
            for i in range(thr):
                token = tokens[i]
                t = threading.Thread(target=self.humanizer(token, nickname, bio), args=())
                t.daemon = True
                threads.append(t)
                
            for i in range(thr):
                threads[i].start()
                
            for i in range(thr):
                threads[i].join()
        
        except Exception as e:
            logger.error(f'Failed to Execute Threads: '+ str(e).capitalize())
            return

    def thread(self, invite, tokens, guild):
        """"""
        threads = []

        for i in range(len(tokens)):
            token = tokens[i]
            t = threading.Thread(target=self.boost, args=(token, invite, guild))
            t.daemon = True
            threads.append(t)

        for i in range(len(tokens)):
            threads[i].start()

        for i in range(len(tokens)):
            threads[i].join()

        return {
            "success": self.success,
            "failed": self.failed,
            "captcha": self.captcha,
        }
    
def getStock(filename: str):
    tokens = []
    for i in open(filename, "r").read().splitlines():
        if ":" in i:
            i = i.split(":")[2]
            tokens.append(i)
        else:
            tokens.append(i)
    return tokens

def remove(token, filename):
    with open(filename, "r") as f:
        lines = f.read().splitlines()
    with open(filename, "w") as f:
        for line in lines:
            if token not in line:
                f.write(line + "\n")

def getStock_Auto(filename: str, num_tokens: int):
    with open(filename, "r") as file:
        lines = file.readlines()

    tokens = []
    remaining_lines = []

    for line in lines[:num_tokens]:
        if ":" in line:
            i = line.split(":")[2]
            tokens.append(i)
        else:
            tokens.append(line)    
    remaining_lines.extend(lines[num_tokens:])
    with open(filename, "w") as file:
        for line in remaining_lines:
            file.write(line)

    return tokens

def getinviteCode(inv):
    if "discord.gg" in inv:
        invite = inv.split("discord.gg/")[1]
        return invite
    if "https://discord.gg" in inv:
        invite = inv.split("https://discord.gg/")[1]
        return invite
    if 'discord.com/invite' in inv:
        invite = inv.split("discord.com/invite/")[1]
        return invite
    if 'https://discord.com/invite/' in inv:
        invite = inv.split("https://discord.com/invite/")[1]
        return invite
    else:
        return inv

def checkInvite(invite: str):
    data = requests.get(
        f"https://discord.com/api/v9/invites/{invite}?inputValue={invite}&with_counts=true&with_expiration=true"
    ).json()

    if data["code"] == 10006:
        return False
    elif data:
        return data["guild"]["id"]
    else:
        return False
class BoostModal(Modal):
    def __init__(self):
        super().__init__(title = "Code Hub - Boost Panel")
        self.add_item(
            TextInput(
                label = "Invite",
                placeholder = "Invite code of the server.",
                required = True,
                style = discord.TextStyle.short
            )
        )

        self.add_item(
            TextInput(
                label = "Amount",
                placeholder = "Amount of boosts (must be in numbers).",
                required = True,
                style = discord.TextStyle.short
            )
        )

        self.add_item(
            TextInput(
                label = "Months",
                placeholder = "Number of months (1/3).",
                required = True,
                style = discord.TextStyle.short
            )
        )

    async def on_submit(self, ctx: discord.Interaction):

        invite = self.children[0].value

        amount = int(self.children[1].value)

        months = int(self.children[2].value)

        await ctx.response.defer()

        if amount % 2 != 0:
            return await ctx.followup.send(
                embed=discord.Embed(
                    title="`Error`",
                    description="`Number of boosts should be in even numbers`",
                    color=0xff00bf,
                )
            )

        if months != 1 and months != 3:
            return await ctx.followup.send(
                embed=discord.Embed(
                    title="`Error`",
                    description="`Invalid Input`",
                    color=0xff00bf,
                )
            )

        inviteCode = getinviteCode(invite)
        inviteData = checkInvite(inviteCode)

        if inviteData == False:
            return await ctx.followup.send(
                embed=discord.Embed(
                    title="`Error`",
                    description=f"`Invalid Invite | .gg/{invite}`",
                    color=0xff00bf,
                )
            )

        if months == 1:
            filename = "data/1m.txt"
        if months == 3:
            filename = "data/3m.txt"

        tokensStock = getStock(filename)
        requiredStock = int(amount / 2)

        if requiredStock > len(tokensStock):
            return await ctx.followup.send(
                embed=discord.Embed(
                    title="`Error`",
                    description=f"`Not enought stock. use the command /restock to restock tokens`",
                    color=0xff00bf,
                )
            )


        session_folder = create_session_folder()
        boost = Booster(session_folder)

        tokens = []

        for x in range(requiredStock):
            tokens.append(tokensStock[x])
            remove(tokensStock[x], filename)

        await ctx.followup.send(
            embed=discord.Embed(
                title="- `Boost Bot Information`", description=f"Joining And Boosting...", color=0xff00e1
            ).set_footer(text="BoostBot Crafted by .gg/coderz")
        )

        start = time.time()
        status = boost.thread(inviteCode, tokens, inviteData)
        time_taken = round(time.time() - start, 2)

        # Archive used tokens to another file so they don't remain in stock
        archive_used_tokens(tokens, f"{months}m", inviteCode)

        await ctx.followup.send(
            embed=discord.Embed(
                title="Boost Bot Information",
                description=f"`Ammount:` {amount}x {months}m Boosts\n`Tokens:` {requiredStock}\n`Server Link:` .gg/{inviteCode}\n`Succeded Boosts:` {len(status['success'])*2}\n`Failed Boosts` {len(status['failed'])}\n`Time Took` {time_taken}seconds\n\n**Failed**```{status['failed']}``` ** Captcha ** \n ``` {status['captcha']}``` \n **Success** \n ``` {status['success']}```",
                color=0xff00bf,
            ).set_footer(text="BoostBot Crafted by .gg/coderz")
        )
        content = ""
        if webhook_url != "" and use_log == True:
            embed = DiscordEmbed(
                title="- ```Boost Bot Information```", 
                description=f"`Ammount:` {amount}x {months}m Boosts\n`Tokens:` {requiredStock}\n`Server Link:` .gg/{inviteCode}\n`Succeded Boosts:` {len(status['success'])*2}\n`Failed Boosts` {len(status['failed'])}\n`Time Took` {time_taken}seconds\n\n**Failed**```{status['failed']}``` ** Captcha ** \n ``` {status['captcha']}``` \n **Success** \n ``` {status['success']}```",
                color=0xff00e1)
            embed.set_footer(text="BoostBot Crafted by .gg/coderz")
            send_webhook_message(webhook_url, content, embed)

        try:
            if config.get('customizations', {}).get('enable', False):
                boost.humanizerthread(tokens=tokens)
        except Exception as e:
            print(e)
