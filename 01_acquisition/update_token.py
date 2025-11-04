#!/usr/bin/env python3
import sys
import os
import json
import httpx

# --- Instructions ---
# 1. Please install the necessary libraries: pip install browser-cookie3 httpx
# 2. Before running this script, please make sure to completely close the Google Chrome browser.
# 3. The script will automatically create or update the bomtoontw-session file in the current directory.
# ---

# Script Settings
BOMTOON_DOMAIN = 'www.bomtoon.tw'
SESSION_COOKIE_NAME = '__Secure-next-auth.session-token'
SESSION_API_URL = f'https://{BOMTOON_DOMAIN}/api/auth/session'
SESSION_FILE_NAME = 'bomtoontw-session'

def find_session_token() -> str | None:
    """
    Automatically finds and decrypts Bomtoon's Session Token from the Chrome browser.
    """
    print(">> Step 1: Searching for Session Token from Chrome...")
    try:
        import browser_cookie3
    except ImportError:
        print("!! Error: Missing 'browser_cookie3' library. Please install it by running 'pip install browser_cookie3'.")
        return None
        
    try:
        cj = browser_cookie3.chrome(domain_name=BOMTOON_DOMAIN)
        
        for cookie in cj:
            if cookie.name == SESSION_COOKIE_NAME:
                print(f"    - Successfully found Session Token!")
                return cookie.value
                
        print("!! Error: The specified Session Token was not found in Chrome's cookies.")
        print("   Please make sure you are logged into Bomtoon.tw in Chrome.")
        return None

    except Exception as e:
        print(f"!! An error occurred while reading Chrome cookies: {e}")
        print("   Please ensure that:")
        print("   1. Google Chrome is completely closed (check in Windows Task Manager or macOS Dock).")
        print("   2. You have permission to read Chrome's user profile.")
        return None

def fetch_bearer_token_from_api(session_token: str) -> str | None:
    """
    Uses the Session Token to directly request the authentication API and extract the Bearer Token from the returned JSON.
    """
    print(">> Step 2: Directly requesting the authentication API to obtain the Bearer Token...")
    if not session_token:
        print("!! Error: Cannot proceed without a Session Token.")
        return None

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
        'Accept': 'application/json',
        'X-Requested-With': 'XMLHttpRequest',
    }
    cookies = {
        SESSION_COOKIE_NAME: session_token
    }

    try:
        with httpx.Client(cookies=cookies, headers=headers, follow_redirects=True, timeout=20.0) as client:
            print(f"    - Requesting API: {SESSION_API_URL}")
            response = client.get(SESSION_API_URL)
            response.raise_for_status()

        data = response.json()
        
        # *** Fixed ***
        # Corrected the JSON parsing path based on the provided response content
        try:
            bearer_token = data['user']['accessToken']['token']
        except (KeyError, TypeError):
            # Capture the error if the structure is incorrect or an intermediate key does not exist
            bearer_token = None

        if bearer_token:
            print(f"    - Successfully extracted Bearer Token from API!")
            return bearer_token
        else:
            print("!! Error: Could not find the path 'user' -> 'accessToken' -> 'token' in the data returned by the API.")
            print(f"   API response content: {data}")
            print("   The API structure may have changed, or your Session Token may have expired.")
            return None

    except httpx.HTTPStatusError as e:
        print(f"!! API request failed with HTTP status code: {e.response.status_code}")
        print(f"   URL: {e.request.url}")
        print("   Please check your internet connection and whether the Session Token is valid.")
        return None
    except json.JSONDecodeError:
        print("!! Error: The API response was not in a valid JSON format.")
        print(f"   Received content: {response.text}")
        return None
    except Exception as e:
        print(f"!! An unknown error occurred while requesting the API: {e}")
        return None


def main():
    """Main execution function"""
    print("============================================================")
    print("        Bomtoon.tw Credentials Auto-Update Script (token_update.py)")
    print("============================================================")
    
    session_token = find_session_token()
    if not session_token:
        sys.exit(1)

    bearer_token = fetch_bearer_token_from_api(session_token)
    if not bearer_token:
        sys.exit(1)
        
    print(f">> Step 3: Writing credentials to '{SESSION_FILE_NAME}'...")
    try:
        content = f"{session_token}\nBearer {bearer_token}\n"
        
        script_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(script_dir, SESSION_FILE_NAME)

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("\n🎉 All done!")
        print(f"Credentials have been successfully saved to: {file_path}")

    except IOError as e:
        print(f"!! An error occurred while writing the file: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()