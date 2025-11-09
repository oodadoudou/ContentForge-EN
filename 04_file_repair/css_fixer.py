import os
import shutil
import zipfile
import hashlib
import json
from bs4 import BeautifulSoup
from ebooklib import epub

def load_default_path_from_settings():
    """Read default working directory from the shared settings file."""
    try:
        # Navigate two levels up to reach the project root
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        settings_path = os.path.join(project_root, 'shared_assets', 'settings.json')
        with open(settings_path, 'r', encoding='utf-8') as f:
            settings = json.load(f)
        # If "default_work_dir" exists and is non-empty, return it
        default_dir = settings.get("default_work_dir")
        return default_dir if default_dir else "."
    except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
        print(f"Warning: Failed to read settings.json ({e}); using user's 'Downloads' as fallback path.")
        # Provide a general fallback path
        return os.path.join(os.path.expanduser("~"), "Downloads")

def get_unique_css_files(unzip_dir):
    """Get all unique CSS files in the unpacked directory."""
    css_files = {}
    for root, _, files in os.walk(unzip_dir):
        for file in files:
            if file.endswith('.css'):
                file_path = os.path.join(root, file)
                with open(file_path, 'rb') as f:
                    file_hash = hashlib.sha256(f.read()).hexdigest()
                if file_hash not in css_files:
                    css_files[file_hash] = os.path.relpath(file_path, unzip_dir)
    return list(css_files.values())

def fix_epub_css(epub_path, output_dir):
    """Fix CSS links in a single EPUB file."""
    temp_dir = os.path.join(output_dir, 'temp_epub_unpack')
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir)

    try:
        with zipfile.ZipFile(epub_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)

        unique_css_paths = get_unique_css_files(temp_dir)
        if not unique_css_paths:
            print(f"  - No CSS files found in {os.path.basename(epub_path)}; skipping.")
            return "skipped", "No CSS files found"

        modified = False
        for root, _, files in os.walk(temp_dir):
            for file in files:
                if file.endswith(('.html', '.xhtml')):
                    file_path = os.path.join(root, file)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        soup = BeautifulSoup(f, 'html.parser')

                    # Check whether there are no stylesheet links
                    if not (soup.head and soup.head.find_all('link', rel='stylesheet')):
                        head = soup.head
                        # If there is no <head> tag, create one
                        if not head:
                            head = soup.new_tag('head')
                            html_tag = soup.find('html')
                            if html_tag:
                                html_tag.insert(0, head)
                            else:
                                # If there is no <html> tag, the file is malformed; still attempt a fix
                                soup.insert(0, head)
                                print(f"  - Warning: File {file} lacks an <html> tag; attempted to create <head>.")

                        for css_path in unique_css_paths:
                            relative_css_path = os.path.relpath(os.path.join(temp_dir, css_path), root).replace('\\', '/')
                            link_tag = soup.new_tag('link', rel='stylesheet', type='text/css', href=relative_css_path)
                            head.append(link_tag)
                        
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(str(soup))
                        modified = True

        if modified:
            fixed_epub_path = os.path.join(output_dir, os.path.basename(epub_path))
            shutil.make_archive(fixed_epub_path.replace('.epub', ''), 'zip', temp_dir)
            os.rename(fixed_epub_path.replace('.epub', '.zip'), fixed_epub_path)
            return "fixed", None
        else:
            return "skipped", "All HTML files already have CSS links"

    except Exception as e:
        return "failed", str(e)
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

def main():
    """Main function: process all EPUB files."""
    default_path = load_default_path_from_settings()
    input_dir = input(f"Please enter the folder path containing EPUB files (default: {default_path}): ") or default_path
    
    if not os.path.isdir(input_dir):
        print(f"Error: Path '{input_dir}' is not a valid folder.")
        return

    output_dir = os.path.join(input_dir, 'fixed_epubs')
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    epub_files = [f for f in os.listdir(input_dir) if f.lower().endswith('.epub')]
    
    if not epub_files:
        print("No EPUB files found in the specified directory.")
        return

    fixed_files = []
    skipped_files = []
    failed_files = []

    print(f"\nStarting to process {len(epub_files)} EPUB file(s)...")
    for filename in epub_files:
        epub_path = os.path.join(input_dir, filename)
        print(f"Processing: {filename}")
        status, reason = fix_epub_css(epub_path, output_dir)
        
        if status == "fixed":
            fixed_files.append(filename)
            print(f"  - Status: fixed")
        elif status == "skipped":
            skipped_files.append(f"{filename} (Reason: {reason})")
            print(f"  - Status: skipped")
        elif status == "failed":
            failed_files.append(f"{filename} (Reason: {reason})")
            print(f"  - Status: failed")

    print("\n--- Processing Report ---")
    print(f"Total files: {len(epub_files)}")
    print(f"Successfully fixed: {len(fixed_files)}")
    print(f"Skipped: {len(skipped_files)}")
    print(f"Failed: {len(failed_files)}")

    if fixed_files:
        print("\nFixed files:")
        for f in fixed_files:
            print(f"- {f}")
    
    if skipped_files:
        print("\nSkipped files:")
        for f in skipped_files:
            print(f"- {f}")

    if failed_files:
        print("\nFailed files:")
        for f in failed_files:
            print(f"- {f}")

if __name__ == "__main__":
    main()