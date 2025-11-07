import os
import sys
import zipfile
import shutil
import tempfile
import json

# --- Configuration ---
NEW_CSS_FILENAME = "new_style.css"
SHARED_ASSETS_DIR_NAME = "shared_assets"
OUTPUT_DIR_NAME = "processed_files"

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_new_css_content():
    """Read CSS file content from shared_assets according to the project structure."""
    css_path = os.path.join(PROJECT_ROOT, SHARED_ASSETS_DIR_NAME, NEW_CSS_FILENAME)
    
    if not os.path.exists(css_path):
        print(f"Error: Style file '{NEW_CSS_FILENAME}' not found in '{SHARED_ASSETS_DIR_NAME}'.")
        print(f"Please ensure the file exists at '{css_path}'.")
        return None
    
    with open(css_path, 'r', encoding='utf-8') as f:
        return f.read()

def modify_single_epub(epub_path, output_dir, new_css_content):
    """Process a single EPUB file and replace its CSS styles."""
    base_name = os.path.basename(epub_path)
    output_epub_path = os.path.join(output_dir, base_name)
    
    # 创建一个临时目录来解压ePub
    temp_extract_dir = tempfile.mkdtemp(prefix=f"{os.path.splitext(base_name)[0]}_")
    
    print(f"\n[+] Processing: {base_name}")

    try:
        # 1. 解压 ePub 文件
        with zipfile.ZipFile(epub_path, 'r') as zip_ref:
            zip_ref.extractall(temp_extract_dir)
            print(f"  -> Extracted to temporary directory: {os.path.basename(temp_extract_dir)}")

        # 2. 查找并替换所有 CSS 文件
        css_replaced_count = 0
        for root, _, files in os.walk(temp_extract_dir):
            for file in files:
                if file.endswith('.css'):
                    css_file_path = os.path.join(root, file)
                    with open(css_file_path, 'w', encoding='utf-8') as f:
                        f.write(new_css_content)
                    css_replaced_count += 1
                    print(f"  -> Replaced style file: {os.path.relpath(css_file_path, temp_extract_dir)}")
        
        if css_replaced_count == 0:
            print("  -> Warning: No CSS files found in this EPUB.")

        # 3. 重新打包成 ePub
        print(f"  -> Repacking as: {base_name}")
        with zipfile.ZipFile(output_epub_path, 'w', zipfile.ZIP_DEFLATED) as zip_out:
            mimetype_path = os.path.join(temp_extract_dir, 'mimetype')
            if os.path.exists(mimetype_path):
                zip_out.write(mimetype_path, 'mimetype', compress_type=zipfile.ZIP_STORED)
            else:
                 print("  -> Warning: 'mimetype' file not found; EPUB may be invalid.")

            for root, _, files in os.walk(temp_extract_dir):
                for file in files:
                    if file == 'mimetype':
                        continue
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, temp_extract_dir)
                    zip_out.write(file_path, arcname)

        print(f"  -> Completed; saved to: {os.path.relpath(output_epub_path)}")
        return True

    except zipfile.BadZipFile:
        print(f"  -> Error: '{base_name}' is not a valid ZIP/EPUB file; skipped.")
        return False
    except Exception as e:
        print(f"  -> Unknown error occurred while processing '{base_name}': {e}")
        return False
    finally:
        # 4. Clean temporary files
        shutil.rmtree(temp_extract_dir)

def process_epub_directory(root_dir):
    """Process all EPUB files in the specified root directory."""
    print("--- EPUB Style Batch Replacement Tool ---")
    
    new_css_content = get_new_css_content()
    if new_css_content is None:
        return

    # 在目标ePub目录下创建输出文件夹
    output_path = os.path.join(root_dir, OUTPUT_DIR_NAME)
    os.makedirs(output_path, exist_ok=True)
    
    print(f"\nScanning directory: {os.path.abspath(root_dir)}")
    print(f"Processed files will be saved to: {os.path.abspath(output_path)}")
    
    epub_files = [f for f in os.listdir(root_dir) if f.lower().endswith('.epub')]
    
    if not epub_files:
        print("\nNo .epub files found in the specified directory.")
        return
        
    success_count = 0
    fail_count = 0
    
    for epub_file in epub_files:
        epub_full_path = os.path.join(root_dir, epub_file)
        if modify_single_epub(epub_full_path, output_path, new_css_content):
            success_count += 1
        else:
            fail_count += 1
            
    print("\n--- Completed ---")
    print(f"Total: {len(epub_files)} file(s) | Success: {success_count} | Failed: {fail_count}")

# --- Added: Load default path from settings.json ---
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

if __name__ == "__main__":
    # --- Update: Dynamically load default path ---
    default_path = load_default_path_from_settings()

    # Get user input
    prompt_message = (
        "Please enter the directory path containing EPUB files\n"
        f"(Press Enter to use the default path: {default_path}): "
    )
    target_dir_input = input(prompt_message)

    # 如果用户未输入（或输入为空白），则使用默认路径
    target_dir = target_dir_input.strip().strip('\'"') if target_dir_input.strip() else default_path
    
    if not target_dir_input.strip():
        print(f"No path entered; using default directory: {target_dir}")

    # 检查最终确定的目录是否存在
    if not os.path.isdir(target_dir):
        print(f"\nError: Directory '{target_dir}' does not exist or is not valid.")
        print("Please verify the path or the default path exists.")
        sys.exit(1)
        
    process_epub_directory(target_dir)