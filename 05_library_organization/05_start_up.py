import os
import sys

# Add the project root to the Python search path to import shared tools
# This assumes the script is in a subdirectory of the project root
# Ensure shared_utils can be found
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

from shared_utils import utils

def menu_library_organization():
    """Module Five: Library Management standalone menu"""
    module_path = '05_library_organization'
    
    while True:
        utils.clear_screen()
        utils.print_header("5. Library Management (Organization & Tools)")
        print(" 1. [Smart Organize] Auto group, translate, and add pinyin prefix renaming")
        print(" 2. [Tools] Extract CSS files from EPUB in batch")
        print(" 3. [Tools] Folder encryption and decryption") # Newly added startup item
        print("----------")
        print(" 8. View module usage (README)")
        print(" 0. Back to main menu")
        
        # Use get_input from shared utilities
        choice = utils.get_input("Please select")

        if choice == '1':
            # The main program guides AI configuration before invoking this module
            utils.run_script("translate_and_org_dirs.py", cwd=module_path)
            input("\nPress Enter to return to menu...")
        
        elif choice == '2':
            # This script will prompt for the target directory
            utils.run_script("extract_epub_css.py", cwd=module_path)
            input("\nPress Enter to return to menu...")

        elif choice == '3': # Newly added logic
            # Call the new integrated folder encryption/decryption tool
            utils.run_script("folder_codec.py", cwd=module_path)
            # folder_codec.py handles exit internally; no input() needed here
            
        elif choice == '8':
            utils.show_usage(module_path)
            input("\nPress Enter to return to menu...")

        elif choice == '0':
            # Return to main menu (exit in sub-scripts)
            break

        else:
            input("Invalid input, press Enter to retry...")


if __name__ == "__main__":
    try:
        menu_library_organization()
    except KeyboardInterrupt:
        # Gracefully exit when the user presses Ctrl+C in the submenu
        print("\n\nOperation interrupted by user.")
        sys.exit(0)