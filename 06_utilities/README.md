============================================================
              Module Six: Utilities (06_utilities)
============================================================

[Overview]
  This module provides auxiliary tools used in specific scenarios, outside of core workflows.


[Core Scripts]
  - open_bomtoon.py


[Usage]
  All features of this module are integrated into the interactive menu in the project root's main.py.

  1. In a terminal, navigate to the ContentForge root directory and run `python main.py`.
  2. In the main menu select "6. Utilities".
  3. Follow the submenu prompts to choose the feature you need.


--------------------- Features & Usage Details ---------------------

+ + + 1. Batch Open Web Pages + + +

  - Script: open_bomtoon.py
  - Purpose: Batch open a series of sequentially numbered URLs for a specific comic in your default browser.
  - Use Cases: Use when you need to quickly open pages consecutively for browsing or manual checks.
  - Operation: After running this feature, the script will guide you through interactive prompts:
      1. Enter the starting number (e.g., 27)
      2. Enter the ending number (e.g., 42)
    The program will automatically open all corresponding pages from start to end.