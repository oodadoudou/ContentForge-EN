import os
import fitz  # PyMuPDF
from PIL import Image
import math
import sys
import json
import shutil
import traceback

# --- Configurable Parameters ---

# Image rendering DPI (resolution). Higher means better quality and larger files.
DPI = 300

# Maximum page height (pixels). Pages exceeding this height will be split.
MAX_PAGE_HEIGHT = 16384

# Output image format ('png' or 'jpg')
IMAGE_FORMAT = 'png'

# Added: Folder name to store processed PDF source files
PROCESSED_PDF_FOLDER_NAME = "converted_pdfs"

# --- Main Script Logic ---

def convert_pdf_with_splitting_in_subdirs(root_dir: str):
    """
    Scans all subdirectories under the root directory and converts their PDF files to images.
    If a page is too long, it will be split into multiple parts.
    Output images for each PDF are saved in a child subdirectory named after the PDF.
    Successfully processed PDF source files are moved to a '<subdir>_processed_pdfs' folder within each subdirectory.

    Args:
        root_dir (str): Root directory containing multiple subdirectories, each with PDF files.
    """
    print("-" * 50)
    print(f"[*] Starting processing...")
    print(f"[*] Root directory: {root_dir}")
    print(f"[*] Maximum page height: {MAX_PAGE_HEIGHT}px")
    print("-" * 50)

    if not os.path.isdir(root_dir):
        print(f"[Error] Root directory '{root_dir}' does not exist. Please check the path.")
        return

    # Retrieve all subdirectories
    try:
        subdirs = [d for d in os.listdir(root_dir) 
                  if os.path.isdir(os.path.join(root_dir, d)) and not d.startswith('.')]
        if not subdirs:
            print(f"[Warning] No subdirectories found in root directory '{root_dir}'.")
            return
    except Exception as e:
        print(f"[Error] Could not read root directory '{root_dir}': {e}")
        return

    print(f"[*] Found {len(subdirs)} subdirectories; starting processing.")

    total_successful_conversions = 0
    total_failed_conversions = 0

    # Iterate through each subdirectory
    for subdir in sorted(subdirs):
        subdir_path = os.path.join(root_dir, subdir)
        print(f"\n{'='*60}")
        print(f"[*] Processing subdirectory: {subdir}")
        print(f"[*] Subdirectory path: {subdir_path}")
        print(f"{'='*60}")
        
        # Create a folder to store processed PDFs (named using the subdirectory)
        processed_pdfs_dir = os.path.join(subdir_path, f"{subdir}_processed_pdfs")
        os.makedirs(processed_pdfs_dir, exist_ok=True)
        print(f"[*] Processed PDFs will be moved to: {processed_pdfs_dir}")
        
        # Get PDF files in the current subdirectory
        try:
            pdf_files = [f for f in os.listdir(subdir_path) 
                        if f.lower().endswith('.pdf') and not f.startswith('.')]
            if not pdf_files:
                print(f"[Warning] No PDF files found in subdirectory '{subdir}'.")
                continue
        except Exception as e:
            print(f"[Error] Could not read subdirectory '{subdir_path}': {e}")
            continue
        
        print(f"[*] Found {len(pdf_files)} PDF file(s) in subdirectory '{subdir}'.")
        
        successful_conversions = 0
        failed_conversions = 0

        for pdf_file in sorted(pdf_files):
            pdf_path = os.path.join(subdir_path, pdf_file)
            
            if not os.path.exists(pdf_path):
                print(f"\n--- Skipping file: {pdf_file} ---")
                print(f"  [Warning] File path invalid or unreadable: {pdf_path}")
                failed_conversions += 1
                continue

            pdf_base_name = os.path.splitext(pdf_file)[0]
            current_output_subdir = os.path.join(subdir_path, pdf_base_name)
            
            try:
                os.makedirs(current_output_subdir, exist_ok=True)
                print(f"\n--- Processing file: {pdf_file} ---")
                print(f"    Output to: {current_output_subdir}")
            except Exception as e:
                print(f"[Error] Failed to create output subdirectory '{current_output_subdir}': {e}")
                failed_conversions += 1
                continue 
            
            try:
                doc = fitz.open(pdf_path)
                for i, page in enumerate(doc):
                    page_num = i + 1
                    pix = page.get_pixmap(dpi=DPI)
                    
                    if pix.height <= MAX_PAGE_HEIGHT:
                        image_filename = f"{pdf_base_name}_page_{page_num:03d}.{IMAGE_FORMAT}"
                        output_path = os.path.join(current_output_subdir, image_filename)
                        pix.save(output_path)
                        print(f"  - Saved page: {page_num} -> {image_filename}")
                    else:
                        print(f"  - Page {page_num} height is {pix.height}px, exceeds max {MAX_PAGE_HEIGHT}px; splitting...")
                        img_pil = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                        num_splits = math.ceil(img_pil.height / MAX_PAGE_HEIGHT)
                        
                        for part_num in range(num_splits):
                            top = part_num * MAX_PAGE_HEIGHT
                            bottom = min((part_num + 1) * MAX_PAGE_HEIGHT, img_pil.height)
                            box = (0, top, img_pil.width, bottom)
                            cropped_img = img_pil.crop(box)
                            image_filename = f"{pdf_base_name}_page_{page_num:03d}_part_{part_num+1:02d}.{IMAGE_FORMAT}"
                            output_path = os.path.join(current_output_subdir, image_filename)
                            cropped_img.save(output_path)
                            print(f"    - Saved split: {part_num+1}/{num_splits} -> {image_filename}")
                doc.close()
                print(f"--- Finished file: {pdf_file} ---")
                successful_conversions += 1

                # Move successfully processed PDF to the subdirectory-specific processed folder
                try:
                    destination_path = os.path.join(processed_pdfs_dir, pdf_file)
                    shutil.move(pdf_path, destination_path)
                    print(f"    -> Moved source file '{pdf_file}' to '{subdir}_processed_pdfs' folder.")
                except Exception as move_error:
                    print(f"    [Warning] Moving file '{pdf_file}' failed: {move_error}")

            except Exception as e:
                print(f"[Error] Critical error while processing file '{pdf_file}': {type(e).__name__} - {e}")
                failed_conversions += 1
                continue

        
        # Subdirectory processing summary
        print(f"\n--- Subdirectory '{subdir}' processing complete ---")
        print(f"    Successfully processed: {successful_conversions} PDF file(s).")
        print(f"    Skipped/Failed: {failed_conversions} PDF file(s).")
        print(f"    Output images are saved in a sub-subdirectory named after each PDF.")
        print(f"    Processed PDF source files have been moved to '{subdir}_processed_pdfs'.")
        
        total_successful_conversions += successful_conversions
        total_failed_conversions += failed_conversions
    
    # Overall processing summary
    print("\n" + "=" * 70)
    print(f"[*] All subdirectories processed.")
    print(f"    Total successfully processed: {total_successful_conversions} PDF file(s).")
    print(f"    Total skipped/failed: {total_failed_conversions} PDF file(s).")
    print(f"[*] All output images are saved in sub-subdirectories named after their PDFs.")
    print(f"[*] All processed PDF source files have been moved to each subdirectory's '<subdir>_processed_pdfs' folder.")
    print("=" * 70)

