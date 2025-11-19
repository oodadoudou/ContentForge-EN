import unittest
import sys
import os
import subprocess
from unittest.mock import patch, MagicMock

# Add project root to Python search path
# So test scripts can correctly import main and shared_utils
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_ROOT)

# Import target module to test
import main

class TestMainDispatcher(unittest.TestCase):

    @patch('main.utils.get_input')
    @patch('subprocess.run')
    def test_menu_navigation(self, mock_subprocess_run, mock_get_input):
        """
        Test whether all main menu navigation options correctly invoke the corresponding submodule entry scripts.
        """
        
        # Define main menu options, descriptions, and expected script paths
        menu_actions = {
            '1': ('Content Acquisition (Download comics from websites)', '01_acquisition/01_start_up.py'),
            '2': ('Comic Processing & Generation (Images to PDF)', '02_comic_processing/02_start_up.py'),
            '3': ('E-book Processing & Generation (TXT/EPUB/HTML)', '03_ebook_workshop/03_start_up.py'),
            '4': ('File Repair & Tools (Resolve common issues)', '04_file_repair/04_start_up.py'),
            '5': ('Library Organization (Organize, archive, rename)', '05_library_organization/05_start_up.py'),
        }

        for choice, (description, expected_script) in menu_actions.items():
            # Reset mocks for each iteration
            mock_subprocess_run.reset_mock()
            
            # Simulate user input: enter only the menu option, then StopIteration ends the test
            mock_get_input.side_effect = [choice]

            print(f"\n--- Testing menu option '{choice}': {description} ---")
            print(f"  [Mock] User input: '{choice}'")
            
            # Use a mocked main loop to execute a single selection
            # Assume after selecting a module the program returns to main menu; simulate via exception capture
            with self.assertRaises(StopIteration): # get_input raises after side_effect list is exhausted
                main.main()

            # Verify subprocess.run was invoked
            print(f"  [Verify] Attempt to call subprocess.run...")
            self.assertTrue(mock_subprocess_run.called, f"Option '{choice}' did not trigger any script call!")
            print(f"    - Call succeeded.")
            
            # Get call arguments
            call_args, _ = mock_subprocess_run.call_args
            
            # call_args[0] is a list, e.g., [sys.executable, 'path/to/script.py']
            called_script_path = call_args[0][1]
            
            # Construct expected absolute script path
            expected_abs_path = os.path.join(PROJECT_ROOT, expected_script)
            
            print(f"  [Verify] Was the called script: {expected_script}")
            # Assert called script path equals expected path
            self.assertEqual(called_script_path, expected_abs_path, 
                             f"Option '{choice}' invoked wrong script!\n"
                             f"  Expected: {expected_abs_path}\n"
                             f"  Actual: {called_script_path}")
            print(f"    - Path match succeeded.")
            
            print(f"  ✅ Test passed!")
    
    @patch('main.menu_system_settings')
    @patch('main.utils.get_input')
    def test_settings_menu_call(self, mock_get_input, mock_settings_menu):
        """Test whether selecting '6' correctly calls the settings menu function."""
        mock_get_input.side_effect = ['6']
        
        print(f"\n--- Testing menu option '6': System Settings & Dependencies ---")
        print(f"  [Mock] User input: '6'")

        with self.assertRaises(StopIteration):
            main.main()
            
        print(f"  [Verify] Was function `main.menu_system_settings` invoked...")
        self.assertTrue(mock_settings_menu.called, "Option '6' failed to call menu_system_settings!")
        print(f"    - Call succeeded.")

        print("  ✅ Test passed!")


# This allows running this file directly from the command line
if __name__ == '__main__':
    # Mock initial run configuration in main so it doesn't execute
    with patch('main.configure_default_path'):
        # Use verbosity=2 for detailed output from unittest framework
        unittest.main(verbosity=2)
