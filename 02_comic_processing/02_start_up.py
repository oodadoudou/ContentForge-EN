import os
import sys

# Add the project root to the Python search path to import shared utilities
# This assumes the script is in a subdirectory of the project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared_utils import utils

def menu_comic_processing():
    """Module 2: Independent Menu for Comic Processing and Generation"""
    module_path = '02_comic_processing'
    
    # Load global settings for use in future scripts
    settings = utils.load_settings()
    
    while True:
        utils.print_header("2. Comic Processing and Generation (Image to PDF)")
        print(" 1. [V5 Smart Fusion] Dual-Assurance Splitting Algorithm (★Highly Recommended★)")
        print(" 2. [V2 Fast-Track] Merge, Split, Repackage, and Generate PDF")
        print(" 3. [V4 Experimental] Process with the latest algorithm (Try if V2 splitting fails)")
        print(" 4. [Quick Convert] Convert image folder directly to PDF (No optimization)")
        print(" 5. [PDF Merge] Merge all PDFs in subfolders into a single file")
        print(" 6. [PDF to Image] Convert PDF to images (Supports long image splitting)")
        print("----------")
        print(" 8. View module usage instructions (README)")
        print(" 0. Back to Main Menu")
        choice = utils.get_input("Please select")

        if choice == '1':
            # Run V5 Smart Fusion version, dual-assurance splitting algorithm
            utils.run_script("image_processes_pipeline_v5.py", cwd=module_path)
        elif choice == '2':
            # Run the stable V2 version
            utils.run_script("image_processes_pipeline_v2.py", cwd=module_path)
        elif choice == '3':
            # Run the latest V4 version as a backup option
            utils.run_script("image_processes_pipeline_v4.py", cwd=module_path)
        elif choice == '4':
            utils.run_script("convert_img_to_pdf.py", cwd=module_path)
        elif choice == '5':
            # Run the PDF merge script
            utils.run_script("merge_pdfs.py", cwd=module_path)
        elif choice == '6':
            # Run the PDF to image script (supports long image splitting)
            utils.run_script("convert_long_pdf.py", cwd=module_path)
        elif choice == '8':
            utils.show_usage(module_path)
        elif choice == '0':
            # Return to the main menu (exit in a sub-script)
            break

if __name__ == "__main__":
    try:
        menu_comic_processing()
    except KeyboardInterrupt:
        # Gracefully exit when the user presses Ctrl+C in the sub-menu
        print("\n\nOperation interrupted by user.")
        sys.exit(0)