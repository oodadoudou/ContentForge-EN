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

def generate_report(report_path: Path, changes_log: list, source_filename: str):
    """
    Generate an HTML change report.
    
    Args:
        report_path: Path to the report file
        changes_log: List of change records, each containing 'original' and 'modified'
        source_filename: Source filename
    """
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
        # 提取高亮的原文和替换文本
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
    
    # Generate rule list items
    rules_list_items = ""
    for i, group in enumerate(sorted_rule_groups):
        rules_list_items += f'''
                    <div class="rule-list-item" onclick="jumpToRule({i})">
                        <div class="rule-text">
                            <span class="rule-original">{html.escape(group["original_text"])}</span> → 
                            <span class="rule-replacement">{html.escape(group["replacement_text"])}</span>
                        </div>
                        <div class="rule-count">{len(group["instances"])} 次</div>
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
                        <span class="rule-badge">{instance_count} 次</span>
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
                                <div class="section-title">原文</div>
                                <div class="text-content">{instance['original']}</div>
                            </div>
                            <div class="modified-section">
                                <div class="section-title">修改后</div>
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
    
    # Replace CSS and JS file paths
    html_content = html_content.replace('href="shared_assets/report_styles.css"', f'href="{css_path}"')
    html_content = html_content.replace('src="shared_assets/report_scripts.js"', f'src="{js_path}"')
    
    try:
        report_path.write_text(html_content, encoding='utf-8')
        print(f"[✓] Report generated: {report_path}")
        
    except Exception as e:
        print(f"[!] Unable to write report file {report_path}: {e}")

def is_main_content(content: str) -> bool:
    """
    Determine whether given content is main body text.
    Exclude titles, copyright info, TOC, headers/footers, and similar.
    Uses a relaxed heuristic to better recognize dialogues and short sentences.
    """
    if not content or not content.strip():
        return False
    
    content = content.strip()
    
    # Check for obvious headings (contains chapter markers, short, no punctuation)
    if len(content) < 8 and any(char in content for char in ['第', '章', '节', '篇', '卷']) and not any(char in content for char in ['，', '。', '！', '？']):
        return False
    
    # Check for copyright-related info
    if any(keyword in content for keyword in [
        '作者', '版权', '出版', '编辑', '译者', '责任编辑', 
        '©', 'Copyright', '版权所有', 'All rights reserved',
        '定价', 'ISBN', '书号'
    ]):
        return False
    
    # Special case: Exclude standalone price info (e.g., "Price: XX元")
    if re.match(r'^定价[：:].+元$', content.strip()):
        return False
    
    # Check for TOC-like content
    if content.count('…') > 3 or content.count('·') > 3:
        return False
    
    # Check for headers/footers (usually contain page numbers)
    if re.match(r'^[\d\-\s]+$', content):
        return False
    
    # Looser length check: only exclude extremely short and meaningless content
    if len(content) < 3:
        return False
    
    # If contains Chinese characters with some length, likely main content
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', content))
    if chinese_chars >= 2:
        return True
    
    # Special case: number + Chinese unit combinations should be processed
    if re.search(r'\d+\s*[\u4e00-\u9fff]+', content):
        return True
    
    # Special case: short text with punctuation and Chinese should be processed
    if chinese_chars >= 1 and re.search(r'[。！？，]', content):
        return True
    
    return False

def fix_punctuation_and_get_changes(content: str) -> tuple[str, list]:
    """
    Fix punctuation issues based on Chinese grammar norms and return changes.
    Reference: GB/T 15834-2011 punctuation usage standard.
    Only completes commas (not periods) and skips non-main content.
    Returns: (modified_text, atomic_changes)
    Atomic changes: [{'original_text': '...','replacement_text': '...'}]
    """
    # 首先判断是否为正文内容
    if not is_main_content(content):
        return content, []
    
    modified_content = content
    atomic_changes = []
    
    # Simplified punctuation and spacing fix rules (pragmatic version)
    punctuation_rules = [
        # 最高优先级：去除标点符号前的空格
        {
            'pattern': r'\s+([，,；;：:.。！!？?])',
            'replacement': r'\1',
            'description': 'Remove spaces before punctuation'
        },
        
        # 数字和单位处理（直接删除空格）
        {
            'pattern': r'([\d]+)\s+([元件个只张页卷本章节天年月日时分秒米厘米公里克千克斤两])',
            'replacement': r'\1\2',
            'description': 'Remove spaces between numbers and units'
        },
        
        # 量词前的空格（直接删除）
        {
            'pattern': r'([一二三四五六七八九十百千万亿零壹贰叁肆伍陆柒捌玖拾佰仟萬億\d]+)\s+([个只条张片块把件套双对副组批次回遍趟])',
            'replacement': r'\1\2',
            'description': 'Remove spaces before classifiers'
        },
        
        # 动作补语前的空格（直接删除）
        {
            'pattern': r'([\u4e00-\u9fff]*[走跑跳站坐躺])\s+(过来|过去|起来|下去|上来|下来|进来|出去)',
            'replacement': r'\1\2',
            'description': 'Remove spaces before result complements'
        },
        
        # 转折因果词前添加逗号（排除前面已有标点的情况）
        {
            'pattern': r'(?<![。！？，；：\-—])([\u4e00-\u9fff])\s+(但|然而|不过|可是|却|所以|因此|因而)',
            'replacement': r'\1，\2',
            'description': 'Add comma before contrast/causal words'
        },
        
        # 其他连词前的空格（直接删除）
        {
            'pattern': r'\s+(和|与|及|以及|或者|或|但是|而且|并且|因为|如果|假如|虽然|尽管)',
            'replacement': r'\1',
            'description': 'Remove spaces before other conjunctions'
        },
        
        # 简单粗暴：所有中文字符间的空格都替换为逗号
        {
            'pattern': r'([\u4e00-\u9fff])\s+([\u4e00-\u9fff])',
            'replacement': r'\1，\2',
            'description': 'Replace spaces between Chinese characters with commas'
        }
    ]
    
    # Apply each rule
    for rule in punctuation_rules:
        pattern = rule['pattern']
        replacement = rule['replacement']
        
        try:
            # Find all matches
            matches = list(re.finditer(pattern, modified_content))
            if matches:
                # Replace from the end to avoid position shifts
                for match in reversed(matches):
                    original_text = match.group(0)
                    replacement_text = re.sub(pattern, replacement, original_text)
                    
                    # Only record when replacement differs from original
                    if original_text != replacement_text:
                        # Simple check: avoid adding commas where punctuation already exists
                        # Allow removing spaces before punctuation
                        if rule['description'] != '去除标点符号前的空格':
                            if '，' in original_text or '。' in original_text or '！' in original_text or '？' in original_text:
                                continue
                        
                        atomic_changes.append({
                            "original_text": original_text,
                            "replacement_text": replacement_text
                        })
                        
                        # Apply replacement
                        modified_content = modified_content.replace(original_text, replacement_text, 1)
        except re.error as e:
            print(f"\n[!] Regex error: '{pattern}'. Error: {e}. Skipping.")
            continue
    
    # 去重
    unique_atomic_changes = [dict(t) for t in {tuple(d.items()) for d in atomic_changes}]
    return modified_content, unique_atomic_changes

def process_txt_file(file_path: Path, processed_dir: Path, report_dir: Path):
    """Process a single .txt file."""
    try:
        content = file_path.read_text(encoding='utf-8')
        paragraphs = content.split('\n\n')
        processed_paragraphs = []
        changes_log_for_report = []
        file_was_modified = False
        current_position = 0  # Track current position in original text

        for paragraph_index, p_original in enumerate(paragraphs):
            p_modified, atomic_changes = fix_punctuation_and_get_changes(p_original)
            processed_paragraphs.append(p_modified)

            if atomic_changes:
                file_was_modified = True
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
                    'position': current_position + paragraph_index  # Add positional info
                })
            
            current_position += len(p_original) + 2  # +2 for \n\n separator

        if file_was_modified:
            new_content = "\n\n".join(processed_paragraphs)
            processed_file_path = processed_dir / file_path.name
            processed_file_path.write_text(new_content, encoding='utf-8')
            report_path = report_dir / f"{file_path.name}.html"
            generate_report(report_path, changes_log_for_report, file_path.name)
            return True

    except Exception as e:
        print(f"\n[!] Failed to process TXT file {file_path.name}: {e}")
    return False

def process_epub_file(file_path: Path, processed_dir: Path, report_dir: Path):
    """Process a single .epub file. Unpack EPUB directly to locate CSS links."""
    try:
        book = epub.read_epub(str(file_path))
        changes_log = []
        book_is_modified = False
        global_position = 0  # 记录全局位置
        
        # Step 1: Unpack EPUB to a temporary directory
        temp_dir = None
        original_html_contents = {}
        original_css_links_by_file = {}
        
        try:
            temp_dir = tempfile.mkdtemp(prefix='epub_extract_')
            print(f"[DEBUG] Unpacked EPUB to temporary directory: {temp_dir}")
            
            # Unpack EPUB file
            with zipfile.ZipFile(str(file_path), 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            # Traverse unpacked dir to find all HTML/XHTML files
            html_files = []
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    if file.endswith(('.html', '.xhtml')):
                        html_files.append(os.path.join(root, file))
            
            print(f"[DEBUG] Found {len(html_files)} HTML/XHTML files in unpacked directory")
            
            # Read each HTML file's original content and find CSS links
            css_pattern = r'<link[^>]*href=["\'][^"\']*.css["\'][^>]*\/?>'  
            
            for html_file_path in html_files:
                try:
                    with open(html_file_path, 'r', encoding='utf-8') as f:
                        file_content = f.read()
                    
                    # Get file name relative to EPUB root
                    relative_path = os.path.relpath(html_file_path, temp_dir)
                    # Normalize path separators to forward slashes
                    relative_path = relative_path.replace('\\', '/')
                    
                    # Save original content
                    original_html_contents[relative_path] = file_content
                    
                    # Find CSS links
                    css_links = re.findall(css_pattern, file_content, re.IGNORECASE)
                    original_css_links_by_file[relative_path] = css_links
                    
                    print(f"[DEBUG] File {relative_path}: Found {len(css_links)} CSS link(s)")
                    if css_links:
                        for i, link in enumerate(css_links):
                            print(f"[DEBUG]   CSS link {i+1}: {link}")
                    
                except Exception as e:
                    print(f"[DEBUG] Failed to read file {html_file_path}: {e}")
                    continue
            
            print(f"[DEBUG] Extracted original content from {len(original_html_contents)} HTML files in total")
            
        finally:
            # Clean temporary directory
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                    print(f"[DEBUG] Cleaned temporary directory: {temp_dir}")
                except Exception as e:
                    print(f"[DEBUG] Failed to clean temporary directory: {e}")

        # Step 2: Use ebooklib to process EPUB content
        for item in book.get_items_of_type(ITEM_DOCUMENT):
            item_name = item.get_name()
            original_content_bytes = item.get_content()
            original_content = original_content_bytes.decode('utf-8')
            
            print(f"[DEBUG] Processing file: {item_name}")
            print(f"[DEBUG] Original HTML first 500 chars: {original_content[:500]}")
            
            # Get CSS link info from unpacked files
            # Try multiple path resolution strategies
            css_links_for_this_file = []
            possible_paths = [
                item_name,
                item_name.lstrip('/'),
                f"EPUB/{item_name}",
                f"OEBPS/{item_name}"
            ]
            
            for path in possible_paths:
                if path in original_css_links_by_file:
                    css_links_for_this_file = original_css_links_by_file[path]
                    print(f"[DEBUG] Found CSS link info via path '{path}'")
                    break
            
            print(f"[DEBUG] CSS link count from unpacked files: {len(css_links_for_this_file)}")
            if css_links_for_this_file:
                for i, link in enumerate(css_links_for_this_file):
                    print(f"[DEBUG] Unpacked file CSS link {i+1}: {link}")
            
            # Parse using BeautifulSoup
            soup = BeautifulSoup(original_content_bytes, 'xml')
            if not soup.body:
                continue

            item_is_modified = False
            for p_tag in soup.body.find_all('p'):
                if not p_tag.get_text(strip=True): 
                    continue

                original_p_html = str(p_tag)
                p_text_original = p_tag.get_text()

                p_text_modified, atomic_changes = fix_punctuation_and_get_changes(p_text_original)

                if atomic_changes:
                    book_is_modified = True
                    item_is_modified = True
                    
                    p_tag.string = p_text_modified  # 更安全地替换段落内容
                    modified_p_html = str(p_tag)

                original_report = original_p_html
                    modified_report = modified_p_html

                    for change in atomic_changes:
                        orig_esc = html.escape(change["original_text"])
                        repl_esc = html.escape(change["replacement_text"])
                        original_report = original_report.replace(orig_esc, f'<span class="highlight">{orig_esc}</span>')
                        modified_report = modified_report.replace(repl_esc, f'<span class="highlight">{repl_esc}</span>')
                    
                    changes_log.append({
                        'original': original_report,
                        'modified': modified_report,
                        'position': global_position  # 添加位置信息
                    })
                
                global_position += len(p_text_original)  # 更新全局位置

            # Get processed content (check CSS links regardless of text changes)
            processed_content = str(soup)
            
            # Debug output: show first 500 chars of processed content
            print(f"[DEBUG] Processed HTML first 500 chars: {processed_content[:500]}")
            
            # 比对解包文件中的CSS链接和处理后的内容，检查CSS链接是否丢失
            css_was_restored = False
            if css_links_for_this_file:
                print(f"[DEBUG] Start comparing CSS links...")
                missing_links = []
                for i, css_link in enumerate(css_links_for_this_file):
                    if css_link not in processed_content:
                        missing_links.append(css_link)
                        print(f"[DEBUG] ✗ CSS link {i+1} missing: {css_link}")
                    else:
                        print(f"[DEBUG] ✓ CSS link {i+1} present: {css_link}")
                
                if missing_links:
                    print(f"[DEBUG] Found {len(missing_links)} missing CSS link(s); restoring from unpacked file...")
                    
                    # 从解包文件的原始内容中提取head标签的完整内容
                    original_file_content = None
                    for path in possible_paths:
                        if path in original_html_contents:
                            original_file_content = original_html_contents[path]
                            print(f"[DEBUG] Found original file content via path '{path}'")
                            break
                    
                    if original_file_content:
                        original_head_match = re.search(r'<head[^>]*>.*?</head>', original_file_content, re.DOTALL | re.IGNORECASE)
                        if original_head_match:
                            original_head_content = original_head_match.group(0)
                            print(f"[DEBUG] Unpacked file head tag content: {original_head_content}")
                            
                            # 查找处理后内容中的head标签
                            processed_head_match = re.search(r'<head[^>]*>.*?</head>', processed_content, re.DOTALL | re.IGNORECASE)
                            if processed_head_match:
                                # 替换整个head标签
                                processed_content = processed_content.replace(processed_head_match.group(0), original_head_content)
                                print(f"[DEBUG] ✓ Replaced processed head tag with unpacked file's head tag")
                                css_was_restored = True
                            else:
                                # 查找自闭合的head标签
                                head_self_closing_match = re.search(r'<head\s*\/>', processed_content, re.IGNORECASE)
                                if head_self_closing_match:
                                    processed_content = processed_content.replace(head_self_closing_match.group(0), original_head_content)
                                    print(f"[DEBUG] ✓ Replaced self-closing head tag with full head tag from unpacked file")
                                    css_was_restored = True
                                else:
                                    print(f"[DEBUG] ✗ No head tag found; unable to restore CSS links")
                        else:
                            print(f"[DEBUG] ✗ No complete head tag found in unpacked file")
                    else:
                        print(f"[DEBUG] ✗ No corresponding unpacked file content found")
                else:
                    print(f"[DEBUG] ✓ All CSS links present; no restoration needed")
            else:
                print(f"[DEBUG] No CSS links in unpacked file; skipping check")
            
            # Debug output: show first 500 chars of final content
            print(f"[DEBUG] Final HTML first 500 chars: {processed_content[:500]}")
            
            # 如果文件被修改，则更新item内容
            if item_is_modified:
                # 如果CSS被恢复，使用恢复后的内容，否则使用BeautifulSoup处理后的内容
                final_content = processed_content if css_was_restored else str(soup)
                item.set_content(final_content.encode('utf-8'))
            elif css_was_restored:
                # 如果只是CSS被恢复而内容没有修改，直接使用恢复后的内容
                item.set_content(processed_content.encode('utf-8'))
                book_is_modified = True  # Ensure even CSS-only restoration is marked as modified

        if book_is_modified:
            # 检查并确保EPUB有必需的identifier元数据
            if not book.get_metadata('DC', 'identifier'):
                # 如果没有identifier，添加一个默认的
                import uuid
                default_identifier = f"urn:uuid:{uuid.uuid4()}"
                book.add_metadata('DC', 'identifier', default_identifier)
                print(f"  [DEBUG] Added default identifier: {default_identifier}")
            
            epub.write_epub(str(processed_dir / file_path.name), book, {})
            unique_changes = [dict(t) for t in {tuple(d.items()) for d in changes_log}]
            generate_report(report_dir / f"{file_path.name}.html", unique_changes, file_path.name)
            return True

    except Exception as e:
        print(f"\n[!] Failed to process EPUB file {file_path.name}: {e}")
    return False

def load_default_path_from_settings():
    """Read default working directory from the shared settings file."""
    try:
        # Navigate two levels up to reach project root
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        settings_path = os.path.join(project_root, 'shared_assets', 'settings.json')
        with open(settings_path, 'r', encoding='utf-8') as f:
            settings = json.load(f)
        # 如果 "default_work_dir" 存在且不为空，则返回它
        default_dir = settings.get("default_work_dir")
        return default_dir if default_dir else "."
    except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
        print(f"Warning: Failed to read settings.json ({e}); using user's 'Downloads' as fallback path.")
        # 提供一个通用的备用路径
        return os.path.join(os.path.expanduser("~"), "Downloads")

def main():
    """Main function."""
    print("[*] Punctuation Completion Tool")
    print("[*] Automatically fixes missing punctuation in Chinese text")
    print("[*] Supports processing .txt and .epub files")
    print()
    
    # Dynamically load default path
    default_path = load_default_path_from_settings()
    
    prompt_message = (
        f"Please enter the folder path containing source files.\n"
        f"(Press Enter to use the default path '{default_path}') : "
    )
    user_input = input(prompt_message)

    if not user_input.strip():
        directory_path = default_path
        print(f"[*] No path entered; using default path: {directory_path}")
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
    print(f"[*] Output folders prepared:\n    - Processed files: {processed_dir}\n    - Change reports: {report_dir}")

    # 查找所有需要处理的文件
    all_target_files = list(base_dir.glob('*.txt')) + list(base_dir.glob('*.epub'))
    files_to_process = all_target_files

    if not files_to_process:
        print("[!] No .txt or .epub files needing processing found in the specified folder.")
        return

    print(f"[*] Found {len(files_to_process)} file(s) to process.")
    print("[*] Starting punctuation completion...")

    modified_count = 0
    with tqdm(total=len(files_to_process), desc="Processing Progress", unit="file") as pbar:
        for file_path in files_to_process:
            pbar.set_postfix_str(file_path.name, refresh=True)
            was_modified = False
            if file_path.suffix == '.txt':
                was_modified = process_txt_file(file_path, processed_dir, report_dir)
            elif file_path.suffix == '.epub':
                was_modified = process_epub_file(file_path, processed_dir, report_dir)
            
            if was_modified:
                modified_count += 1
            pbar.update(1)

    print("\n----------------------------------------")
    print(f"[✓] 标点符号补全任务完成！")
    print(f"    - 共处理 {len(files_to_process)} 个文件。")
    print(f"    - 其中 {modified_count} 个文件被修改。")
    print(f"    - 结果已保存至 '{PROCESSED_DIR_NAME}' 和 '{REPORT_DIR_NAME}' 文件夹。")
    
    if modified_count > 0:
        print(f"\n[*] 请查看 '{REPORT_DIR_NAME}' 文件夹中的 HTML 报告以了解详细修改内容。")

if __name__ == '__main__':
    main()
