import os
import sys
import time
import yaml
from pystyle import Colors, Colorate, Center
import logging

logging.getLogger("discord.gateway").setLevel(logging.ERROR)

def clear_console():
    os.system('cls' if os.name == 'nt' else 'clear')

banner = """
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣸⣧⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠘⣿⣦⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⣴⣾⣿⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢻⣿⣿⣶⣤⣀⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣀⡀⣴⣿⣿⣿⣿⡿⠁⠀⠀⢰⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠻⣿⣿⣿⣿⣿⣦⣤⣀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⣾⣿⣷⣿⣿⣿⣿⣿⠁⠀⠀⠀⢨⣇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣰⠀⠀⠀⠀⠉⢿⣿⣿⣿⣿⣾⣿⣿⣷⣦⣄⡀⠀⠀⠀⠀⠀⠀⠀⢀⣴⣾⣿⣿⣿⣿⣿⣿⣿⣿⣇⠀⠀⠀⢀⣼⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢿⡄⠀⠀⠀⠀⠋⠉⠉⠙⠛⠿⠟⠻⠿⠿⠿⠿⠷⣤⣀⠀⠀⢀⠴⠟⠛⠛⠛⠋⠉⠁⠉⠁⠀⠀⠀⠀⠀⠀⣼⣿⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠘⣿⣶⣄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡀⢰⣄⣿⣿⣿⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠹⣿⣿⣧⣀⣀⢀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢰⣶⣿⣿⣸⣿⣿⣿⡷⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠉⣿⣿⣿⣿⢸⣿⣦⣦⣄⡀⠀⢠⣶⢰⣦⣶⣰⣆⣶⣰⣦⣄⢰⣴⡄⣴⠀⠀⣦⣷⣿⣿⣿⣿⣯⣿⣿⣿⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠸⢿⣿⣿⣿⣿⣿⣿⣿⣷⠀⣼⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣾⣿⣿⣿⡇⢸⣿⣿⣿⣿⣿⣿⣿⣿⡟⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠋⣿⣿⣿⣿⣿⣿⣿⡇⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⢸⣿⣿⣿⣿⣿⡿⣿⠿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠉⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣸⣿⣿⣿⣿⡿⠇⠇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⢿⢹⠘⣿⣿⣿⣿⣿⣿⣿⡟⣿⣿⣿⣿⣿⣿⡟⢹⣿⣿⣿⣿⣿⣿⠹⠛⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠀⠀⠈⠟⠏⢿⢿⢿⢧⠘⣿⢿⣿⡟⠿⡇⠸⣿⠿⢻⡟⠛⠈⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠀⠀⠘⠀⠀⠈⠈⠁⠀⠃⠀⠀⠀⠀⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀

                 ╒══════════════════════════════════════════╕
                 │      Boost tool made by .gg/coderz       │
                 ╘══════════════════════════════════════════╛
"""

def load_config():
    try:
        with open('config/config.yaml') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        return {}

