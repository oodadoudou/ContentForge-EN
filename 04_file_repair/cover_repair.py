import os
import sys
import zipfile
import tempfile
import re
from xml.etree import ElementTree as ET
import json

def find_opf_file(unzip_dir):
    """Find the .opf file in the unpacked directory."""
    for root, _, files in os.walk(unzip_dir):
        for file in files:
            if file.endswith('.opf'):
                return os.path.join(root, file)
    return None

def get_cover_info(opf_path):
    """
    Parse cover image and cover page info from the .opf file.
    Returns a dict with cover image path and cover HTML file path.
    """
    if not opf_path:
        return None

    cover_info = {'image_path': None, 'html_path': None}
    try:
        # Register namespaces to parse correctly
        namespaces = {
            'opf': 'http://www.idpf.org/2007/opf',
            'dc': 'http://purl.org/dc/elements/1.1/'
        }
        ET.register_namespace('opf', namespaces['opf'])
        ET.register_namespace('dc', namespaces['dc'])

        tree = ET.parse(opf_path)
        root = tree.getroot()
        
        # --- Step 1: Find the cover image ID ---
        cover_id = None
        # First try EPUB3 <meta> tag
        meta_cover = root.find('.//opf:meta[@name="cover"]', namespaces)
        if meta_cover is not None:
            cover_id = meta_cover.get('content')
        
        # --- Step 2: Find image path by ID from manifest ---
        manifest = root.find('opf:manifest', namespaces)
        if manifest is None: return None
        
        if cover_id:
            cover_item = manifest.find(f".//opf:item[@id='{cover_id}']", namespaces)
            if cover_item is not None:
                cover_info['image_path'] = cover_item.get('href')

        # If not found, try to find item with cover-image property
        if not cover_info['image_path']:
            cover_item = manifest.find(".//*[@properties='cover-image']", namespaces)
            if cover_item is not None:
                cover_info['image_path'] = cover_item.get('href')
        
        if not cover_info['image_path']:
             print("  - [Warning] No explicit cover image definition found in .opf.")
             return None

        # --- Step 3: Find the cover XHTML file ---
        # Find XHTML file that references the cover image
        for item in manifest.findall('.//opf:item', namespaces):
            href = item.get('href', '')
            if 'cover' in href.lower() and href.endswith(('.xhtml', '.html')):
                cover_info['html_path'] = href
                break
        
        if not cover_info['html_path']:
            print("  - [Warning] No explicit cover HTML file found; will create a new one.")
            cover_info['html_path'] = 'cover.xhtml' # Create one if not found

        return cover_info
    except Exception as e:
        print(f"  - [Error] Failed to parse OPF file: {e}")
        return None

def create_and_write_cover_html(unzip_dir, cover_info):
    """
    Create or overwrite the cover HTML file with a standardized template.
    """
    # Compute cover image path relative to cover HTML
    html_full_path = os.path.join(os.path.dirname(os.path.join(unzip_dir, 'DUMMY')), cover_info['html_path'])
    image_full_path = os.path.join(os.path.dirname(os.path.join(unzip_dir, 'DUMMY')), cover_info['image_path'])
    
    # Get directory paths of both files
    html_dir = os.path.dirname(html_full_path)
    image_dir = os.path.dirname(image_full_path)
    
    # Compute relative path
    relative_image_path = os.path.relpath(image_dir, html_dir)
    # Compose final src path
    final_image_src = os.path.join(relative_image_path, os.path.basename(image_full_path)).replace('\\', '/')
    
    # Highly compatible cover HTML template
    cover_html_template = f"""<?xml version='1.0' encoding='utf-8'?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
  <title>Cover</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <style type="text/css">
    html, body {{ margin: 0; padding: 0; height: 100%; width: 100%; overflow: hidden; }}
    .cover-container {{ width: 100%; height: 100%; text-align: center; }}
    .cover-image {{ max-width: 100%; max-height: 100%; height: auto; width: auto; }}
  </style>
</head>
<body>
  <div class="cover-container">
    <img src="{final_image_src}" alt="Cover" class="cover-image"/>
  </div>
</body>
</html>"""

    # Find the directory containing the OPF file (content root)
    opf_path = find_opf_file(unzip_dir)
    content_root = os.path.dirname(opf_path)
    
    # Write the new cover HTML file
    target_html_path = os.path.join(content_root, cover_info['html_path'])
    os.makedirs(os.path.dirname(target_html_path), exist_ok=True)
    with open(target_html_path, 'w', encoding='utf-8') as f:
        f.write(cover_html_template)
    print(f"  - [Fixed] Generated standardized cover file: {cover_info['html_path']}")


def fix_cover(epub_path, output_dir):
    """
    Repair the cover of a single EPUB file.
    """
    print(f"\n[Process] {os.path.basename(epub_path)}")
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            with zipfile.ZipFile(epub_path, 'r') as zf:
                zf.extractall(temp_dir)
            
            opf_path = find_opf_file(temp_dir)
            if not opf_path:
                print("  - [Error] .opf file not found; unable to process.")
                return

            cover_info = get_cover_info(opf_path)
            if not cover_info or not cover_info.get('image_path'):
                print("  - [Skip] Failed to identify cover information.")
                return

            create_and_write_cover_html(os.path.dirname(opf_path), cover_info)
            
            # Repack
            base_name, _ = os.path.splitext(os.path.basename(epub_path))
            new_epub_path = os.path.join(output_dir, f"{base_name}-cover-fixed.epub")
            
            with zipfile.ZipFile(new_epub_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                mimetype_path = os.path.join(temp_dir, 'mimetype')
                if os.path.exists(mimetype_path):
                    zf.write(mimetype_path, 'mimetype', compress_type=zipfile.ZIP_STORED)
                
                for root, _, files in os.walk(temp_dir):
                    for file in files:
                        if file != 'mimetype':
                            full_path = os.path.join(root, file)
                            arcname = os.path.relpath(full_path, temp_dir)
                            zf.write(full_path, arcname)
            
            print(f"  -> [Success] Cover fixed; new file saved to: {os.path.basename(output_dir)}")
        
        except Exception as e:
            print(f"  - [Critical] Unexpected error during processing: {e}")

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
    """Script entry point"""
    # --- Change: dynamically load default path ---
    default_path = load_default_path_from_settings()
    prompt_message = f"Please enter the directory containing EPUB files to fix covers (Press Enter to use: {default_path}): "
    target_directory = input(prompt_message).strip() or default_path

    if not os.path.isdir(target_directory):
        print(f"Error: Directory '{target_directory}' does not exist or is invalid.", file=sys.stderr)
        sys.exit(1)
        
    output_dir = os.path.join(target_directory, "processed_files")
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"[*] Starting to scan directory: {os.path.abspath(target_directory)}")
    print(f"[*] All fixed files will be saved to: {os.path.abspath(output_dir)}")
    
    for filename in os.listdir(target_directory):
        if filename.endswith('.epub') and '-cover-fixed' not in filename:
            file_path = os.path.join(target_directory, filename)
            if os.path.isfile(file_path):
                fix_cover(file_path, output_dir)
    
    print("\n[*] All operations completed.")

if __name__ == "__main__":
    main()