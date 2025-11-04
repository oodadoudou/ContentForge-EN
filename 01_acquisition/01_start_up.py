import os
import sys

# Add the project root to the Python search path to import shared utilities
# This assumes the script is in a subdirectory of the project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared_utils import utils

def menu_acquisition():
    """Module 1: Standalone Menu for Content Acquisition"""
    module_path = '01_acquisition'
    script_name = "bomtoontwext.py"
    
    # Load global settings to use the default download directory
    settings = utils.load_settings()
    
    while True:
        utils.print_header("1. Content Acquisition (Download comics from websites)")
        print("--- Preparations ---")
        print(" 1. Automatically update/generate login credentials (⭐Recommended to run this first)")
        print("\n--- Discover Comics (Get Comic ID) ---")
        print(" 2. List all purchased comics")
        print(" 3. Search for comics by keyword")
        print("\n--- Download Comics ---")
        print(" 4. (Manual) List chapters for a specific comic")
        print(" 5. Download specific chapters of a comic")
        print(" 6. Download all chapters of a comic")
        print(" 7. Download chapters by sequence range (e.g., 1-5, 8, 10)")
        print("----------")
        print(" 8. View usage instructions for this module (README)")
        print(" 0. Back to Main Menu")
        choice = utils.get_input("Please select")

        base_command = f'{script_name}'
        default_dir = settings.get('default_work_dir', ".")

        if choice == '1':
            utils.run_script("update_token.py", cwd=module_path)
        elif choice == '2':
            utils.run_script(f"{base_command} list-comic", cwd=module_path)
        elif choice == '3':
            keyword = utils.get_input("Please enter comic keyword")
            if keyword:
                utils.run_script(f'{base_command} search "{keyword}"', cwd=module_path)
        elif choice == '4':
            comic_id = utils.get_input("Please enter Comic ID")
            if comic_id:
                utils.run_script(f'{base_command} list-chapter "{comic_id}"', cwd=module_path)
        
        # --- Modified Download Flow ---
        elif choice in ['5', '6', '7']:
            # Step 1: Automatically list all purchased comics to help users find the ID
            utils.print_header("Step 1: List all purchased comics")
            utils.run_script(f"{base_command} list-comic", cwd=module_path)
            comic_id = utils.get_input("\n? Please copy and enter the [Comic ID] you want to operate on from the list above")
            if not comic_id:
                print("No Comic ID entered, operation cancelled.")
                input("Press Enter to continue...")
                continue
            
            # Step 2: Get the save directory
            output_dir = utils.get_input(f"\n? Please enter the download save directory", default=default_dir)
            if not os.path.isdir(output_dir):
                print(f"❌ Error: Directory '{output_dir}' is invalid.")
                input("Press Enter to continue...")
                continue

            # Step 3: Execute different operations based on the choice
            if choice == '5': # Download specific chapters
                # 3a: Automatically list all chapters for the comic
                utils.print_header(f"Step 2: List all chapters for comic '{comic_id}'")
                utils.run_script(f'{base_command} list-chapter "{comic_id}"', cwd=module_path)
                chapters = utils.get_input("\n? Please copy one or more [Chapter IDs] from the list above (separated by spaces)")
                if chapters:
                    utils.run_script(f'{base_command} dl -o "{output_dir}" "{comic_id}" {chapters}', cwd=module_path)

            elif choice == '6': # Download all chapters
                print("\nStarting to download all chapters of this comic...")
                utils.run_script(f'{base_command} dl-all -o "{output_dir}" "{comic_id}"', cwd=module_path)

            elif choice == '7': # Download by sequence
                # 3a: Automatically list all chapters and their sequence numbers for the comic
                utils.print_header(f"Step 2: List all chapters and their sequence numbers for comic '{comic_id}'")
                utils.run_script(f'{base_command} list-chapter "{comic_id}"', cwd=module_path)
                seq = utils.get_input("\n? Please enter the download range based on the sequence numbers above (e.g., 1-5 or 3,5,r1)")
                if seq:
                    utils.run_script(f'{base_command} dl-seq -o "{output_dir}" "{comic_id}" "{seq}"', cwd=module_path)
        
        elif choice == '8':
            utils.show_usage(module_path)
        elif choice == '0':
            break

if __name__ == "__main__":
    try:
        menu_acquisition()
    except KeyboardInterrupt:
        print("\n\nOperation interrupted by user.")
        sys.exit(0)