# ▼▼▼ Main function standardized as requested ▼▼▼
if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("=== PDF to Images Tool (Batch subdirectory processing; supports long-page splitting and source file archiving) ===")
    print("=" * 70)

    # --- Standardized helper: Read default work directory from shared settings ---
    def load_default_path_from_settings():
        """Read the default work directory from the shared settings file."""
        try:
            # Assume this script is in a project subdirectory; go up two levels to the project root
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            settings_path = os.path.join(project_root, 'shared_assets', 'settings.json')
            with open(settings_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)
            # Treat empty or None default_work_dir as invalid
            default_dir = settings.get("default_work_dir")
            return default_dir if default_dir else "."
        except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
            print(f"Warning: Failed to read settings.json ({e}); using built-in fallback path.")
            # Provide a generic fallback path (user's Downloads folder)
            return os.path.join(os.path.expanduser("~"), "Downloads")
    # --- End standardized helper ---

    default_input_dir_name = load_default_path_from_settings()
    input_dir = "" # Initialize variable

    # --- Standardized path handling logic ---
    while True:
        prompt_message = (
            f"\n- Please enter the root directory path that contains multiple subdirectories (each with PDFs to convert).\n"
            f"  (Press Enter to use the default path: '{default_input_dir_name}'): "
        )
        user_input = input(prompt_message).strip()

        # Use default path if the user enters nothing; otherwise use the provided path
        path_to_check = user_input if user_input else default_input_dir_name
        
        abs_path_to_check = os.path.abspath(path_to_check)

        if os.path.isdir(abs_path_to_check):
            input_dir = abs_path_to_check
            print(f"\n[*] Processing directory: {input_dir}")
            break
        else:
            print(f"Error: Path '{abs_path_to_check}' is not a valid directory or does not exist.")
    # --------------------------

    try:
        convert_pdf_with_splitting_in_subdirs(root_dir=input_dir)
    except KeyboardInterrupt:
        print("\n\n[Info] Operation interrupted by user; program exited.")
        sys.exit(0)
    except Exception as e:
        print("\n" + "!"*70)
        print("The script encountered an unexpected critical error and has been terminated.")
        print(f"Error details: {e}")
        traceback.print_exc()
        print("!"*70)

    print("\nScript execution finished.")