import os
import sys
import subprocess
import time

def check_dependencies():
    try:
        import autogen
        import playwright
        return True
    except ImportError as e:
        print(f"\n\033[91m[CRITICAL ERROR] Missing Dependency: {e.name}\033[0m")
        print("Please ensure requirements.txt is installed.")
        input("Press Enter to continue/exit...")
        sys.exit(1)

# Run check immediately
check_dependencies()

# ANSI Colors
GREEN = "\033[92m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"
BOLD = "\033[1m"

def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")

def print_banner():
    banner = f"""{GREEN}{BOLD}
    ____        __  __                  ___                      __ 
   / __ \__  __/ /_/ /_  ____  ____    /   |____ ____  ____  [t] / /_
  / /_/ / / / / __/ __ \/ __ \/ __ \  / /| / __ `/ _ \/ __ \/ / __/
 / ____/ /_/ / /_/ / / / /_/ / / / / / ___ / /_/ /  __/ / / / / /_  
/_/    \__, /\__/_/ /_/\____/_/ /_/ /_/  |_\__, /\___/_/ /_/_/\__/  
      /____/                              /____/                    
    {RESET}
    {CYAN}:: Local LLM Agent Launcher ::{RESET}       {YELLOW}v1.0{RESET}
    """
    print(banner)

def main():
    while True:
        clear_screen()
        print_banner()
        print(f"{GREEN}[AVAILABLE AGENTS]{RESET}")
        print(f" {GREEN}1.{RESET} AutoBot Basic       {YELLOW}(autobot.pyc){RESET}")
        print(f" {GREEN}2.{RESET} AutoBot Notepad     {YELLOW}(autobot2.pyc){RESET}")
        print(f" {GREEN}3.{RESET} AutoGen Bot (Robust){YELLOW}(bot_autogen.pyc){RESET}")
        print(f" {GREEN}4.{RESET} AutoHF (Phi-3)      {YELLOW}(auto_hf.pyc){RESET}")
        print(f" {GREEN}5.{RESET} SilverBullet Notes  {YELLOW}(bot_silverbullet.pyc){RESET}")
        print(f" {GREEN}6.{RESET} RAG Memory (ChromaDB){YELLOW}(bot_rag.pyc){RESET}")
        print(f" {GREEN}7.{RESET} Bot Super (Hybrid)  {YELLOW}(bot_super.pyc){RESET}")
        print(f" {GREEN}0.{RESET} Exit / Keluar")
        print("\n" + "-"*50)
        
        choice = input(f"{GREEN}{BOLD}root@agent:~#{RESET} ").strip()
        
        script_map = {
            "1": "autobot.pyc",
            "2": "autobot2.pyc",
            "3": "bot_autogen.pyc",
            "4": "auto_hf.pyc",
            "5": "bot_silverbullet.pyc",
            "6": "bot_rag.pyc",
            "7": "bot_super.pyc"
        }
        
        if choice == "0":
            print(f"\n{YELLOW}Shutting down agent...{RESET}")
            sys.exit(0)
            
        if choice in script_map:
            script_name = script_map[choice]
            if not os.path.exists(script_name):
                print(f"\n{RED}Error: File {script_name} not found!{RESET}")
                time.sleep(2)
                continue
                
            print(f"\n{CYAN}[+] Launching {script_name}...{RESET}\n")
            try:
                # Run the compiled python script
                subprocess.run([sys.executable, script_name], check=False)
            except KeyboardInterrupt:
                print(f"\n{RED}[!] Process interrupted{RESET}")
            except Exception as e:
                print(f"\n{RED}[!] Error: {e}{RESET}")
            
            print(f"\n{YELLOW}[Press ENTER to return to menu]{RESET}")
            input()
        else:
            print(f"\n{RED}Invalid command!{RESET}")
            time.sleep(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
