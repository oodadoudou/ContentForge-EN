import os
import sys
import json

def fix_text_file_encoding(file_path, output_path):
    """
    Try reading a text file using multiple encodings and re-write in UTF-8.
    
    :param file_path: Original file path.
    :param output_path: Path to save the fixed file.
    """
    # Common Chinese encodings listed in typical order
    encodings_to_try = ['utf-8', 'gbk', 'gb18030', 'big5']
    
    content = None
    original_encoding = None

    # Try opening the file with different encodings
    for encoding in encodings_to_try:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read()
            original_encoding = encoding
            print(f"  - [Success] Read file successfully using '{encoding}' encoding.")
            break  # Exit loop after first successful read
        except UnicodeDecodeError:
            # On decode failure, try next encoding
            continue
        except Exception as e:
            # Catch other possible exceptions
            print(f"  - [Warning] Unknown error using '{encoding}' encoding: {e}")
            continue

    # If all encodings fail, it may not be a text file or uses uncommon encoding
    if content is None:
        print(f"  - [Error] Unable to decode file: {os.path.basename(file_path)}. It may not be plain text or uses unsupported encoding.")
        return

    # Write content to a new file in UTF-8
    try:
        # Using 'utf-8-sig' writes a BOM to help certain Windows apps (e.g., Notepad) recognize UTF-8.
        with open(output_path, 'w', encoding='utf-8-sig') as f:
            f.write(content)
        print(f"  -> [Done] File fixed and saved to: {os.path.relpath(output_path)}")
    except Exception as e:
        print(f"  - [Error] Failed to write new file: {e}")

# --- Added: function to load default path from settings.json ---
def load_default_path_from_settings():
    """Read default working directory from the shared settings file."""
    try:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        settings_path = os.path.join(project_root, 'shared_assets', 'settings.json')
        with open(settings_path, 'r', encoding='utf-8') as f:
            settings = json.load(f)
        default_dir = settings.get("default_work_dir")
        return default_dir if default_dir else "."
    except Exception:
        return os.path.join(os.path.expanduser("~"), "Downloads")

def main():
    """
    Script main function: handle user input and file traversal.
    """
    # --- Change: dynamically load default path ---
    default_path = load_default_path_from_settings()
    
    # Prompt for input, showing the default value
    prompt_message = f"Please enter the directory of TXT files to process (Press Enter to use: {default_path}): "
    target_directory = input(prompt_message).strip() or default_path

    # Validate input path
    if not os.path.isdir(target_directory):
        print(f"Error: Directory '{target_directory}' does not exist or is invalid.", file=sys.stderr)
        sys.exit(1)
        
    # Create unified output folder
    output_dir = os.path.join(target_directory, "processed_files")
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"\n[*] Starting to scan directory: {os.path.abspath(target_directory)}")
    print(f"[*] All processed files will be saved to: {os.path.abspath(output_dir)}")
    
    # Traverse directory (including subdirectories)
    for root, _, files in os.walk(target_directory):
        # Skip our output directory to avoid re-processing
        if os.path.abspath(root).startswith(os.path.abspath(output_dir)):
            continue

        for filename in files:
            # Only process .txt files
            if filename.endswith('.txt'):
                file_path = os.path.join(root, filename)
                output_path = os.path.join(output_dir, filename)
                
                print(f"\n[Process file] {filename}")
                fix_text_file_encoding(file_path, output_path)
    
    print("\n[*] All operations completed.")

if __name__ == "__main__":
    main()