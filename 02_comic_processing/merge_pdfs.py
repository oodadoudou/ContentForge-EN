import os
import re
import pikepdf
import natsort
import logging
import json  # Added: for parsing JSON

# --- Configuration ---
# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define subdirectory name for merged PDFs
MERGED_PDF_SUBDIR_NAME = "merged_pdf"

# Removed old hard-coded DEFAULT_INPUT_DIR

def natural_sort_key(s: str) -> list:
    """
    Generate a natural sort key for filenames.
    """
    return [int(text) if text.isdigit() else text.lower() for text in re.split('([0-9]+)', s)]


def merge_pdfs_in_directory(root_dir: str):
    """
    Merge PDFs within the specified directory structure.
    """
    # Create merged_pdf output directory
    output_dir = os.path.join(root_dir, MERGED_PDF_SUBDIR_NAME)
    os.makedirs(output_dir, exist_ok=True)
    logging.info(f"Output directory '{output_dir}' is ready.")

    subfolders = [d.path for d in os.scandir(root_dir) if d.is_dir() and d.name != MERGED_PDF_SUBDIR_NAME]

    if not subfolders:
        logging.warning(f"No subfolders to process found under root directory '{root_dir}'.")
        return

    print(f"\n--- Found {len(subfolders)} subfolders; starting merge ---")

    for subfolder_path in natsort.natsorted(subfolders):
        subfolder_name = os.path.basename(subfolder_path)
        logging.info(f"===== Processing subfolder: {subfolder_name} =====")

        pdf_files_to_merge = []
        logging.info(f"Searching for PDF files in '{subfolder_name}' and all descendant directories...")
        for dirpath, _, filenames in os.walk(subfolder_path):
            for filename in filenames:
                if filename.lower().endswith('.pdf'):
                    pdf_path = os.path.join(dirpath, filename)
                    pdf_files_to_merge.append(pdf_path)
                    logging.info(f"  [Found file] {os.path.relpath(pdf_path, subfolder_path)}")

        pdf_files_to_merge = natsort.natsorted(pdf_files_to_merge)

        if not pdf_files_to_merge:
            logging.warning(f"No PDFs found in '{subfolder_name}', skipping.")
            print(f"  🟡 No PDFs discovered in '{subfolder_name}', skipped.\n")
            continue

        print(f"  - Found {len(pdf_files_to_merge)} PDF(s) in '{subfolder_name}'. Preparing to merge.")

        output_pdf_path = os.path.join(output_dir, f"{subfolder_name}.pdf")
        new_pdf = pikepdf.Pdf.new()

        try:
            for i, pdf_path in enumerate(pdf_files_to_merge):
                try:
                    with pikepdf.open(pdf_path) as src_pdf:
                        new_pdf.pages.extend(src_pdf.pages)
                        print(f"    ({i+1}/{len(pdf_files_to_merge)}) Added: {os.path.basename(pdf_path)}")
                except Exception as e:
                    logging.error(f"    Error merging file '{os.path.basename(pdf_path)}': {e}")

            if len(new_pdf.pages) > 0:
                new_pdf.save(output_pdf_path)
                print(f"  ✅ Success! Merged file saved to: '{output_pdf_path}'\n")
            else:
                logging.warning(f"Merge result for '{subfolder_name}' is empty; no PDF generated.")
        except Exception as e:
            logging.error(f"Critical error saving merged PDF '{output_pdf_path}': {e}")
        finally:
             pass

# ▼▼▼ 主函数已按新标准修改 ▼▼▼
def main():
    """
    Main execution function
    """
    print("\n--- PDF Merge Tool ---")
    print("This tool automatically searches each subfolder (and all descendant directories) for PDF files,")
    print("and merges them into a single PDF named after the subfolder.")

    # --- Added: dynamic path loader consistent with pipeline scripts ---
    def load_default_path_from_settings():
        """Read the default work directory from the shared settings file."""
        try:
            # Assume this script is in a project subdirectory; go up two levels to find project root
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            settings_path = os.path.join(project_root, 'shared_assets', 'settings.json')
            with open(settings_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)
            # Treat empty or None default_work_dir as invalid
            default_dir = settings.get("default_work_dir")
            return default_dir if default_dir else "."
        except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
            print(f"Warning: Failed to read settings.json ({e}); using built-in fallback path.")
            # Provide a generic fallback path
            return os.path.join(os.path.expanduser("~"), "Downloads")
    # --- End of added section ---

    default_root_dir_name = load_default_path_from_settings()

    # --- Standardized path handling logic ---
    while True:
        prompt_message = (
            f"\n- Please enter the path to the target root folder.\n"
            f"  (Press Enter to use the default path: '{default_root_dir_name}'): "
        )
        user_input = input(prompt_message).strip()

        # Use default path if user provides nothing; otherwise use the provided path
        root_dir_to_check = user_input if user_input else default_root_dir_name
        
        abs_path_to_check = os.path.abspath(root_dir_to_check)

        if os.path.isdir(abs_path_to_check):
            root_dir = abs_path_to_check
            print(f"\n[*] Processing directory: {root_dir}")
            break
        else:
            print(f"Error: Path '{abs_path_to_check}' is not a valid directory or does not exist.")
    # --------------------------

    print(f"\n--- Starting processing; root directory: {root_dir} ---")
    merge_pdfs_in_directory(root_dir)
    print("\n--- All operations completed ---")

if __name__ == "__main__":
    main()