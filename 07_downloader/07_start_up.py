import os
import sys

# Add the project root to the Python search path to import shared tools
# This assumes the script is in a subdirectory of the project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared_utils import utils

def menu_downloader():
    """Module Seven: Downloader standalone menu"""
    module_path = '07_downloader'
    
    # Load global settings for potential future use
    settings = utils.load_settings()
    
    while True:
        utils.print_header("7. General Downloader Module")
        print(" 1. [Diritto] Novel Downloader")
        print("----------")
        print(" 8. View module usage (README)")
        print(" 0. Back to main menu")
        choice = utils.get_input("Please select")

        if choice == '1':
            # Run the Diritto novel downloader
            utils.run_script("diritto_downloader.py", cwd=module_path)
        elif choice == '8':
            # Show this module's README.md
            utils.show_usage(module_path)
        elif choice == '0':
            # Return to main menu
            break

if __name__ == "__main__":
    try:
        menu_downloader()
    except KeyboardInterrupt:
        # Gracefully exit when the user presses Ctrl+C in the submenu
        print("\n\nOperation interrupted by user.")
        sys.exit(0)