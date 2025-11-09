import os
import sys

# Add project root to Python search path to import shared tools
# This assumes the script is in a subdirectory of the project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared_utils import utils

def menu_file_repair_and_utilities():
    """Module 4: Standalone menu for File Repair & Utilities."""
    module_path_repair = '04_file_repair'
    module_path_utils = '06_utilities'
    
    # Load global settings
    settings = utils.load_settings()
    
    while True:
        utils.print_header("4. File Repair & Utilities (Fix common issues)")
        print("--- EPUB Repair ---")
        print(" 1. Auto-fix vertical layout and convert to Simplified Chinese")
        print(" 2. Fix missing cover display on devices like Kindle")
        print(" 3. Repair missing CSS style links in EPUB")
        print("\n--- TXT Repair ---")
        print(" 4. TXT formatting (add paragraph spacing)")
        print(" 5. Fix TXT encoding issues (resolve garbled text)")
        print("\n--- Utilities ---")
        print(" 6. Batch open Bomtoon links in browser")
        print("----------")
        print(" 8. View module usage (README)")
        print(" 0. Return to main menu")
        choice = utils.get_input("Please choose")

        if choice == '1':
            utils.run_script("epub_reformat_and_convert_v2.py", cwd=module_path_repair)
        elif choice == '2':
            utils.run_script("cover_repair.py", cwd=module_path_repair)
        elif choice == '3':
            utils.run_script("css_fixer.py", cwd=module_path_repair)
        elif choice == '4':
            utils.run_script("txt_reformat.py", cwd=module_path_repair)
        elif choice == '5':
            utils.run_script("fix_txt_encoding.py", cwd=module_path_repair)
        elif choice == '6':
            utils.run_script("open_bomtoon.py", cwd=module_path_utils)
        elif choice == '8':
            utils.show_usage(module_path_repair)
        elif choice == '0':
            # Return to main menu (exit in sub-script)
            break

if __name__ == "__main__":
    try:
        menu_file_repair_and_utilities()
    except KeyboardInterrupt:
        # Graceful exit when user presses Ctrl+C in submenu
        print("\n\nOperation interrupted by user.")
        sys.exit(0)
