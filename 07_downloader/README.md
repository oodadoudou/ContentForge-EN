============================================================
           Module Seven: General Downloader (07_downloader)
============================================================

[Overview]
  This module provides specialized download tools for specific websites. Currently supports downloading novel content from Diritto.


[Core Scripts]
  - diritto_downloader.py


[Usage]
  All features of this module are integrated into the interactive menu in the project root's main.py.

  1. In the terminal, navigate to the ContentForge root directory and run `python main.py`.
  2. In the main menu select "7. General Downloader".
  3. Follow the submenu prompts to choose the feature you need.


--------------------- Features & Usage Details ---------------------

+ + + 1. [Diritto] Novel Downloader + + +

  - **Script**: `diritto_downloader.py`
  - **Purpose**: Automatically scrape all chapter content from the specified Diritto novel page, save each chapter as an individual TXT file, and finally package all chapters into a ZIP archive stored in your default working directory.
  - **Use Cases**: Use when you need to back up or read Diritto novels offline.

  - **Important Preparation**:
    This tool needs to connect to your logged-in Chrome browser via "remote debugging" mode. Before running the script, be sure to follow the steps below:

    1.  **Completely close all Chrome windows**.
        (Check the taskbar or Dock to ensure Chrome has fully exited.)

    2.  **Launch Chrome via the command line**.
        Open your system terminal (Windows CMD/PowerShell or macOS Terminal).

        - **For Windows users**:
          Enter the following command in the terminal and press Enter:
          ```bash
          "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222
          ```
          *(If your Chrome is installed in another path, modify accordingly.)*

        - **For macOS users**:
          Enter the following command in the terminal and press Enter:
          ```bash
          /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222
          ```

    3.  **Keep the terminal and the newly opened Chrome window open**.
        Once successful, you will see a separate Chrome window open. You can now log in to the Diritto website normally.

  - **Operation**:
    1.  Complete the preparation above and keep Chrome running.
    2.  Return to ContentForge, enter this module from the main menu and select the download feature.
    3.  Paste the URL of the novel directory page you want to download as prompted.
    4.  The program will automatically begin scraping, and you can see real-time progress in the terminal.
