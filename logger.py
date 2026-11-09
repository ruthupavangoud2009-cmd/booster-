import colorama
import time

colorama.init()

def log(message, **kwargs):
    timestamp = time.strftime('%H:%M:%S', time.localtime())
    formatted_message = f"{colorama.Fore.WHITE}[{colorama.Fore.LIGHTMAGENTA_EX}{timestamp}{colorama.Fore.WHITE}] {message}"
    
    if kwargs:
        formatted_message += f" {colorama.Fore.LIGHTBLACK_EX}→ {colorama.Fore.WHITE}"
        for key, value in kwargs.items():
            formatted_message += f"{colorama.Fore.LIGHTBLACK_EX}{key}={colorama.Fore.LIGHTCYAN_EX} {value} "
    
    print(formatted_message)

def fail(message, **kwargs):
    prefix = f"{colorama.Fore.WHITE}[{colorama.Fore.RED}ERR{colorama.Fore.WHITE}]{colorama.Fore.RED} › {message}"
    log(prefix, **kwargs)

def error(message, **kwargs):
    prefix = f"{colorama.Fore.WHITE}[{colorama.Fore.RED}ERR{colorama.Fore.WHITE}]{colorama.Fore.RED} › {message}"
    log(prefix, **kwargs)

def warn(message, **kwargs):
    prefix = f"{colorama.Fore.WHITE}[{colorama.Fore.LIGHTYELLOW_EX}WRN{colorama.Fore.WHITE}]{colorama.Fore.LIGHTYELLOW_EX} › {message}"
    log(prefix, **kwargs)

def success(message, **kwargs):
    prefix = f"{colorama.Fore.WHITE}[{colorama.Fore.LIGHTGREEN_EX}SUC{colorama.Fore.WHITE}]{colorama.Fore.LIGHTGREEN_EX} › {message}"
    log(prefix, **kwargs)

def info(message, **kwargs):
    prefix = f"{colorama.Fore.WHITE}[{colorama.Fore.BLUE}INF{colorama.Fore.WHITE}]{colorama.Fore.LIGHTGREEN_EX} › {message}"
    log(prefix, **kwargs)

def debug(message, **kwargs):
    prefix = f"{colorama.Fore.WHITE}[{colorama.Fore.CYAN}DGB{colorama.Fore.WHITE}]{colorama.Fore.CYAN} › {message}"
    log(prefix, **kwargs)

def captcha(message, **kwargs):
    prefix = f"{colorama.Fore.WHITE}[{colorama.Fore.LIGHTBLUE_EX}CAP{colorama.Fore.WHITE}]{colorama.Fore.LIGHTBLUE_EX} › {message}"
    log(prefix, **kwargs)

def update(message, **kwargs):
    prefix = f"{colorama.Fore.WHITE}[{colorama.Fore.LIGHTMAGENTA_EX}UPD{colorama.Fore.WHITE}]{colorama.Fore.LIGHTCYAN_EX} › {message}"
    log(prefix, **kwargs)