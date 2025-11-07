import os
import sys
from ebooklib import epub, ITEM_DOCUMENT
from bs4 import BeautifulSoup
from tqdm import tqdm
import json

# --- Configuration ---
# Name of the output folder
OUTPUT_DIR_NAME = 'processed_files' 

def convert_epub_to_txt(epub_path, output_txt_path):
    """
    Convert a single EPUB file to a TXT file, preserving paragraph structure.

    Args:
        epub_path (str): Path to the source EPUB file.
        output_txt_path (str): Path to save the output TXT file.

    Returns:
        bool: True if conversion succeeded; False otherwise.
    """
    try:
        # Read the EPUB file using ebooklib
        book = epub.read_epub(epub_path)
        
        all_paragraphs = []

        # Iterate over all document items (usually chapter XHTML files)
        for item in book.get_items_of_type(ITEM_DOCUMENT):
            # Get the raw HTML content of the chapter
            html_content = item.get_content()
            
            # Parse HTML using BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Find all text tags (paragraphs and headings)
            # Includes <p> and heading tags <h1> to <h6>
            content_tags = soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
            
            for tag in content_tags:
                # Get all text inside the tag
                text = tag.get_text(' ', strip=True)
                if text: # Ensure no empty content added
                    all_paragraphs.append(text)
        
        # Join all paragraphs with two newlines (i.e., a blank line)
        final_text = "\n\n".join(all_paragraphs)
        
        # Write the final text content to a TXT file using UTF-8 encoding
        with open(output_txt_path, 'w', encoding='utf-8') as f:
            f.write(final_text)
            
        return True

    except Exception as e:
        # Print error info on any exception during processing
        print(f"\n[!] Error processing file '{os.path.basename(epub_path)}': {e}")
        return False

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

def main():
    """
    Main function that handles user input, directory scanning, and conversion.
    """
    print("--- EPUB to TXT Converter ---")

    # --- Update: Dynamically load default path ---
    default_dir = load_default_path_from_settings()
    
    # Get user input; if user presses Enter, use the default path
    input_dir = input(f"Enter the directory containing EPUB files (default: {default_dir}): ").strip()
    if not input_dir:
        input_dir = default_dir
        print(f"[*] No path entered; using default directory: {input_dir}")

    # Check if the specified directory exists
    if not os.path.isdir(input_dir):
        print(f"[!] Error: Directory '{input_dir}' does not exist. Exiting.")
        sys.exit(1)

    # Create output directory for processed files
    output_dir = os.path.join(input_dir, OUTPUT_DIR_NAME)
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"[*] Converted .txt files will be saved in: {output_dir}")

    # Scan directory to find all .epub files
    epub_files = [f for f in os.listdir(input_dir) if f.lower().endswith('.epub')]

    if not epub_files:
        print("\n[!] No .epub files found in the specified directory.")
        return

    print(f"\n[*] Found {len(epub_files)} EPUB file(s); starting conversion...")
    
    success_count = 0
    fail_count = 0

    # Use tqdm to visualize progress
    with tqdm(total=len(epub_files), desc="Conversion Progress", unit="file") as pbar:
        for filename in epub_files:
            pbar.set_postfix_str(filename, refresh=True)
            
            source_epub_path = os.path.join(input_dir, filename)
            
            # Build output .txt filename
            base_name = os.path.splitext(filename)[0]
            output_txt_path = os.path.join(output_dir, f"{base_name}.txt")
            
            # 调用核心转换函数
            if convert_epub_to_txt(source_epub_path, output_txt_path):
                success_count += 1
            else:
                fail_count += 1
            
            pbar.update(1)

    print("\n----------------------------------------")
    print(f"[✓] Task completed!")
    print(f"    - Successfully converted: {success_count} file(s)")
    print(f"    - Conversion failed: {fail_count} file(s)")
    print(f"    - Results saved to '{OUTPUT_DIR_NAME}' folder.")

# 当该脚本被直接执行时，运行 main 函数
if __name__ == '__main__':
    main()