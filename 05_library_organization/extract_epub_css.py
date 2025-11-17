import os
import zipfile
import sys
import json

def extract_css_from_epubs(base_dir):
    """
    Traverse the specified base directory, find all .epub files in subdirectories,
    and extract any .css files inside them to the directory where the .epub file resides.

    :param base_dir: The base directory path specified by the user for searching.
    """
    if not os.path.isdir(base_dir):
        print(f"Error: Directory '{base_dir}' does not exist or is not a valid directory.", file=sys.stderr)
        sys.exit(1)

    print(f"[*] Start scanning directory: {os.path.abspath(base_dir)}")
    
    for root, dirs, files in os.walk(base_dir):
        for filename in files:
            if filename.endswith('.epub'):
                epub_path = os.path.join(root, filename)
                print(f"\n[+] Found EPUB file: {epub_path}")

                try:
                    with zipfile.ZipFile(epub_path, 'r') as zf:
                        all_zip_files = zf.namelist()
                        
                        css_files_in_zip = [f for f in all_zip_files if f.endswith('.css')]

                        if not css_files_in_zip:
                            print(f"  -> No CSS files found in '{filename}'.")
                            continue

                        print(f"  -> Found {len(css_files_in_zip)} CSS files, preparing to extract...")

                        for css_file_path in css_files_in_zip:
                            zf.extract(css_file_path, path=root)
                            extracted_filename = os.path.basename(css_file_path)
                            print(f"    - Extracted '{extracted_filename}' to '{root}'")

                except zipfile.BadZipFile:
                    print(f"  [!] Warning: Cannot open '{filename}'. The file may be corrupted or not a valid EPUB/ZIP file.")
                except Exception as e:
                    print(f"  [!] Error: Unknown error occurred while processing '{filename}': {e}")

    print("\n[*] All operations completed.")

def load_default_path_from_settings():
    """Read the default working directory from the shared settings file."""
    try:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        settings_path = os.path.join(project_root, 'shared_assets', 'settings.json')
        with open(settings_path, 'r', encoding='utf-8') as f:
            settings = json.load(f)
        default_dir = settings.get("default_work_dir")
        return default_dir if default_dir else "."
    except Exception:
        return os.path.join(os.path.expanduser("~"), "Downloads")

if __name__ == "__main__":
    default_path = load_default_path_from_settings()
    
    prompt_message = f"Enter target directory path (press Enter to use default path: {default_path}): "
    user_input = input(prompt_message)
    
    target_directory = user_input.strip() if user_input.strip() else default_path
    
    extract_css_from_epubs(target_directory)