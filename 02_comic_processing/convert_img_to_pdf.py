# -*- coding: utf-8 -*-

import os
import shutil
import sys
import re
from PIL import Image, ImageFile
import natsort
import traceback

# --- Global Settings ---
ImageFile.LOAD_TRUNCATED_IMAGES = True
Image.MAX_IMAGE_PIXELS = None

SUCCESS_MOVE_SUBDIR_NAME = "IMG"  # Successfully processed folders will be moved to this directory
IMAGE_EXTENSIONS_FOR_MERGE = ('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif', '.tiff', '.tif')

# --- PDF Page and Image Quality Settings ---
PDF_TARGET_PAGE_WIDTH_PIXELS = 1600
PDF_DPI = 300
# --- End of Global Settings ---


def print_progress_bar(iteration, total, prefix='', suffix='', decimals=1, length=50, fill='█', print_end="\r"):
    """
    Prints a visual progress bar in the terminal.
    """
    if total == 0:
        percent_str = "0.0%"
        filled_length = 0
    else:
        percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
        percent_str = f"{percent}%"
        filled_length = int(length * iteration // total)

    bar = fill * filled_length + '-' * (length - filled_length)
    sys.stdout.write(f'\r{prefix} |{bar}| {percent_str} {suffix}')
    sys.stdout.flush()
    if iteration == total:
        sys.stdout.write('\n')
        sys.stdout.flush()


def find_image_folders(root_dir, excluded_dirs):
    """
    Recursively traverses the root directory to find all folders that directly contain image files.
    """
    print("\n--- Step 1: Scanning and finding all folders containing images ---")
    image_folders = []
    
    # Extract the names (not full paths) of excluded directories for comparison
    excluded_basenames = [os.path.basename(d) for d in excluded_dirs]

    for dirpath, dirnames, filenames in os.walk(root_dir):
        # If the current directory is in the exclusion list, skip it and its subdirectories
        if os.path.basename(dirpath) in excluded_basenames:
            dirnames[:] = []  # Clearing dirnames prevents os.walk from descending further
            continue

        if any(f.lower().endswith(IMAGE_EXTENSIONS_FOR_MERGE) for f in filenames):
            image_folders.append(dirpath)
    
    sorted_folders = natsort.natsorted(image_folders)
    print(f"    🔍 Found {len(sorted_folders)} image folders to process.")
    return sorted_folders


def create_pdf_from_images(image_paths_list, output_pdf_path,
                           target_page_width_px, pdf_target_dpi):
    """
    Creates a PDF file from a list of image file paths.
    """
    if not image_paths_list:
        print("    Warning: No valid images available to create this PDF.")
        return None

    processed_pil_images = []
    total_images_for_pdf = len(image_paths_list)
    print_progress_bar(0, total_images_for_pdf, prefix='      Converting images:', suffix='Done', length=40)

    for i, image_path in enumerate(image_paths_list):
        try:
            with Image.open(image_path) as img:
                img_to_process = img
                if img_to_process.mode in ['RGBA', 'P']:
                    background = Image.new("RGB", img_to_process.size, (255, 255, 255))
                    background.paste(img_to_process, mask=img_to_process.split()[3] if img_to_process.mode == 'RGBA' else None)
                    img_to_process = background
                elif img_to_process.mode != 'RGB':
                    img_to_process = img_to_process.convert('RGB')

                original_width, original_height = img_to_process.size
                if original_width > target_page_width_px:
                    ratio = target_page_width_px / original_width
                    new_height = int(original_height * ratio)
                    img_resized = img_to_process.resize((target_page_width_px, new_height), Image.Resampling.LANCZOS)
                else:
                    img_resized = img_to_process.copy()

                processed_pil_images.append(img_resized)
        except Exception as e:
            sys.stdout.write(f"\r      Warning: Failed to process image '{os.path.basename(image_path)}': {e}. Skipped.\n")
        finally:
            print_progress_bar(i + 1, total_images_for_pdf, prefix='      Converting images:', suffix='Done', length=40)

    if not processed_pil_images:
        print("    Error: No images were successfully processed; cannot create PDF.")
        return None

    try:
        if len(processed_pil_images) == 1:
            processed_pil_images[0].save(
                output_pdf_path,
                resolution=float(pdf_target_dpi),
                optimize=True
            )
        else:
            first_image = processed_pil_images[0]
            other_images = processed_pil_images[1:]
            first_image.save(
                output_pdf_path,
                save_all=True,
                append_images=other_images,
                resolution=float(pdf_target_dpi),
                optimize=True
            )
        
        print(f"    ✅ Successfully created PDF: {os.path.basename(output_pdf_path)}")
        return output_pdf_path
    except Exception as e:
        print(f"    ❌ Error: Failed to save PDF '{os.path.basename(output_pdf_path)}': {e}")
        traceback.print_exc()
        return None
    finally:
        for img_obj in processed_pil_images:
            try:
                img_obj.close()
            except Exception:
                pass


def normalize_filenames(pdf_dir):
    """
    Cleans and normalizes the names of all files in the PDF directory.
    """
    print("\n--- Step 3: Normalizing PDF filenames ---")
    try:
        pdf_files = [f for f in os.listdir(pdf_dir) if f.lower().endswith('.pdf')]
    except FileNotFoundError:
        print(f"    Directory '{pdf_dir}' not found, skipping filename normalization.")
        return

    renamed_count = 0
    for filename in pdf_files:
        base, ext = os.path.splitext(filename)
        # Remove common separators and brackets
        cleaned_base = re.sub(r'[\s()\[\]【】。.]', '', base)
        
        normalized_name = cleaned_base + ext
        
        if normalized_name != filename:
            original_path = os.path.join(pdf_dir, filename)
            new_path = os.path.join(pdf_dir, normalized_name)
            try:
                os.rename(original_path, new_path)
                print(f"    Renamed: '{filename}' -> '{normalized_name}'")
                renamed_count += 1
            except OSError as e:
                print(f"    ❌ Error: Failed to rename '{filename}': {e}")
                
    if renamed_count > 0:
        print(f"    ✨ Normalized {renamed_count} filenames.")
    else:
        print("    All filenames are already compliant, no changes needed.")


def run_conversion_process(root_dir):
    """
    Executes the complete workflow from finding folders to generating PDFs, moving, and renaming.
    """
    # Create a unique PDF output folder based on the root directory name
    root_dir_basename = os.path.basename(os.path.abspath(root_dir))
    overall_pdf_output_dir = os.path.join(root_dir, f"{root_dir_basename}_pdfs")
    os.makedirs(overall_pdf_output_dir, exist_ok=True)
    
    # Create a folder to store successfully processed projects
    success_move_target_dir = os.path.join(root_dir, SUCCESS_MOVE_SUBDIR_NAME)
    os.makedirs(success_move_target_dir, exist_ok=True)

    # Find folders to process, excluding management directories
    folders_to_process = find_image_folders(root_dir, [overall_pdf_output_dir, success_move_target_dir])

    if not folders_to_process:
        print("\nNo folders containing images were found in the specified directory and its subdirectories. Script finished.")
        return

    print("\n--- Step 2: Starting batch conversion of image folders to PDF ---")
    
    total_folders = len(folders_to_process)
    failed_tasks = []
    success_count = 0

    for i, image_dir_path in enumerate(folders_to_process):
        folder_name = os.path.basename(image_dir_path)
        print(f"\n--- ({i+1}/{total_folders}) Processing: {folder_name} ---")

        try:
            image_filenames = [f for f in os.listdir(image_dir_path)
                               if f.lower().endswith(IMAGE_EXTENSIONS_FOR_MERGE) and not f.startswith('.')]
        except Exception as e:
            print(f"  ❌ Error: Could not read contents of folder '{folder_name}': {e}")
            failed_tasks.append(folder_name)
            continue
            
        if not image_filenames:
            print("    No qualifying images found in the folder, skipped.")
            continue

        sorted_image_paths = [os.path.join(image_dir_path, f) for f in natsort.natsorted(image_filenames)]
        output_pdf_filename = f"{folder_name}.pdf"
        output_pdf_filepath = os.path.join(overall_pdf_output_dir, output_pdf_filename)

        result_path = create_pdf_from_images(
            sorted_image_paths, output_pdf_filepath,
            PDF_TARGET_PAGE_WIDTH_PIXELS, PDF_DPI
        )
        
        if result_path:
            success_count += 1
            # Move the successfully processed folder
            print(f"    Moving successfully processed folder: {folder_name}")
            try:
                # Ensure the target folder exists
                if os.path.basename(image_dir_path) == os.path.basename(success_move_target_dir):
                    print(f"      -> Skipped moving, source and target folders have the same name.")
                else:
                    shutil.move(image_dir_path, success_move_target_dir)
                    print(f"      -> Moved to '{SUCCESS_MOVE_SUBDIR_NAME}' folder.")
            except Exception as e:
                print(f"      ❌ Error: Failed to move folder: {e}")
                if folder_name not in failed_tasks:
                    failed_tasks.append(f"{folder_name} (Move failed)")
                success_count -= 1
        else:
            failed_tasks.append(folder_name)

    normalize_filenames(overall_pdf_output_dir)

    print("\n" + "=" * 70)
    print("Task Summary Report")
    print("-" * 70)
    print(f"Total projects (folders) found: {total_folders}")
    print(f"  - ✅ Successfully processed: {success_count}")
    print(f"  - ❌ Failed: {len(failed_tasks)}")
    
    if failed_tasks:
        print("\nList of failed projects:")
        for task in failed_tasks:
            print(f"  - {task}")
    
    print("-" * 70)
    print(f"All successfully generated PDF files have been saved in: {overall_pdf_output_dir}")
    print(f"All successfully processed original folders have been moved to: {success_move_target_dir}")


if __name__ == "__main__":
    print("=" * 70)
    print("=== Batch Image Folder to PDF Converter (V2 - move on success) ===")
    print("=" * 70)
    
    root_input_dir = ""
    # Try to load the default path from shared settings
    try:
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from shared_utils import utils
        settings = utils.load_settings()
        default_root_dir_name = settings.get("default_work_dir", "")
    except (ImportError, FileNotFoundError):
        default_root_dir_name = os.path.join(os.path.expanduser("~"), "Downloads")

    while True:
        prompt_message = (
            f"Please enter the path to the [root directory] containing multiple image subfolders.\n"
            f"(Press Enter to use the default path: '{default_root_dir_name}'): "
        )
        user_provided_path = input(prompt_message).strip()
        
        current_path_to_check = user_provided_path if user_provided_path else default_root_dir_name
        if not user_provided_path:
            print(f"\nUsing default path: {current_path_to_check}")

        abs_path_to_check = os.path.abspath(current_path_to_check)
        if os.path.isdir(abs_path_to_check):
            root_input_dir = abs_path_to_check
            print(f"Confirmed root processing directory: {root_input_dir}")
            break
        else:
            print(f"\nError: The path '{abs_path_to_check}' is not a valid directory or does not exist. Please try again.\n")
    
    try:
        run_conversion_process(root_input_dir)
    except Exception as e:
        print("\n" + "!"*70)
        print("The script encountered an unexpected critical error and has been terminated.")
        print(f"Error details: {e}")
        traceback.print_exc()
        print("!"*70)

    print("\nScript execution finished.")