import os
import sys
import subprocess

# =================================================================
#                 全局变量与路径设置
# =================================================================

# --- FIX: 将项目根目录添加到Python搜索路径中，以便能导入共享工具 ---
try:
    # 获取脚本文件所在的目录
    PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
except NameError:
    # 兼容在某些交互式环境中 __file__ 未定义的情况
    PROJECT_ROOT = os.getcwd()

# 将项目根目录添加到sys.path
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

# --- NEW: 从共享模块导入所有工具函数 ---
from shared_utils import utils


# =================================================================
#                 系统设置相关函数
# =================================================================

def configure_default_path(first_time=False):
    """交互式配置默认工作目录"""
    if first_time:
        utils.print_header("First Run Setup")
        print("Welcome to ContentForge! This is a powerful content processing toolkit.")
        print("For convenience, please set a default working directory first.")
        print("For example: 'D:\\Downloads' or '/Users/YourName/Documents'")
        print("All modules will use this directory as the default when a path is required.")
    else:
        utils.print_header("Configure Default Working Directory")
    
    current_path = utils.settings.get('default_work_dir', 'Not set')
    
    while True:
        new_path = utils.get_input("Please enter your default working directory path", default=current_path)
        if os.path.isdir(new_path):
            utils.settings['default_work_dir'] = new_path
            if utils.save_settings():
                print(f"\n✅ Default working directory updated to: {new_path}")
            break
        else:
            print(f"❌ Error: Path '{new_path}' is not a valid directory. Please re-enter.")
    
    if not first_time:
        input("\nPress Enter to return to the settings menu...")


def manage_ai_config():
    """交互式地加载、显示、更新AI配置"""
    utils.print_header("AI Translation Configuration")
    config = utils.settings.get('ai_config', {})
    print("Current AI configuration:")
    print(f"  API Key: {config.get('api_key', 'Not set')}")
    print(f"  Base URL: {config.get('base_url', 'Not set')}")
    print(f"  Model Name: {config.get('model_name', 'Not set')}")
    print("-" * 60)

    if utils.get_input("Modify configuration? (Press Enter to confirm, enter n to cancel): ").lower() != 'n':
        api_key = utils.get_input("Enter new API Key", config.get('api_key'))
        base_url = utils.get_input("Enter new Base URL", config.get('base_url'))
        model_name = utils.get_input("Enter new Model Name", config.get('model_name'))
        utils.settings['ai_config'] = {
            'api_key': api_key,
            'base_url': base_url,
            'model_name': model_name
        }
        utils.save_settings()
        print("✅ AI configuration updated.")


def menu_install_dependencies():
    """一键安装/更新依赖，优化了跨平台兼容性和错误提示"""
    utils.print_header("Install/Update Project Dependencies")
    
    requirements_path = os.path.join(utils.PROJECT_ROOT, 'requirements.txt')

    if not os.path.exists(requirements_path):
        print(f"❌ Error: 'requirements.txt' not found in the project root.")
        input("Press Enter to return...")
        return
        
    print(f"pip will install all dependencies listed in '{requirements_path}'.")
    if utils.get_input("Continue? (Press Enter to confirm, enter n to cancel): ").lower() != 'n':
        try:
            command = [sys.executable, "-m", "pip", "install", "-r", requirements_path]
            print(f"\n▶️  Executing: {' '.join(command)}")
            print("-" * 60)
            result = subprocess.run(command, check=True, capture_output=True, text=True, encoding='utf-8')
            print(result.stdout)
            print("\n✅ Dependencies installed successfully!")

        except subprocess.CalledProcessError as e:
            print("\n❌ Automatic dependency installation failed.")
            print("="*20 + " Error Details " + "="*20)
            print(e.stderr)
            print("="*52)
            print("\nPlease try running one of the following commands manually in your terminal:")
            print("\n[Recommended] Option 1 (most reliable):")
            print(f"   python -m pip install -r \"{requirements_path}\"")
            print("\nOption 2 (if Option 1 doesn't work):")
            print(f"   pip install -r \"{requirements_path}\"")
            print("\nIf the issue persists, please check your Python and pip environment configuration.")
            
        except FileNotFoundError:
            print("\n❌ Error: 'python' or 'pip' command not found. Please ensure Python is installed and added to your system PATH.")
        except Exception as e:
            print(f"\n❌ Unknown error occurred: {e}")
    
    input("\nPress Enter to return to the menu...")

def menu_system_settings():
    """模块六: 系统设置与依赖"""
    while True:
        utils.print_header("6. System Settings & Dependencies")
        print(" 1. Configure default working directory")
        print(" 2. Configure AI Translation API")
        print(" 3. Install/Update project dependencies (pip)")
        print(" 0. Return to main menu")
        choice = utils.get_input("Please select")

        if choice == '1':
            configure_default_path()
        elif choice == '2':
            manage_ai_config()
            input("\nPress Enter to return...")
        elif choice == '3':
            menu_install_dependencies()
        elif choice == '0':
            break

# =================================================================
#                         主函数
# =================================================================

def main():
    """主函数，显示主菜单并调用子模块入口。"""
    
    settings_path = os.path.join(PROJECT_ROOT, 'shared_assets', 'settings.json')

    if not os.path.exists(settings_path):
        configure_default_path(first_time=True)
    
    utils.load_settings()

    if not os.path.isdir(utils.settings.get('default_work_dir', '')):
        print("\nWarning: The default working directory in the configuration is invalid or not set.")
        configure_default_path(first_time=False)

    main_menu = {
        '1': ('Content Acquisition (Download comics from websites)', '01_acquisition/01_start_up.py'),
        '2': ('Comic Processing & Generation (Images to PDF)', '02_comic_processing/02_start_up.py'),
        '3': ('eBook Processing & Generation (TXT/EPUB/HTML)', '03_ebook_workshop/03_start_up.py'),
        '4': ('File Repair & Tools (Common issues)', '04_file_repair/04_start_up.py'),
        '5': ('Library Management (Organize, archive, rename)', '05_library_organization/05_start_up.py'),
        '6': ('System Settings & Dependencies', menu_system_settings),
        '7': ('Universal Downloader', '07_downloader/07_start_up.py'),
        '0': ('Exit', lambda: sys.exit(0))
    }

    while True:
        utils.print_header("Welcome to ContentForge Main Menu")
        sorted_items = sorted(main_menu.items(), key=lambda item: float('inf') if item[0] == '0' else int(item[0]))
        
        for key, (text, _) in sorted_items:
            if key != '0':
                print(f" {key}. {text}")
        print(" 0. Exit")

        choice = utils.get_input("Please select a module")
        
        if choice in main_menu:
            action = main_menu[choice][1]
            if isinstance(action, str):
                script_path = os.path.join(PROJECT_ROOT, action)
                subprocess.run([sys.executable, script_path], cwd=PROJECT_ROOT)
            else:
                if choice == '0':
                     print("\n\nThank you for using ContentForge! (｡･ω･｡)ﾉ♡")
                action()
        else:
            print("Invalid input, please try again.")
            input("Press Enter to continue...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nThank you for using ContentForge! (｡･ω･｡)ﾉ♡")
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
    except Exception as e:
        print(f"\nUnexpected top-level error: {e}")
        sys.exit(1)