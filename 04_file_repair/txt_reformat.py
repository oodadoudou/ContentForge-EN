import os
import re
import sys
import json

def fix_novel_text_file(input_path, output_path):
    """
    Read a TXT file and format so each line is followed by an empty line.
    - Addresses split paired symbols (such as quotes) issues.
    - Simplified approach: only add a blank line after each content line.
    """
    try:
        print(f"Reading file: {os.path.basename(input_path)} ...")
        
        # Try UTF-8 first; fallback to GBK on decode error
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except UnicodeDecodeError:
            with open(input_path, 'r', encoding='gbk', errors='ignore') as f:
                lines = f.readlines()

        processed_lines = []
        for line in lines:
            # Strip leading/trailing whitespace (including newline) and check if line has content
            stripped_line = line.strip()
            if stripped_line:
                # If not empty, append an extra blank line (two newlines)
                processed_lines.append(stripped_line + '\n\n')
        
        # Join processed lines into a single string
        final_text = "".join(processed_lines)

        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            # Use rstrip() to remove potentially extra trailing blank lines
            f.write(final_text.rstrip())
            
        print(f"Processing complete; saved to: {os.path.basename(output_path)}")

    except FileNotFoundError:
        print(f"Error: File not found - {input_path}", file=sys.stderr)
    except Exception as e:
        print(f"Error occurred while processing file {input_path}: {e}", file=sys.stderr)

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
    Main function: get user input and process a single file or entire directory.
    """
    # --- Change: dynamically load default path ---
    default_path = load_default_path_from_settings()
    user_path = input(f"Enter the TXT file or directory path (Press Enter to use default: {default_path}): ").strip()
    
    if not user_path:
        user_path = default_path
        print(f"No path entered; using default: {user_path}")

    # Validate path exists
    if not os.path.exists(user_path):
        print(f"Error: Path '{user_path}' does not exist.", file=sys.stderr)
        return

    # Case 1: path is a directory
    if os.path.isdir(user_path):
        input_dir = user_path
        output_dir = os.path.join(input_dir, "processed_files")
        print(f"Detected directory; processing all .txt files within.")
        print(f"Output directory set to: '{output_dir}'")
        
        file_count = 0
        for filename in os.listdir(input_dir):
            if filename.lower().endswith(".txt"):
                file_count += 1
                input_filepath = os.path.join(input_dir, filename)
                output_filename = os.path.splitext(filename)[0] + '_reformatted.txt'
                output_filepath = os.path.join(output_dir, output_filename)
                fix_novel_text_file(input_filepath, output_filepath)
        
        if file_count == 0:
            print(f"No .txt files found in directory '{input_dir}'.")
        else:
            print(f"\nAll {file_count} .txt files processed!")

    # Case 2: path is a single file
    elif os.path.isfile(user_path):
        if user_path.lower().endswith(".txt"):
            input_filepath = user_path
            base_dir = os.path.dirname(input_filepath)
            output_dir = os.path.join(base_dir, "processed_files")
            
            print(f"Detected single file; preparing to process.")
            print(f"Output directory set to: '{output_dir}'")

            output_filename = os.path.splitext(os.path.basename(input_filepath))[0] + '_reformatted.txt'
            output_filepath = os.path.join(output_dir, output_filename)
            fix_novel_text_file(input_filepath, output_filepath)
            print("\nFile processed!")
        else:
            print(f"Error: '{user_path}' is a file but not a .txt file.", file=sys.stderr)
            
    else:
        print(f"Error: '{user_path}' is not a valid file or directory.", file=sys.stderr)


if __name__ == "__main__":
    main()