def main():
    clear_console()
    print(Center.XCenter(Colorate.Vertical(color=Colors.red_to_black, text=banner), spaces=15))
    
    try:
        from coderz import getinviteCode, checkInvite, getStock, Booster, remove
    except ImportError as e:
        print(f" [!] Error loading bot logic: {e}")
        input(" Press Enter to exit...")
        sys.exit(1)
        
    print("\n" + Colorate.Horizontal(Colors.red_to_black, "   [ BoostBot Tool - Token Booster ]") + "\n")
    print(Colorate.Horizontal(Colors.red_to_black, " [1] Boost a Server"))
    print(Colorate.Horizontal(Colors.red_to_black, " [2] Online all Tokens"))
    print(Colorate.Horizontal(Colors.red_to_black, " [3] Humanize Tokens"))
    
    try:
        choice = input(Colorate.Horizontal(Colors.red_to_black, "\n [?] Choose an option (1/2/3): ")).strip()
        
        if choice == "3":
            print(Colorate.Horizontal(Colors.red_to_black, " [*] Preparing tokens for humanizer..."))
            tokens_1m = getStock("data/1m.txt") or []
            tokens_3m = getStock("data/3m.txt") or []
            all_tokens = tokens_1m + tokens_3m
            
            if not all_tokens:
                print(Colorate.Horizontal(Colors.red_to_black, " [!] No tokens found to humanize!"))
                return
            
            try:
                # Write tokens to humanizer input
                os.makedirs("humanizer/input", exist_ok=True)
                with open("humanizer/input/tokens.txt", "w", encoding="utf-8") as f:
                    for t in all_tokens:
                        f.write(t + "\n")
                
                print(Colorate.Horizontal(Colors.red_to_black, f" [+] Sent {len(all_tokens)} tokens to humanizer. Launching..."))
                import subprocess
                subprocess.run([sys.executable, "main.py"], cwd="humanizer")
                print(Colorate.Horizontal(Colors.red_to_black, " [+] Humanizer finished execution."))
            except Exception as e:
                print(Colorate.Horizontal(Colors.red_to_black, f" [!] Failed to run humanizer: {e}"))
            return

        elif choice == "2":
            print(Colorate.Horizontal(Colors.red_to_black, " [*] Checking for tokens..."))
            tokens_1m = getStock("data/1m.txt")
            tokens_3m = getStock("data/3m.txt")
            if tokens_1m is None: tokens_1m = []
            if tokens_3m is None: tokens_3m = []
            
            all_tokens = tokens_1m + tokens_3m
            if not all_tokens:
                print(Colorate.Horizontal(Colors.red_to_black, " [!] No tokens to put online!"))
                return
                
            print(Colorate.Horizontal(Colors.red_to_black, f" [*] Putting {len(all_tokens)} tokens online..."))
            try:
                from coderz import AvatarSocket
                onliner = AvatarSocket()
                for token in all_tokens:
                    onliner.run_socket(token)
                    time.sleep(0.1)
                print("\n" + Colorate.Horizontal(Colors.red_to_black, f" [+] Successfully started onliner for {len(all_tokens)} tokens!"))
                print(Colorate.Horizontal(Colors.red_to_black, " [!] WARNING: DO NOT CLOSE THIS WINDOW. If you close it, the tokens will go offline!"))
                print(Colorate.Horizontal(Colors.red_to_black, " [i] Press CTRL+C to stop the onliner and return to the menu.\n"))
                
                start_time = time.time()
                while True:
                    elapsed = int(time.time() - start_time)
                    m, s = divmod(elapsed, 60)
                    h, m = divmod(m, 60)
                    t_str = f"{h}h {m}m {s}s" if h > 0 else f"{m}m {s}s"
                    status = f" [*] Keeping {len(all_tokens)} Tokens ONLINE | Uptime: {t_str} | (DO NOT CLOSE)".ljust(80)
                    sys.stdout.write("\r" + Colorate.Horizontal(Colors.red_to_black, status))
                    sys.stdout.flush()
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n\n" + Colorate.Horizontal(Colors.red_to_black, " [!] Onliner stopped by user."))
                return
            except Exception as e:
                print("\n" + Colorate.Horizontal(Colors.red_to_black, f" [!] Failed to start onliner: {e}"))
            return

        elif choice == "1":
            invite_str = input(Colorate.Horizontal(Colors.red_to_black, "\n [?] Enter Server Invite (e.g. discord.gg/invite): ")).strip()
            if not invite_str:
                print(Colorate.Horizontal(Colors.red_to_black, " [!] Invite cannot be empty."))
                return

            amount_str = input(Colorate.Horizontal(Colors.red_to_black, " [?] Enter Amount of Boosts (must be even, e.g. 2, 4, 14): ")).strip()
            months_str = input(Colorate.Horizontal(Colors.red_to_black, " [?] Enter Months (1 or 3): ")).strip()

            amount = int(amount_str)
            months = int(months_str)

            if amount <= 0 or amount % 2 != 0:
                print(Colorate.Horizontal(Colors.red_to_black, " [!] Amount must be a positive even number (2 boosts per token)."))
                return
                
            if months not in [1, 3]:
                print(Colorate.Horizontal(Colors.red_to_black, " [!] Months must be 1 or 3."))
                return
        else:
            print(Colorate.Horizontal(Colors.red_to_black, " [!] Invalid option."))
            return

    except ValueError:
        print(" [!] Invalid numerical input. Please enter numbers for amounts/months.")
        return

    print("\n [*] Verifying invite...")
    inviteCode = getinviteCode(invite_str)
    inviteData = checkInvite(inviteCode)

    if not inviteData:
        print(" [!] Invalid invite link or server is not accessible.")
        return

    filename = "data/1m.txt" if months == 1 else "data/3m.txt"
    tokensStock = getStock(filename)
    
    if tokensStock is None:
        tokensStock = []
        
    requiredStock = int(amount / 2)
    
    if requiredStock > len(tokensStock):
        print(f" [!] Not enough stock! Need {requiredStock} tokens ({amount} boosts), but only have {len(tokensStock)} tokens ({len(tokensStock)*2} boosts) in {filename}.")
        return

    print(f" [*] Processing {amount} boosts for {months} Months...")
    
    boost = Booster()
    tokens = []

    for x in range(requiredStock):
        tokens.append(tokensStock[x])
        remove(tokensStock[x], filename)

    start = time.time()
    print(" [*] Joining and Boosting... Please wait.")
    
    status = boost.thread(inviteCode, tokens, inviteData)
    time_taken = round(time.time() - start, 2)

    success_count = 0
    failed_count = 0
    if isinstance(status, dict):
        success_count = len(status.get('success', []))
        failed_count = len(status.get('failed', []))
    
    print("\n" + "="*50)
    print(f" [+] Boosting Complete in {time_taken}s!")
    print(f" [+] Success: {success_count * 2} boosts applied")
    print(f" [-] Failed: {failed_count * 2} boosts failed")
    print("="*50 + "\n")

if __name__ == "__main__":
    while True:
        main()
        input("\n Press Enter to boost another server, or close the window to exit...")
