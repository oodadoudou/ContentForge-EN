import os
import sys
import json
import requests
import time
import shutil
import re
from pypinyin import pinyin, Style

# --- Global configuration (overridden by settings file) ---
API_URL = ""
API_BEARER_TOKEN = ""
API_MODEL = ""

# --- AI translation prompts ---
SYSTEM_PROMPT = "You are a professional novel translator."
TRANSLATION_PROMPT_TEMPLATE = """
Primary goal: Accurately, fluently, and emotionally translate Korean or Japanese novel titles into Simplified Chinese to provide an immersive reading experience.

I. Format and structure rules
Line-by-line translation:
Translate strictly according to the original number of lines and paragraphs.
Do not merge or split paragraphs or line breaks arbitrarily.

Symbol handling:
In the translation, only retain the following English punctuation and symbols: !, ?, "", @.
Content within [] indicates author names; do not translate them. Remove and skip.

Content preservation:
English words, code, numbers, URLs, etc., that appear in the original text must be preserved as-is in the translation.

II. Content and style standards
Completeness:
Except for symbols to be discarded per the above rules, all original content must be fully translated.
This includes but is not limited to: onomatopoeia, mimetic words, modal particles, interjections, and all proper nouns (such as character names, skill names, and place names).

Fluency:
The translation must be smooth and conform to modern Simplified Chinese colloquial expressions.
Aim for natural wording that reads clearly and easily; avoid rigid "translationese".

Do not add any extra explanations, notes, or formatting; only return the translated single-line text.

Please translate the following single-line text:
{}
"""

# --- File Organizer configuration ---
ORGANIZER_TARGET_EXTENSIONS = ".pdf .epub .txt .jpg .jpeg .png .gif .bmp .tiff .webp .zip .rar .7z .tar .gz"

