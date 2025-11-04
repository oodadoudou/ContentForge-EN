============================================================
           Module 1: Content Acquisition (01_acquisition)
============================================================

[Introduction]
  The core function of this module is to download comics you have purchased from the Bomtoon.tw platform.
  All operations require valid user credentials.


[Core Scripts]
  - bomtoontwext.py
  - update_token.py (Tool for automatically updating credentials)


[Preparation]
  You have two ways to configure the login credentials required to run this module:

  --- Method 1: Automatic Update (Recommended) ---
    1. Enter this module from the main menu in main.py.
    2. Select "1. [Auto-Update] Update/Generate Login Credentials".
    3. Follow the prompts to [completely close] all Chrome browser windows.
    4. Press Enter, and the script will automatically fetch the latest credentials and generate
       the `bomtoontw-session` file.

  --- Method 2: Manual Configuration ---
    If the automatic update fails, you can manually create the `bomtoontw-session` file.
    Please create this file in the 01_acquisition folder and follow the steps below
    to enter the two key pieces of information.

    [How to get the credentials?]
      1. Log in to the website:
         Log in to your Bomtoon.tw account normally in the Google Chrome browser.

      2. Open Developer Tools:
         Press the F12 key (or Ctrl+Shift+I / Cmd+Opt+I).

      3. Get the Session Token:
         - Go to "Application" -> "Cookies" -> "https://www.bomtoon.tw".
         - Find the item named "__Secure-next-auth.session-token".
         - Copy its corresponding "Cookie Value". [This is the first line of content needed]

      4. Get the Bearer Token:
         - Switch to the "Network" tab and refresh the page.
         - In the request list, find any request made to "api/".
         - Click on that request, and in the "Request Headers" on the right,
           find "authorization" and copy its [complete] value (usually starting with
           "Bearer ..."). [This is the second line of content needed]

    [Fill in the file]
      Paste the two lines of credentials you copied into the bomtoontw-session file in order and save it.


[Usage]
  All functions of this module have been integrated into the interactive menu of main.py in the project root directory.

  1. In the terminal, navigate to the ContentForge root directory and run `python main.py`.
  2. In the main menu, enter "1" and press Enter to go to the "Content Acquisition" submenu.
  3. Follow the prompts in the submenu to perform operations:
     - List all purchased comics: Used to get the "Comic ID" of all comics under your account.
     - Search for comics: Search for comics by keyword to get the "Comic ID".
     - List chapters of a specific comic: Enter the "Comic ID" to get the "Chapter ID" of all chapters.
     - Download specific chapters: Enter the "Comic ID" and one or more "Chapter IDs" to download.
     - Download all chapters of a comic: Enter the "Comic ID" to download the entire comic.
     - Download chapters by sequence: Use formats like "1-5" (range) or "3,5,r1" (specific and reverse) to download.
     - Usage instructions: Displays the content of this file.