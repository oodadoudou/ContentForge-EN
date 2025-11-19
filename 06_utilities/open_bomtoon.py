import webbrowser
import os

def open_urls_in_chrome(start_num, end_num):
    """
    Open web pages for the specified numeric range in Chrome.

    Parameters:
    start_num (int): Starting number
    end_num (int): Ending number
    """
    base_url = "https://www.bomtoon.tw/viewer/PAYBACK/"
    chrome_path = '' # 初始化 chrome_path

    # Attempt to locate Chrome path (for different operating systems)
    # Windows
    if os.name == 'nt':
        # Common Chrome installation paths
        possible_paths = [
            "C:/Program Files/Google/Chrome/Application/chrome.exe",
            "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
            os.path.expanduser("~\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe")
        ]
        for path in possible_paths:
            if os.path.exists(path):
                chrome_path = path
                break
    # macOS
    elif os.name == 'posix': # macOS also belongs to posix
        mac_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        if os.path.exists(mac_path):
            # For macOS, typically use 'open -a "Google Chrome" %s' or rely on registered browsers
            # The webbrowser module usually finds the default browser or registered Chrome
            # If you need to force Chrome, uncomment and ensure the path is correct
            # chrome_path = mac_path # not directly used with webbrowser.register
            pass # On macOS, webbrowser generally handles or finds by name
    # Linux
    elif 'linux' in os.name.lower():
        # Common Linux Chrome/Chromium paths
        possible_paths = [
            "/usr/bin/google-chrome-stable",
            "/usr/bin/google-chrome",
            "/usr/bin/chromium-browser",
            "/usr/bin/chromium"
        ]
        for path in possible_paths:
            if os.path.exists(path):
                chrome_path = path
                break

    try:
        # Register Chrome browser (if specific path was found)
        # On macOS, no explicit path registration is typically required; webbrowser.get('chrome') or webbrowser.get('google-chrome') may work
        # If chrome_path is not empty and not macOS app bundle path (macOS usually handles by name)
        if chrome_path and os.name != 'posix': # Use path on Windows/Linux
             webbrowser.register('chrome', None, webbrowser.BackgroundBrowser(chrome_path))
        elif os.name == 'posix': # macOS special handling
            # Try 'google-chrome' or 'chrome'; if not available, user may need to set default browser manually
            # Or use os.system(f'open -a "Google Chrome" "{url}")
            pass

        browser = None
        try:
            if os.name == 'posix' and os.path.exists("/Applications/Google Chrome.app"):
                 # On macOS, try using 'google-chrome' or 'chrome' name
                 # Or directly use the 'open' command (more reliable)
                browser_controller_name = 'google-chrome' # or 'chrome'
                try:
                    browser = webbrowser.get(browser_controller_name)
                except webbrowser.Error:
                    print(f"Unable to obtain Chrome browser controller by name '{browser_controller_name}'.")
                    print("Please ensure Chrome is installed or try alternative methods.")
                    # For macOS, using the 'open' command is generally more reliable
                    print("Will attempt to use 'open -a' command (macOS only).")

            elif chrome_path : # Windows/Linux
                browser = webbrowser.get('chrome')
            else: # If no specific path found, attempt default browser or registered Chrome
                print("Unable to automatically locate Chrome browser path. Trying system default or registered Chrome.")
                try:
                    browser = webbrowser.get('chrome') # Try getting registered 'chrome'
                except webbrowser.Error:
                    try:
                        browser = webbrowser.get('google-chrome') # Try 'google-chrome'
                    except webbrowser.Error:
                         print("Unable to obtain Chrome browser. Will use default browser.")
                         browser = webbrowser.get() # Get default browser

        except webbrowser.Error as e:
            print(f"Error occurred: {e}")
            print("Unable to obtain the specified browser. Please ensure Chrome is properly installed and added to the system path, or set it as your default browser.")
            print("Will attempt to use the default browser.")
            browser = webbrowser.get() # Get default browser instance

        if not browser and os.name == 'posix' and not os.path.exists("/Applications/Google Chrome.app"):
            print("Chrome app not found on macOS. Please install Chrome.")
            return
        elif not browser and not chrome_path and os.name != 'posix':
            print("Chrome browser path not found and cannot obtain by name. Please check installation.")
            return


        print(f"Preparing to open pages from {start_num} to {end_num}...")
        for i in range(start_num, end_num + 1):
            url_to_open = f"{base_url}{i}"
            print(f"Opening: {url_to_open}")
            if os.name == 'posix' and os.path.exists("/Applications/Google Chrome.app") and not (browser and hasattr(browser, 'open_new_tab')):
                # macOS fallback if webbrowser.get() fails or returns a non-ideal object
                os.system(f'open -a "Google Chrome" "{url_to_open}"')
            elif browser:
                browser.open_new_tab(url_to_open)
            else: # Final fallback if browser object is still None
                print(f"Cannot open with a specific browser object, trying webbrowser.open_new_tab (may use default browser): {url_to_open}")
                webbrowser.open_new_tab(url_to_open)


    except Exception as e:
        print(f"An error occurred during execution: {e}")
        print("Please check your Chrome installation path or try setting Chrome as the default browser.")

if __name__ == "__main__":
    while True:
        try:
            start_input = input("Enter the starting number (e.g., 27): ")
            start_page = int(start_input)
            break
        except ValueError:
            print("Invalid input, please enter an integer.")

    while True:
        try:
            end_input = input(f"Enter the ending number (e.g., 42, must be >= {start_page}): ")
            end_page = int(end_input)
            if end_page >= start_page:
                break
            else:
                print(f"The ending number must be greater than or equal to the starting number ({start_page}).")
        except ValueError:
            print("Invalid input, please enter an integer.")

    open_urls_in_chrome(start_page, end_page)
    print("All specified pages have been attempted to open.")