def print_progress_bar(iteration, total, prefix='', suffix='', decimals=1, length=50, fill='█', print_end="\r"):
    if total == 0:
        percent_str, filled_length = "0.0%", 0
    else:
        percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
        percent_str, filled_length = f"{percent}%", int(length * iteration // total)
    bar = fill * filled_length + '-' * (length - filled_length)
    sys.stdout.write(f'\r{prefix} |{bar}| {percent_str} {suffix}')
    sys.stdout.flush()
    if iteration == total:
        sys.stdout.write('\n')
        sys.stdout.flush()

# --- New: load configuration from settings.json ---
def load_settings_from_json():
    """Read all configuration from the shared settings file and update global variables."""
    global API_URL, API_BEARER_TOKEN, API_MODEL
    try:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        settings_path = os.path.join(project_root, 'shared_assets', 'settings.json')
        with open(settings_path, 'r', encoding='utf-8') as f:
            settings = json.load(f)
        
        # Load AI configuration
        ai_config = settings.get("ai_config", {})
        API_URL = ai_config.get("base_url", "https://ark.cn-beijing.volces.com/api/v3/chat/completions")
        API_BEARER_TOKEN = ai_config.get("api_key", "")
        API_MODEL = ai_config.get("model_name", "doubao-pro-32k")
        
        # Return default working directory
        default_dir = settings.get("default_work_dir")
        return default_dir if default_dir else os.path.join(os.path.expanduser("~"), "Downloads")

    except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
        print(f"Warning: Failed to read settings.json ({e}); using built-in fallback values.")
        return os.path.join(os.path.expanduser("~"), "Downloads")

# ==============================================================================
# Module 1: File Organization
# ==============================================================================
def clean_name_for_grouping(filename: str) -> str:
    cleaned = filename
    if cleaned.startswith('['):
        try:
            idx = cleaned.index(']') + 1
            cleaned = cleaned[idx:].strip()
        except ValueError:
            pass
    cleaned = os.path.splitext(cleaned)[0]
    cut_pos = len(cleaned)
    for ch in '0123456789[]()@#%&':
        pos = cleaned.find(ch)
        if pos != -1 and pos < cut_pos:
            cut_pos = pos
    cleaned = cleaned[:cut_pos].strip()
    return re.sub(r'\s+', ' ', cleaned)

def get_folder_name_for_group(group: list[str]) -> str:
    if not group: return "Unnamed_Group"
    cleaned_group_names = [clean_name_for_grouping(f) for f in group if clean_name_for_grouping(f)]
    if not cleaned_group_names:
        return re.sub(r'[\\/*?:"<>|]', '_', os.path.splitext(group[0])[0])[:50] or "Organized_Files"
    folder_name = os.path.commonprefix(cleaned_group_names).strip(' -_')
    if len(folder_name) < 3:
        folder_name = cleaned_group_names[0]
    return folder_name[:50] or "Organized_Group"

def organize_files_into_subdirs(root_directory: str):
    """Organize loose files in the root directory into subfolders based on filenames."""
    print(f"\n--- Preprocessing: Start organizing files in the root directory ---")
    target_extensions = set(ext.lower() for ext in ORGANIZER_TARGET_EXTENSIONS.split())
    try:
        all_files = [
            f for f in os.listdir(root_directory)
            if os.path.isfile(os.path.join(root_directory, f)) and os.path.splitext(f)[1].lower() in target_extensions
        ]
        if not all_files:
            print("    No files to organize in the root directory.")
            return
        
        print(f"    Found {len(all_files)} files to organize. Performing intelligent grouping...")
        groups = {}
        for filename in all_files:
            group_key = clean_name_for_grouping(filename)
            if group_key not in groups:
                groups[group_key] = []
            groups[group_key].append(filename)

        moved_count = 0
        print_progress_bar(0, len(groups), prefix='    Organizing progress:', suffix='Done', length=40)
        i = 0
        for group_key, file_list in groups.items():
            i += 1
            folder_name_raw = group_key if len(group_key) > 2 else os.path.splitext(file_list[0])[0]
            folder_name_sanitized = re.sub(r'[\\/*?:"<>|]', '_', folder_name_raw).strip()
            if not folder_name_sanitized: continue

            folder_path = os.path.join(root_directory, folder_name_sanitized)
            os.makedirs(folder_path, exist_ok=True)

            for filename in file_list:
                source_path = os.path.join(root_directory, filename)
                destination_path = os.path.join(folder_path, filename)
                if os.path.exists(source_path):
                    shutil.move(source_path, destination_path)
                    moved_count += 1
            print_progress_bar(i, len(groups), prefix='    Organizing progress:', suffix='Done', length=40)
        
        print(f"    File organization complete. Moved {moved_count} files into newly created subfolders.")
    except Exception as e:
        print(f"    Error occurred during file organization: {e}")

# ==============================================================================
# Module 2: Extraction, Translation, and Initial Renaming
# ==============================================================================
def extract_folder_names_to_file(root_directory: str) -> list:
    """Scan the directory to get subfolder names, save them to list.txt, and return the list."""
    print(f"\n--- Step 1: Scan directory and generate list.txt ---")
    try:
        subdirectories = [
            entry_name for entry_name in os.listdir(root_directory)
            if os.path.isdir(os.path.join(root_directory, entry_name)) and not entry_name.startswith('.')
        ]
        subdirectories.sort()
        if not subdirectories:
            print("    No subfolders found in this directory.")
            return []
        print(f"    Found {len(subdirectories)} subfolders.")
        with open(os.path.join(root_directory, "list.txt"), 'w', encoding='utf-8') as f:
            for dir_name in subdirectories:
                f.write(dir_name + '\n')
        print(f"    Successfully wrote folder name list to: {os.path.join(root_directory, 'list.txt')}")
        return subdirectories
    except Exception as e:
        print(f"    Step 1 encountered an error: {e}")
    return []

def translate_names_via_api(root_directory: str, original_names: list) -> list:
    """Call the AI API to translate folder names one by one and save results to list-zh.txt."""
    print(f"\n--- Step 2: Send to AI for translation and generate list-zh.txt ---")
    if not original_names: return []
    if not API_BEARER_TOKEN:
        print("    Error: API key is not configured in settings.json. Skipping translation step.")
        return original_names

    translated_names = []
    headers = {"Authorization": f"Bearer {API_BEARER_TOKEN}"}
    total_names = len(original_names)
    print_progress_bar(0, total_names, prefix='    Translation progress:', suffix='Done', length=40)
    for i, original_name in enumerate(original_names):
        name_to_translate = original_name.replace('+', ' ').replace('_', ' ').strip()
        if original_name != name_to_translate:
            print(f"\n    Preprocess: '{original_name}' -> '{name_to_translate}'")
            
        payload = {
            "model": API_MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": TRANSLATION_PROMPT_TEMPLATE.format(name_to_translate)}
            ]
        }
        try:
            # --- Bug fix: use the json parameter so requests handles encoding automatically ---
            response = requests.post(API_URL, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            response_json = response.json()
            translated_text = response_json['choices'][0]['message']['content'].strip()
            final_translation = translated_text.split('\n')[0].strip()
            translated_names.append(final_translation)
        except Exception as e:
            print(f"\n    Translation failed for '{name_to_translate}': {e}. Using original name as placeholder.")
            translated_names.append(original_name)
            
        print_progress_bar(i + 1, total_names, prefix='    Translation progress:', suffix='Done', length=40)
        time.sleep(0.5)
        
    print("\n    All translation attempts completed.")
    with open(os.path.join(root_directory, "list-zh.txt"), 'w', encoding='utf-8') as f:
        for name in translated_names: f.write(name + '\n')
    print(f"    Successfully wrote translation results to: {os.path.join(root_directory, 'list-zh.txt')}")
    return translated_names

def rename_dirs_to_chinese(root_directory: str, original_names: list, translated_names: list) -> list:
    """Rename folders to Chinese names based on translation results, and return the list of successfully renamed names."""
    print(f"\n--- Step 3: Rename folders to Chinese based on translation results ---")
    if not original_names or not translated_names or len(original_names) != len(translated_names):
        print("    Error: Name lists are empty or counts do not match; aborting rename.")
        return []
    renamed_pairs = []
    successful_renames = []
    for original_name, new_name in zip(original_names, translated_names):
        original_path = os.path.join(root_directory, original_name)
        if original_name == new_name:
            print(f"    Skipped: translation equals original '{original_name}'")
            successful_renames.append(original_name)
            continue

        invalid_chars = r'[\\/*?:"<>|]'
        cleaned_new_name = "".join(c for c in new_name if c not in invalid_chars)
        new_path = os.path.join(root_directory, cleaned_new_name)
        
        if os.path.isdir(original_path):
            if not os.path.exists(new_path):
                try:
                    os.rename(original_path, new_path)
                    print(f"    Success: '{original_name}' -> '{cleaned_new_name}'")
                    successful_renames.append(cleaned_new_name)
                except Exception as e:
                    print(f"    Failed: Error renaming '{original_name}': {e}")
            else:
                print(f"    Skipped: target name '{cleaned_new_name}' already exists.")
                successful_renames.append(cleaned_new_name)
        else:
            print(f"    Skipped: original folder not found '{original_path}'.")

    print("    Chinese renaming completed.")
    return successful_renames

# ==============================================================================
# Module 3: Add pinyin prefix
# ==============================================================================
def add_pinyin_prefix_to_dirs(root_directory: str, dir_names: list) -> list:
    """Add first-letter pinyin prefix to the given Chinese folder names."""
    print(f"\n--- Step 4: Add pinyin first-letter prefix ---")
    if not dir_names:
        print("    No folders available to add prefix.")
        return []
    
    final_names = []
    renamed_count = 0
    error_count = 0
    
    print_progress_bar(0, len(dir_names), prefix='    Prefix addition progress:', suffix='Done', length=40)
    for i, original_name in enumerate(dir_names):
        if re.match(r'^[A-Z]-', original_name):
            print(f"\n    Skipped: '{original_name}' already has a prefix.")
            final_names.append(original_name)
            continue

        first_char_match = re.search(r'([\u4e00-\u9fff]|[A-Za-z])', original_name)
        if not first_char_match:
            print(f"\n    Warning: Cannot determine first letter for '{original_name}', skipping.")
            final_names.append(original_name)
            error_count += 1
            continue
        
        prefix = ''
        try:
            first_char = first_char_match.group(1)
            if '\u4e00' <= first_char <= '\u9fff':
                prefix = pinyin(first_char, style=Style.FIRST_LETTER)[0][0].upper()
            elif 'a' <= first_char.lower() <= 'z':
                prefix = first_char.upper()
        except Exception as e:
            print(f"\n    Failed to generate prefix for '{original_name}': {e}")
            prefix = 'X'
        
        if prefix:
            new_name_with_prefix = f"{prefix}-{original_name}"
            original_path = os.path.join(root_directory, original_name)
            new_path = os.path.join(root_directory, new_name_with_prefix)
            
            if os.path.isdir(original_path):
                if not os.path.exists(new_path):
                    try:
                        os.rename(original_path, new_path)
                        print(f"\n    Success: '{original_name}' -> '{new_name_with_prefix}'")
                        renamed_count += 1
                        final_names.append(new_name_with_prefix)
                    except Exception as e:
                        print(f"\n    Failed: Error adding prefix when renaming '{original_name}': {e}")
                        error_count += 1
                        final_names.append(original_name)
                else:
                    print(f"\n    Skipped: prefixed name '{new_name_with_prefix}' already exists.")
                    final_names.append(new_name_with_prefix)
            else:
                 final_names.append(original_name)
        else:
             final_names.append(original_name)
        
        print_progress_bar(i + 1, len(dir_names), prefix='    Prefix addition progress:', suffix='Done', length=40)

    print(f"\n    Prefix addition completed. Success: {renamed_count}, Failed/Skipped: {error_count}")
    return final_names

# ==============================================================================
# New Module 4: Clean up temporary files
# ==============================================================================
def cleanup_temp_files(root_directory: str):
    """Clean up temporary list.txt and list-zh.txt files generated during the process."""
    print(f"\n--- Step 5: Clean up temporary files ---")
    files_to_delete = ["list.txt", "list-zh.txt"]
    for filename in files_to_delete:
        file_path = os.path.join(root_directory, filename)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"    Deleted temporary file: {filename}")
            except OSError as e:
                print(f"    Failed to delete temporary file '{filename}': {e}")
        else:
            print(f"    Temporary file not found, no deletion needed: {filename}")

