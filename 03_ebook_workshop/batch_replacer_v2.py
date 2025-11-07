import pandas as pd
import re
import os
import warnings
import tempfile
import zipfile
import shutil
from pathlib import Path
from ebooklib import epub, ITEM_DOCUMENT, ITEM_STYLE
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
from tqdm import tqdm
import html
import sys
import json

# --- Suppress known warnings ---
warnings.filterwarnings("ignore", category=UserWarning, module='ebooklib')
warnings.filterwarnings("ignore", category=FutureWarning, module='ebooklib')
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

# --- Constants ---
PROCESSED_DIR_NAME = "processed_files"
REPORT_DIR_NAME = "compare_reference"
HIGHLIGHT_STYLE = "background-color: #f1c40f; color: #000; padding: 2px; border-radius: 3px;"

def find_rules_file(directory: Path) -> Path:
    """Find the rules.txt file in the specified directory."""
    rules_files = list(directory.glob('rules.txt'))
    if rules_files:
        return rules_files[0]
    return None

def load_rules(rules_file: Path) -> pd.DataFrame:
    """Load replacement rules; supports .txt format only."""
    print(f"[*] Loading replacement rules from {rules_file.name}...")
    rules_list = []
    try:
        with open(rules_file, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                match = re.match(r'^(.*?)\s*->\s*(.*?)\s*\(Mode:\s*(Text|Regex)\s*\)$', line, re.IGNORECASE)
                
                if not match:
                    match_no_replacement = re.match(r'^(.*?)\s*->\s*\(Mode:\s*(Text|Regex)\s*\)$', line, re.IGNORECASE)
                    if match_no_replacement:
                        original, mode = match_no_replacement.groups()
                        replacement = ""
                    else:
                        print(f"[!] Warning: Rule format invalid at line {i}; ignored: \"{line}\"")
                        continue
                else:
                    original, replacement, mode = match.groups()

                rules_list.append({
                    'Original': original.strip(),
                    'Replacement': replacement.strip(),
                    'Mode': mode.strip().capitalize()
                })
        
        df = pd.DataFrame(rules_list)
        
        if df.empty:
            print("[!] Warning: Rules file is empty or all rules are invalid.")
        
        return df

    except Exception as e:
        print(f"[!] Failed to load rules file: {e}")
        exit(1)

def process_and_get_changes(content: str, rules: pd.DataFrame) -> tuple[str, list]:
    """
    Core processing: apply all replacements to plain text.
    Returns a tuple: (modified_text, atomic_change_list)
    Atomic changes: [{'original_text': '...','replacement_text': '...'}]
    """
    modified_content = content
    atomic_changes = []

    for _, rule in rules.iterrows():
        original, replacement, mode = rule['Original'], rule['Replacement'], rule['Mode']
        if pd.isna(original) or original == "" or original == "nan":
            continue
        
        search_pattern = re.escape(original) if mode.lower() == 'text' else original
        
        try:
            # Always search on the latest modified string to handle chained replacements
            matches = list(re.finditer(search_pattern, modified_content))
            if matches:
                # Record each matched original and the replacement text it becomes
                for match in matches:
                    atomic_changes.append({
                        "original_text": match.group(0),
                        "replacement_text": match.expand(replacement)
                    })
                # Apply the replacement for this rule
                modified_content = re.sub(search_pattern, replacement, modified_content)
        except re.error as e:
            print(f"\n[!] Regex error: '{search_pattern}'. Error: {e}. Skipped.")
            continue

    unique_atomic_changes = [dict(t) for t in {tuple(d.items()) for d in atomic_changes}]
    return modified_content, unique_atomic_changes

def generate_report(report_path: Path, changes_log: list, source_filename: str):
    """Generate an HTML change report."""
    if not changes_log:
        print(f"[!] No change records; skipping report generation: {report_path}")
        return
    
    # 获取项目根目录和模板路径
    project_root = Path(__file__).parent.parent
    template_path = project_root / 'shared_assets' / 'report_template.html'
    
    if not template_path.exists():
        print(f"[!] Template file does not exist: {template_path}")
        return
    
    # 计算从报告文件到shared_assets的相对路径
    report_dir = report_path.parent
    shared_assets_dir = project_root / 'shared_assets'
    try:
        relative_path = os.path.relpath(shared_assets_dir, report_dir)
        css_path = f"{relative_path}/report_styles.css".replace('\\', '/')
        js_path = f"{relative_path}/report_scripts.js".replace('\\', '/')
    except ValueError:
        # If relative path cannot be computed, use default paths
        css_path = "shared_assets/report_styles.css"
        js_path = "shared_assets/report_scripts.js"
    
    # Group by replacement rules
    rule_groups = {}
    for change in changes_log:
        # Extract highlighted original and replacement text
        original_match = re.search(r'<span class="highlight">([^<]+)</span>', change['original'])
        modified_match = re.search(r'<span class="highlight">([^<]+)</span>', change['modified'])
        
        if original_match and modified_match:
            original_text = original_match.group(1)
            replacement_text = modified_match.group(1)
            rule_key = f"{original_text} → {replacement_text}"
            
            if rule_key not in rule_groups:
                rule_groups[rule_key] = {
                    'original_text': original_text,
                    'replacement_text': replacement_text,
                    'instances': []
                }
            
            rule_groups[rule_key]['instances'].append(change)
    
    # Sort by number of instances
    sorted_rule_groups = sorted(rule_groups.values(), key=lambda x: len(x['instances']), reverse=True)
    total_instances = sum(len(group['instances']) for group in sorted_rule_groups)
    
    # Read template file
    template_content = template_path.read_text(encoding='utf-8')
    
    # Generate rules list items
    rules_list_items = ""
    for i, group in enumerate(sorted_rule_groups):
        rules_list_items += f'''
                    <div class="rule-list-item" onclick="jumpToRule({i})">
                        <div class="rule-text">
                            <span class="rule-original">{html.escape(group["original_text"])}</span> → 
                            <span class="rule-replacement">{html.escape(group["replacement_text"])}</span>
                        </div>
                        <div class="rule-count">{len(group["instances"])} times</div>
                    </div>
        '''
    
    # Generate content sections
    content_sections = ""
    for group_index, group in enumerate(sorted_rule_groups):
        instance_count = len(group['instances'])
        content_sections += f'''
            <div class="rule-group" data-group-index="{group_index}">
                <div class="rule-header" onclick="toggleInstances({group_index})">
                    <div class="rule-title">
                        <span class="rule-badge">{instance_count} times</span>
                        <span class="toggle-icon" id="toggle-{group_index}">▼</span>
                    </div>
                    <div class="rule-description">
                        <span><strong>{html.escape(group['original_text'])}</strong></span>
                        <span class="rule-arrow">→</span>
                        <span><strong>{html.escape(group['replacement_text'])}</strong></span>
                    </div>
                </div>
                <div class="instances-container" id="instances-{group_index}">
        '''
        
        # Sort instances by position
        sorted_instances = sorted(group['instances'], key=lambda x: x.get('position', 0))
        
        for instance in sorted_instances:
            content_sections += f'''
                    <div class="instance-item">
                        <div class="instance-content">
                            <div class="original-section">
                                <div class="section-title">Original</div>
                                <div class="text-content">{instance['original']}</div>
                            </div>
                            <div class="modified-section">
                                <div class="section-title">Modified</div>
                                <div class="text-content">{instance['modified']}</div>
                            </div>
                        </div>
                    </div>
            '''
        
        content_sections += '''
                </div>
            </div>
        '''
    
    # Replace placeholders in template
    html_content = template_content.replace('{{source_filename}}', html.escape(source_filename))
    html_content = html_content.replace('{{rules_count}}', str(len(sorted_rule_groups)))
    html_content = html_content.replace('{{total_instances}}', str(total_instances))
    html_content = html_content.replace('{{rules_list_items}}', rules_list_items)
    html_content = html_content.replace('{{content_sections}}', content_sections)
    html_content = html_content.replace('{{generation_time}}', html.escape(str(__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S'))))
    
    # Replace CSS and JS paths
    html_content = html_content.replace('href="shared_assets/report_styles.css"', f'href="{css_path}"')
    html_content = html_content.replace('src="shared_assets/report_scripts.js"', f'src="{js_path}"')
    
    try:
        report_path.write_text(html_content, encoding='utf-8')
        print(f"[✓] Report generated: {report_path}")
    except Exception as e:
        print(f"[!] Unable to write report file {report_path}: {e}")

def process_txt_file(file_path: Path, rules: pd.DataFrame, processed_dir: Path, report_dir: Path):
    """Process a single .txt file."""
    replacement_count = 0
    try:
        content = file_path.read_text(encoding='utf-8')
        paragraphs = content.split('\n\n')
        processed_paragraphs = []
        changes_log_for_report = []
        file_was_modified = False
        current_position = 0

        for paragraph_index, p_original in enumerate(paragraphs):
            p_modified, atomic_changes = process_and_get_changes(p_original, rules)
            processed_paragraphs.append(p_modified)

            if atomic_changes:
                file_was_modified = True
                replacement_count += len(atomic_changes)
                original_report = html.escape(p_original)
                modified_report = html.escape(p_modified)

                for change in atomic_changes:
                    orig_esc = html.escape(change["original_text"])
                    repl_esc = html.escape(change["replacement_text"])
                    original_report = original_report.replace(orig_esc, f'<span class="highlight">{orig_esc}</span>')
                    modified_report = modified_report.replace(repl_esc, f'<span class="highlight">{repl_esc}</span>')
                
                changes_log_for_report.append({
                    'original': original_report.replace('\n', '<br>'),
                    'modified': modified_report.replace('\n', '<br>'),
                    'position': current_position + paragraph_index
                })
            
            current_position += len(p_original) + 2

        if file_was_modified:
            new_content = "\n\n".join(processed_paragraphs)
            processed_file_path = processed_dir / file_path.name
            processed_file_path.write_text(new_content, encoding='utf-8')
            report_path = report_dir / f"{file_path.name}.html"
            generate_report(report_path, changes_log_for_report, file_path.name)
            return {'modified': True, 'replacement_count': replacement_count, 'css_fixed': False, 'error': None}

    except Exception as e:
        print(f"\n[!] Failed to process TXT file {file_path.name}: {e}")
        return {'modified': False, 'replacement_count': 0, 'css_fixed': False, 'error': str(e)}
    return {'modified': False, 'replacement_count': 0, 'css_fixed': False, 'error': None}

def process_epub_file(file_path: Path, rules: pd.DataFrame, processed_dir: Path, report_dir: Path):
    """Process EPUB with two-phase workflow: 1) text replacement, 2) CSS link fix."""
    
    changes_log = []
    book_is_modified = False
    global_position = 0
    replacement_count = 0
    
    try:
        # Phase 1: Use BeautifulSoup for text replacement
        book = epub.read_epub(str(file_path))
        
        for item in book.get_items():
            if item.get_type() == ITEM_DOCUMENT:
                content = item.get_content().decode('utf-8')
                soup = BeautifulSoup(content, 'xml')
                item_is_modified = False
                
                if not soup.body:
                    continue
                
                for p_tag in soup.body.find_all('p'):
                    if not p_tag.get_text(strip=True):
                        continue

                    p_text_original = p_tag.get_text()
                    p_text_modified, atomic_changes = process_and_get_changes(p_text_original, rules)

                    if atomic_changes:
                        book_is_modified = True
                        item_is_modified = True
                        replacement_count += len(atomic_changes)
                        
                        p_tag.string = p_text_modified

                        original_report = html.escape(p_text_original)
                        modified_report = html.escape(p_text_modified)

                        for change in atomic_changes:
                            orig_esc = html.escape(change["original_text"])
                            repl_esc = html.escape(change["replacement_text"])
                            original_report = original_report.replace(orig_esc, f'<span class="highlight">{orig_esc}</span>')
                            modified_report = modified_report.replace(repl_esc, f'<span class="highlight">{repl_esc}</span>')
                        
                        changes_log.append({
                            'original': original_report.replace('\n', '<br>'),
                            'modified': modified_report.replace('\n', '<br>'),
                            'position': global_position
                        })
                    
                    global_position += len(p_text_original)

                # 如果文件被修改，更新item内容
                if item_is_modified:
                    item.set_content(str(soup).encode('utf-8'))

        # Save EPUB after phase 1 fix
        temp_epub_path = processed_dir / f"temp_{file_path.name}"
        if book_is_modified:
            # Ensure EPUB has required identifier metadata
            if not book.get_metadata('DC', 'identifier'):
                # If no identifier, add a default one
                import uuid
                default_identifier = f"urn:uuid:{uuid.uuid4()}"
                book.add_metadata('DC', 'identifier', default_identifier)
            
            epub.write_epub(str(temp_epub_path), book, {})
        else:
            # If not modified, copy original as temp file
            shutil.copy2(file_path, temp_epub_path)
        
        # Phase 2: Fix CSS links
        css_fixed = fix_css_links_in_epub(temp_epub_path, file_path)
        
        if css_fixed:
            book_is_modified = True
        
        # Move final file to destination
        final_epub_path = processed_dir / file_path.name
        if temp_epub_path.exists():
            shutil.move(str(temp_epub_path), str(final_epub_path))
        
        # Generate report
        if book_is_modified and changes_log:
            unique_changes = [dict(t) for t in {tuple(d.items()) for d in changes_log}]
            report_path = report_dir / f"{file_path.name}.html"
            generate_report(report_path, unique_changes, file_path.name)
        
        return {'modified': book_is_modified, 'replacement_count': replacement_count, 'css_fixed': css_fixed, 'error': None}

    except Exception as e:
        print(f"\n[!] Failed to process EPUB file {file_path.name}: {e}")
        # Clean temp file
        temp_epub_path = processed_dir / f"temp_{file_path.name}"
        if temp_epub_path.exists():
            temp_epub_path.unlink()
        return {'modified': False, 'replacement_count': 0, 'css_fixed': False, 'error': str(e)}


def fix_css_links_in_epub(epub_path, original_epub_path):
    """Fix CSS links inside an EPUB file."""
    
    # Create temp directories
    temp_dir = epub_path.parent / f"css_fix_temp_{epub_path.stem}"
    original_temp_dir = epub_path.parent / f"original_temp_{epub_path.stem}"
    
    css_was_fixed = False
    
    try:
        # Unpack fixed EPUB
        temp_dir.mkdir(exist_ok=True)
        with zipfile.ZipFile(epub_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        # Unpack original EPUB
        original_temp_dir.mkdir(exist_ok=True)
        with zipfile.ZipFile(original_epub_path, 'r') as zip_ref:
            zip_ref.extractall(original_temp_dir)
        
        # Find all HTML/XHTML files
        html_files = []
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                if file.endswith(('.html', '.xhtml')):
                    html_files.append(os.path.join(root, file))
        
        # Process each HTML file
        for html_file_path in html_files:
            # Read fixed file content
            with open(html_file_path, 'r', encoding='utf-8') as f:
                fixed_content = f.read()
            
            # Find the corresponding original file
            relative_path = os.path.relpath(html_file_path, temp_dir)
            original_file_path = original_temp_dir / relative_path
            
            if original_file_path.exists():
                with open(original_file_path, 'r', encoding='utf-8') as f:
                    original_content = f.read()
                
                # Check if original file has CSS links
                original_css_links = re.findall(r'<link[^>]*href=["\']([^"\'>]*\.css)["\'][^>]*>', original_content, re.IGNORECASE)
                
                if original_css_links:

                    # Check whether fixed file misses any CSS links
                    missing_links = []
                    for css_link in original_css_links:
                        if css_link not in fixed_content:
                            missing_links.append(css_link)
                    
                    if missing_links:
                        
                        # Extract full head tag from original
                        original_head_match = re.search(r'<head[^>]*>.*?</head>', original_content, re.DOTALL | re.IGNORECASE)
                        if original_head_match:
                            original_head_content = original_head_match.group(0)
                            
                            # Find head tag in fixed file and replace
                            fixed_head_match = re.search(r'<head[^>]*>.*?</head>', fixed_content, re.DOTALL | re.IGNORECASE)
                            if fixed_head_match:
                                fixed_content = fixed_content.replace(fixed_head_match.group(0), original_head_content)
                                css_was_fixed = True
                            else:
                                # Handle self-closing head tag
                                head_self_closing_match = re.search(r'<head\s*\/>', fixed_content, re.IGNORECASE)
                                if head_self_closing_match:
                                    fixed_content = fixed_content.replace(head_self_closing_match.group(0), original_head_content)
                                    css_was_fixed = True
                            
                            # Save fixed file
                            if css_was_fixed:
                                with open(html_file_path, 'w', encoding='utf-8') as f:
                                    f.write(fixed_content)
        
        # Repack EPUB if CSS was fixed
        if css_was_fixed:
            # Delete original EPUB file
            epub_path.unlink()
            
            # Create EPUB again
            with zipfile.ZipFile(epub_path, 'w', zipfile.ZIP_DEFLATED) as zip_ref:
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arc_name = os.path.relpath(file_path, temp_dir)
                        zip_ref.write(file_path, arc_name)
        
    except Exception as e:
        print(f"[!] CSS link fix failed: {e}")
    finally:
        # Clean temp directories
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        if original_temp_dir.exists():
            shutil.rmtree(original_temp_dir)
    
    return css_was_fixed

def load_default_path_from_settings():
    """Read the default work directory from the shared settings file."""
    try:
        # Navigate up two levels to reach the project root
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        settings_path = os.path.join(project_root, 'shared_assets', 'settings.json')
        with open(settings_path, 'r', encoding='utf-8') as f:
            settings = json.load(f)
        # If "default_work_dir" exists and is non-empty, return it
        default_dir = settings.get("default_work_dir")
        return default_dir if default_dir else "."
    except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
        print(f"Warning: Failed to read settings.json ({e}); using 'Downloads' in the user home as fallback.")
        # Provide a generic fallback path
        return os.path.join(os.path.expanduser("~"), "Downloads")

def main():
    """Main function"""
    # 动态加载默认路径
    default_path = load_default_path_from_settings()
    
    prompt_message = (
        f"Please enter the folder path containing source files and rules.\n"
        f"(Press Enter to use the default path '{default_path}'): "
    )
    user_input = input(prompt_message)

    if not user_input.strip():
        directory_path = default_path
        print(f"[*] No input provided; using default path: {directory_path}")
    else:
        directory_path = user_input.strip()

    base_dir = Path(directory_path)
    if not base_dir.is_dir():
        print(f"[!] Error: Folder '{base_dir}' does not exist.")
        return

    processed_dir = base_dir / PROCESSED_DIR_NAME
    report_dir = base_dir / REPORT_DIR_NAME
    processed_dir.mkdir(exist_ok=True)
    report_dir.mkdir(exist_ok=True)

    print(f"[*] Working directory: {base_dir}")
    print(f"[*] Output folders ready:\n    - Processed files: {processed_dir}\n    - Change reports: {report_dir}")

    rules_file = find_rules_file(base_dir)
    if not rules_file:
        print("[!] Error: No 'rules.txt' rules file found in the specified folder.")
        return
    
    print("[*] Loading replacement rules from rules.txt...")
    rules = load_rules(rules_file)

    if rules.empty:
        print("[!] Rules are empty; no replacements performed.")
        return

    all_target_files = list(base_dir.glob('*.txt')) + list(base_dir.glob('*.epub'))
    files_to_process = [f for f in all_target_files if f.resolve() != rules_file.resolve()]

    if not files_to_process:
        print("[!] No .txt or .epub files found in the specified folder.")
        return

    print(f"[+] Successfully loaded {len(rules)} rules.")
    print(f"[*] Found {len(files_to_process)} files to process.")
    print()

    # 收集处理统计信息
    processing_results = []
    modified_count = 0
    
    with tqdm(total=len(files_to_process), desc="Processing progress", unit="file(s)") as pbar:
        for file_path in files_to_process:
            pbar.set_postfix_str(file_path.name, refresh=True)
            
            if file_path.suffix == '.txt':
                result = process_txt_file(file_path, rules, processed_dir, report_dir)
            elif file_path.suffix == '.epub':
                result = process_epub_file(file_path, rules, processed_dir, report_dir)
            else:
                result = {'modified': False, 'replacement_count': 0, 'css_fixed': False, 'error': 'Unsupported file type'}
            
            # 添加文件信息到结果中
            result['filename'] = file_path.name
            result['file_type'] = file_path.suffix.upper()[1:]  # 去掉点号并转大写
            processing_results.append(result)
            
            if result['modified']:
                modified_count += 1
            
            pbar.update(1)

    # 以表格形式显示处理结果
    print("\n" + "="*80)
    print("Processing Results Summary")
    print("="*80)
    
    # 表头
    print(f"{'Filename':<40} {'Type':<6} {'Replacements':<12} {'CSS Fixed':<10} {'Status':<10}")
    print("-"*80)
    
    # 表格内容
    for result in processing_results:
        filename = result['filename']
        if len(filename) > 37:
            filename = filename[:34] + "..."
        
        file_type = result['file_type']
        replacement_count = result['replacement_count']
        css_fixed = "Yes" if result['css_fixed'] else "No"
        
        if result['error']:
            status = "Failed"
        elif result['modified']:
            status = "Modified"
        else:
            status = "Unchanged"
        
        print(f"{filename:<40} {file_type:<6} {replacement_count:<12} {css_fixed:<10} {status:<10}")
    
    print("-"*80)
    print(f"Total: {len(files_to_process)} files | Modified: {modified_count} | Total replacements: {sum(r['replacement_count'] for r in processing_results)}")
    print(f"Results saved in '{PROCESSED_DIR_NAME}' and '{REPORT_DIR_NAME}' folders")
    print("="*80)

if __name__ == '__main__':
    main()