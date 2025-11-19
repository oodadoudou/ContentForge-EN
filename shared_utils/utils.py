import os
import sys
import json
import shlex
import subprocess

# =================================================================
#                 Global Paths & Configuration
# =================================================================

# Define project root to base all path operations
try:
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
except NameError:
    PROJECT_ROOT = os.path.dirname(os.getcwd())

# Define absolute paths for shared assets and settings file
SHARED_ASSETS_PATH = os.path.join(PROJECT_ROOT, "shared_assets")
SETTINGS_FILE_PATH = os.path.join(SHARED_ASSETS_PATH, "settings.json")

# Global settings variable
settings = {}

# =================================================================
#                 General Helper Functions
# =================================================================

def clear_screen():
    """Clear the terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header(title):
    """Print a header separator with title"""
    clear_screen()
    print("=" * 60)
    print(f"{title:^60}")
    print("=" * 60)

def run_script(command, cwd="."):
    """
    Unified script execution function.
    :param command: Script name or command to execute.
    :param cwd: Working directory when executing (relative to PROJECT_ROOT).
    """
    absolute_cwd = os.path.join(PROJECT_ROOT, cwd)
    try:
        # shlex.split properly handles paths and arguments with spaces
        args = [sys.executable] + shlex.split(command)
        print(f"\n▶️  Executing: {' '.join(args)}")
        print(f"   Working directory: {os.path.abspath(absolute_cwd)}")
        print("-" * 60)
        process = subprocess.Popen(args, cwd=absolute_cwd)
        process.wait()
    except FileNotFoundError:
        print(f"❌ Error: Script '{command.split()[0]}' not found")
    except Exception as e:
        print(f"❌ Unknown error occurred while executing script: {e}")
    
    print("-" * 60)
    input("Press Enter to return to menu...")

def get_input(prompt, default=None):
    """Get user input, with default value support"""
    if default is not None:
        return input(f"{prompt} (default: {default}): ") or default
    else:
        return input(f"{prompt}: ")

def show_usage(module_path):
    """Read and display module usage (README.md)"""
    readme_path = os.path.join(PROJECT_ROOT, module_path, 'README.md')
    try:
        with open(readme_path, 'r', encoding='utf-8') as f:
            print_header(f"Module Usage: {os.path.basename(module_path)}")
            print(f.read())
            print("=" * 60)
            input("Press Enter to return to menu...")
    except FileNotFoundError:
        print(f"ℹ️  README.md usage for module '{module_path}' not found.")
        input("Press Enter to return to menu...")

def load_settings():
    """Load global settings"""
    global settings
    if os.path.exists(SETTINGS_FILE_PATH):
        try:
            with open(SETTINGS_FILE_PATH, 'r', encoding='utf-8') as f:
                settings = json.load(f)
        except (json.JSONDecodeError, IOError):
            settings = {}
    else:
        settings = {}

    # Ensure basic structure exists to avoid downstream errors
    if 'default_work_dir' not in settings:
        settings['default_work_dir'] = os.path.join(os.path.expanduser('~'), 'Downloads')
    if 'ai_config' not in settings:
        settings['ai_config'] = {
            'api_key': 'YOUR_API_KEY',
            'base_url': 'YOUR_API_BASE_URL',
            'model_name': 'YOUR_MODEL_NAME'
        }
    return settings

def save_settings():
    """Save global settings"""
    try:
        os.makedirs(SHARED_ASSETS_PATH, exist_ok=True)
        with open(SETTINGS_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=4, ensure_ascii=False)
        return True
    except IOError as e:
        print(f"\n❌ Failed to save settings: {e}")
        return False
        