# ==============================================================================
# Main execution flow
# ==============================================================================
if __name__ == "__main__":
    print("File organization, translation, and renaming pipeline script")
    print("-" * 50)

    # --- Change: load all configuration dynamically ---
    default_path = load_settings_from_json()
    
    try:
        target_directory_input = input(f"Please enter the root directory path (default: {default_path}) and press Enter: ").strip()
        
        target_directory = target_directory_input if target_directory_input else default_path
        if not target_directory_input:
            print(f"    Using default path: {target_directory}")

        while not os.path.isdir(target_directory):
            print(f"Error: '{target_directory}' is not a valid directory path.")
            target_directory_input = input("Please re-enter the path, or press Enter to exit: ").strip()
            if not target_directory_input:
                print("No valid path entered, exiting script.")
                sys.exit()
            target_directory = target_directory_input

    except KeyboardInterrupt:
        print("\nOperation interrupted by user. Exiting script.")
        sys.exit()

    organize_files_into_subdirs(target_directory)
    original_folders = extract_folder_names_to_file(target_directory)

    if original_folders:
        translated_folders = translate_names_via_api(target_directory, original_folders)
        if translated_folders and len(original_folders) == len(translated_folders):
            renamed_to_chinese_folders = rename_dirs_to_chinese(target_directory, original_folders, translated_folders)
            if renamed_to_chinese_folders:
                add_pinyin_prefix_to_dirs(target_directory, renamed_to_chinese_folders)

    # --- New: call cleanup function ---
    cleanup_temp_files(target_directory)

    print("\nAll processes completed.")