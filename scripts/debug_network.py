
import urllib.request
import socket
import os

supabase_url = os.environ.get("SUPABASE_URL", "https://rbdowedrdhtlbngapexj.supabase.co")

def check_url(url, name):
    print(f"Checking {name}: {url}")
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            print(f"  Success: {response.status}")
    except Exception as e:
        print(f"  Failed: {e}")

def check_dns(hostname):
    print(f"Resolving {hostname}...")
    try:
        ip = socket.gethostbyname(hostname)
        print(f"  Resolved to {ip}")
    except Exception as e:
        print(f"  Resolution Failed: {e}")

if __name__ == "__main__":
    print("--- Network Debug ---")
    check_dns("google.com")
    check_dns("rbdowedrdhtlbngapexj.supabase.co")
    
    check_url("https://www.google.com", "Google")
    check_url(supabase_url, "Supabase")
