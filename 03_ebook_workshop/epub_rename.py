import os
import sys
import zipfile
import tempfile
import shutil
import xml.etree.ElementTree as ET
import json

def sanitize_filename(name):
    """Remove illegal characters from a string to make a valid filename."""
    invalid_chars = r'<>:"/\|?*'
    if name:
        for char in invalid_chars:
            name = name.replace(char, '')
        return name.strip()
    return "Untitled"

def get_unique_filepath(path):
    """Check if a file path exists; append a number to make it unique if needed."""
    if not os.path.exists(path):
        return path
    directory, filename = os.path.split(path)
    name, ext = os.path.splitext(filename)
    counter = 1
    while True:
        new_name = f"{name} ({counter}){ext}"
        new_path = os.path.join(directory, new_name)
        if not os.path.exists(new_path):
            return new_path
        counter += 1

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

def run_epub_modifier_v8_final():
    """
    v8: Final version. All files will be processed; skipped files use their original metadata title.
    """
    print("=====================================================")
    print("=     EPUB Rename Tool (v8 - Final full processing)     =")
    print("=====================================================")
    print("Features:")
    print("  - All scanned files will be processed and placed in the 'processed_files' folder.")
    print("  - Entering a new title uses that title for the filename.")
    print("  - Pressing Enter uses the book's own metadata title.")

    # --- 修改：动态加载默认路径 ---
    default_path = load_default_path_from_settings()
    folder_path = input(f"\nEnter the folder path containing EPUB files (default: {default_path}): ").strip() or default_path

    if not os.path.isdir(folder_path):
        sys.exit(f"\nError: Folder '{folder_path}' does not exist.")

    processed_folder_path = os.path.join(folder_path, "processed_files")
    os.makedirs(processed_folder_path, exist_ok=True)

    epub_files = sorted([f for f in os.listdir(folder_path) if f.lower().endswith('.epub')])
    if not epub_files:
        sys.exit(f"No EPUB files found in '{folder_path}'.")
        
    print("\nFound the following files to process:")
    for i, filename in enumerate(epub_files): print(f"  {i+1}. {filename}")

    # 获取用户意图
    tasks = []
    print("\n----------------------------------------")
    for i, filename in enumerate(epub_files):
        user_input = input(f"\n{i+1}. Enter a new title for '{filename}' (or press Enter to standardize using metadata title): ")
        tasks.append({'filename': filename, 'new_title_input': user_input.strip()})
    
    print("\n--- Starting batch processing ---")
    
    for task in tasks:
        original_filename = task['filename']
        new_title_input = task['new_title_input']
        original_path = os.path.join(folder_path, original_filename)
        temp_dir = None
        
        print(f"\n--- Processing: {original_filename} ---")
        try:
            temp_dir = tempfile.mkdtemp()
            with zipfile.ZipFile(original_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)

            container_path = os.path.join(temp_dir, 'META-INF', 'container.xml')
            if not os.path.exists(container_path):
                raise FileNotFoundError("Error: META-INF/container.xml not found")
            
            tree = ET.parse(container_path)
            root = tree.getroot()
            ns = {'cn': 'urn:oasis:names:tc:opendocument:xmlns:container'}
            opf_path_element = root.find('cn:rootfiles/cn:rootfile', ns)
            if opf_path_element is None: raise FileNotFoundError("Error: <rootfile> tag not found in container.xml")
            
            opf_file_rel_path = opf_path_element.get('full-path')
            opf_file_abs_path = os.path.join(temp_dir, opf_file_rel_path)
            print(f"  - Found metadata file: {opf_file_rel_path}")

            opf_ns = {'dc': 'http://purl.org/dc/elements/1.1/'}
            tree = ET.parse(opf_file_abs_path)
            root = tree.getroot()
            
            title_element = root.find('.//dc:title', opf_ns)
            if title_element is None: raise ValueError(f"Error: <dc:title> tag not found in '{opf_file_rel_path}'")

            current_title = title_element.text or ""
            
            # Decide final title
            if new_title_input:
                target_title = new_title_input
                print(f"  - New title entered: '{target_title}'")
                title_element.text = target_title
                tree.write(opf_file_abs_path, encoding='utf-8', xml_declaration=True)
            else:
                target_title = current_title
                print(f"  - Skipped; using original book title: '{target_title}'")

            # 重新打包
            new_safe_filename = sanitize_filename(target_title) + '.epub'
            destination_path = get_unique_filepath(os.path.join(processed_folder_path, new_safe_filename))
            
            print(f"  - Repacking as: {os.path.basename(destination_path)}")
            with zipfile.ZipFile(destination_path, 'w') as zip_out:
                mimetype_path = os.path.join(temp_dir, 'mimetype')
                if os.path.exists(mimetype_path):
                    zip_out.write(mimetype_path, 'mimetype', compress_type=zipfile.ZIP_STORED)
                
                for root_dir, _, files in os.walk(temp_dir):
                    for file in files:
                        file_path = os.path.join(root_dir, file)
                        arcname = os.path.relpath(file_path, temp_dir)
                        if arcname != 'mimetype':
                            zip_out.write(file_path, arcname, compress_type=zipfile.ZIP_DEFLATED)
            print("  - Processed successfully!")

        except Exception as e:
            print(f"  ! A critical error occurred while processing '{original_filename}': {e}")
        finally:
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)

    print("\n--- All tasks completed ---")

if __name__ == "__main__":
    run_epub_modifier_v8_final()