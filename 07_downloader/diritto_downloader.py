import os
import sys
import time
import json
import shutil
import traceback
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- Core script code ---

def load_default_download_path():
    """
    Read the default working directory from the shared settings file; if it fails, return the user's Downloads folder.
    """
    try:
        # Compatible with packaged programs (e.g., PyInstaller)
        if getattr(sys, 'frozen', False):
            project_root = os.path.dirname(sys.executable)
        # For normal script execution, assume the script is in a subdirectory like 'scripts'
        else:
            # Go up two levels to find the project root directory
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        settings_path = os.path.join(project_root, 'shared_assets', 'settings.json')
        
        if os.path.exists(settings_path):
            print(f"[Info] Found settings file: {settings_path}")
            with open(settings_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)
            default_dir = settings.get("default_work_dir")
            
            # Verify the path is a valid directory
            if default_dir and os.path.isdir(default_dir):
                return default_dir
            elif default_dir:
                print(f"⚠️ Warning: Path '{default_dir}' in the settings file is invalid. Using fallback path.")

    except Exception as e:
        print(f"⚠️ Warning: Error reading settings file ({e}). Using fallback path.")

    # If any of the above steps fail, fall back to the system's default Downloads folder
    return os.path.join(os.path.expanduser("~"), "Downloads")


def setup_driver():
    """Configure and connect to an already opened Chrome browser instance"""
    print("Attempting to connect to an already launched Chrome browser...")
    print("Please ensure Chrome was launched with --remote-debugging-port=9222 as instructed.")
    options = Options()
    options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    try:
        driver = webdriver.Chrome(options=options)
        print("✅ Successfully connected to the browser!")
        return driver
    except Exception as e:
        print(f"❌ Failed to connect to the browser: {e}")
        print("Please confirm:")
        print("1. Was Chrome launched from the command line with the '--remote-debugging-port=9222' parameter?")
        print("2. Are there no other Chrome windows open (completely exit Chrome before launching as instructed)?")
        return None

def process_book(driver, start_url, download_path):
    """
    Process a single book's complete download flow, starting from the main page and loading via scroll.
    """
    stats = {'skipped': 0, 'successful': 0, 'failed': 0, 'failed_items': []}
    
    try:
        # 1. Determine the book's main page URL
        is_chapter_url = "/episodes/" in start_url
        base_url = start_url.split('/episodes/')[0] if is_chapter_url else start_url.split('?')[0]
        base_url = base_url.rstrip('/')

        print(f"Visiting book main page: {base_url}")
        driver.get(base_url)
        wait = WebDriverWait(driver, 45)  # Increase timeout to 45 seconds
        
        # 2. Get novel title
        print("Waiting for page to load and obtaining novel title...")
        
        # Try multiple possible title selectors
        title_selectors = [
            'p[class*="e1fhqjtj1"]',    # 原始选择器
            'h1[class*="title"]',       # 备用选择器1
            'h1',                       # 通用h1选择器
            'h2[class*="title"]',       # 备用选择器2
            '[class*="title"]',         # 任何包含title的class
            '.title'                    # 通用title类
        ]
        
        novel_title = None
        for selector in title_selectors:
            try:
                novel_title_element = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, selector)))
                novel_title = novel_title_element.text.strip().replace('/', '_').replace('\\', '_')
                if novel_title:  # 确保标题不为空
                    print(f"✅ Found novel title using selector: {selector}")
                    break
            except (TimeoutException, Exception):
                print(f"⚠️ 选择器 {selector} 未找到标题，尝试下一个...")
                continue
        
        if not novel_title:
            print("⚠️ Warning: Failed to obtain novel title, using default name")
            novel_title = "Unknown Novel"
            
        print(f"📘 Novel title: {novel_title}")

        # 3. Scroll to bottom to load all chapters
        print("Retrieving chapter list (infinite scroll)...")
        
        # Use multiple possible selectors to locate chapter container
        chapter_container_selectors = [
            'div[class*="eihlkz80"]',  # 原始选择器
            'div[class*="ese98wi3"]',  # 备用选择器1
            'div[class*="episode"]',   # 备用选择器2
            'div[data-testid*="episode"]',  # 备用选择器3
            'div[class*="chapter"]',   # 备用选择器4
            'div[class*="list"]'       # 备用选择器5
        ]
        
        chapter_container_found = False
        for selector in chapter_container_selectors:
            try:
                wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, selector)))
                print(f"✅ Found chapter container using selector: {selector}")
                chapter_container_found = True
                break
            except TimeoutException:
                print(f"⚠️ Selector {selector} did not find element, trying next...")
                continue
        
        if not chapter_container_found:
            print("❌ Warning: Failed to find chapter container, continuing to attempt scroll loading...")
        
        # Scroll loading strategy, increase attempts limit
        last_height = driver.execute_script("return document.body.scrollHeight")
        scroll_attempts = 0
        max_scroll_attempts = 10
        
        while scroll_attempts < max_scroll_attempts:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)  # Increase wait time
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                print("✅ Reached bottom, loading complete.")
                break
            last_height = new_height
            scroll_attempts += 1
            print(f"  Scrolling... ({scroll_attempts}/{max_scroll_attempts})")
        
        if scroll_attempts >= max_scroll_attempts:
            print("⚠️ Reached maximum scroll attempts, stopping scroll.")
        
        # 4. Get all chapter links
        # Try multiple possible chapter list container selectors
        chapter_list_selectors = [
            'div[class*="ese98wi3"]',  # 原始选择器
            'div[class*="eihlkz80"]',  # 备用选择器1
            'div[class*="episode"]',   # 备用选择器2
            'div[class*="chapter"]',   # 备用选择器3
            'div[class*="list"]',      # 备用选择器4
            'main',                    # 通用容器选择器
            'body'                     # 最后的兜底选择器
        ]
        
        chapter_list_container = None
        for selector in chapter_list_selectors:
            try:
                chapter_list_container = driver.find_element(By.CSS_SELECTOR, selector)
                print(f"✅ Found chapter list container using selector: {selector}")
                break
            except Exception:
                print(f"⚠️ Selector {selector} did not find a chapter list container, trying next...")
                continue
        
        if chapter_list_container is None:
            print("❌ Error: Failed to find any chapter list container.")
            return None, None, stats
        
        # Try multiple possible chapter link selectors
        chapter_link_selectors = [
            'a[href*="/episodes/"]',     # 原始选择器
            'a[href*="episode"]',        # 备用选择器1
            'a[href*="chapter"]',        # 备用选择器2
            'a[class*="episode"]',       # 备用选择器3
            'a[class*="chapter"]'        # 备用选择器4
        ]
        
        full_url_list = []
        for selector in chapter_link_selectors:
            try:
                chapter_links_elements = chapter_list_container.find_elements(By.CSS_SELECTOR, selector)
                if chapter_links_elements:
                    urls = [elem.get_attribute('href') for elem in chapter_links_elements if elem.get_attribute('href')]
                    full_url_list = sorted(list(set(urls)))
                    print(f"✅ Found chapter links using selector: {selector}")
                    break
            except Exception:
                print(f"⚠️ 选择器 {selector} 未找到章节链接，尝试下一个...")
                continue

        if not full_url_list:
            print("❌ Error: Failed to find any chapter links.")
            return None, None, stats
            
        print(f"Found {len(full_url_list)} chapters in total.")

        # 5. Determine the download starting point
        start_index = 0
        if is_chapter_url:
            try:
                clean_start_url = start_url.split('?')[0].rstrip('/')
                clean_full_url_list = [url.split('?')[0].rstrip('/') for url in full_url_list]
                start_index = clean_full_url_list.index(clean_start_url)
                print(f"✅ Found starting point; will process from chapter {start_index + 1}.")
            except ValueError:
                print(f"⚠️ Warning: The chapter URL {start_url} was not found in the final directory list. Starting from chapter 1.")
        
        # Create main directory named after the novel
        book_dir = os.path.join(download_path, novel_title)
        os.makedirs(book_dir, exist_ok=True)
        print(f"All files will be saved to: {book_dir}")
        
        # 6. Iterate through each chapter and add retry logic
        for i, url in enumerate(full_url_list[start_index:], start=start_index):
            chapter_number = i + 1
            print(f"\n--- Processing '{novel_title}' - Chapter {chapter_number} / {len(full_url_list)} ---")
            
            chapter_prefix = f"{str(chapter_number).zfill(4)}_"
            
            # Check files in the new book_dir
            # Check if files already exist in the main directory and chapters subdirectory
            chapters_subdir = os.path.join(book_dir, "chapters")
            existing_in_main = [f for f in os.listdir(book_dir) if f.startswith(chapter_prefix) and os.path.isfile(os.path.join(book_dir, f))]
            existing_in_sub = []
            if os.path.exists(chapters_subdir):
                existing_in_sub = [f for f in os.listdir(chapters_subdir) if f.startswith(chapter_prefix)]

            if existing_in_main or existing_in_sub:
                existing_file_name = (existing_in_main + existing_in_sub)[0]
                print(f"✅ Detected file '{existing_file_name}', this chapter is already downloaded; skipping.")
                stats['skipped'] += 1
                continue

            retries = 0
            MAX_RETRIES = 3
            download_successful = False
            
            while retries < MAX_RETRIES and not download_successful:
                try:
                    if retries > 0:
                        print(f"  - Retry {retries}... URL: {url}")
                    else:
                        print(f"  - URL: {url}")
                        
                    driver.get(url)

                    # Try multiple possible chapter title selectors
                    chapter_title_selectors = [
                        'span[class*="e14fx9ai3"]',  # 原始选择器
                        'h1[class*="title"]',        # 备用选择器1
                        'h1',                        # 通用h1选择器
                        'h2',                        # 备用h2选择器
                        '[class*="title"]'           # 任何包含title的class
                    ]
                    
                    chapter_title = None
                    for selector in chapter_title_selectors:
                        try:
                            chapter_title_element = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, selector)))
                            chapter_title = chapter_title_element.text.strip()
                            if chapter_title:  # 确保标题不为空
                                break
                        except (TimeoutException, Exception):
                            continue
                    
                    if not chapter_title:
                        chapter_title = f"Chapter {chapter_number}"
                        print(f"  ⚠️ Unable to obtain chapter title, using default: {chapter_title}")
                    
                    # Try multiple possible content selectors
                    content_selectors = [
                        '.tiptap.ProseMirror',       # 原始选择器
                        '.content',                  # 通用内容选择器
                        '[class*="content"]',        # 任何包含content的class
                        '.ProseMirror',              # ProseMirror编辑器
                        '[class*="text"]',           # 任何包含text的class
                        'article'                    # article标签
                    ]
                    
                    content = None
                    for selector in content_selectors:
                        try:
                            content_container = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                            content_elements = content_container.find_elements(By.CSS_SELECTOR, 'p')
                            if content_elements:
                                content = "\n\n".join([p.text for p in content_elements if p.text.strip()])
                                if content.strip():  # 确保内容不为空
                                    break
                        except (TimeoutException, Exception):
                            continue
                    
                    if not content or not content.strip():
                        raise ValueError("Content retrieved is empty; the page structure may have changed.")

                    sanitized_title = chapter_title.replace('/', '_').replace('\\', '_').replace(':', '：')
                    file_name = f"{chapter_prefix}{sanitized_title}.txt"
                    file_path = os.path.join(book_dir, file_name)
                    
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(f"{chapter_title}\n\n")
                        f.write(content)
                    
                    print(f"  ✅ Saved: {file_name}")
                    stats['successful'] += 1
                    download_successful = True

                except Exception as e:
                    retries += 1
                    error_msg = str(e)
                    print(f"  - Error scraping chapter (attempt {retries}/{MAX_RETRIES}): {error_msg}")
                    
                    # 如果是TimeoutException，提供更详细的调试信息
                    if "TimeoutException" in error_msg or "timeout" in error_msg.lower():
                        print(f"  - Timeout error; the page may load too slowly or selectors have changed")
                        print(f"  - Current page URL: {driver.current_url}")
                        try:
                            page_source_preview = driver.page_source[:500]
                            print(f"  - Page source preview: {page_source_preview}...")
                        except:
                            print("  - Unable to retrieve page source preview")
                    
                    if retries < MAX_RETRIES:
                        time.sleep(5)  # 增加重试间隔
                    else:
                        print(f"  ❌ Failed to scrape this chapter; reached maximum retry attempts.")
                        stats['failed'] += 1
                        stats['failed_items'].append({'url': url, 'error': error_msg})

            time.sleep(2)
            
        return novel_title, book_dir, stats

    except Exception as e:
        print(f"❌ A critical error occurred while processing the book {start_url}: {e}")
        traceback.print_exc()
        return None, None, stats

def merge_chapters(novel_title, book_dir):
    """Merge all TXT files in the folder in order, then move volumes to a subdirectory. Files smaller than 3KB will be skipped from merging."""
    merged_filename = os.path.join(book_dir, f"{novel_title}.txt")
    print(f"\n🔄 Starting to merge all chapters into a single file: {merged_filename}")
    
    try:
        if not os.path.exists(book_dir):
            print(f"⚠️ Warning: Directory {book_dir} does not exist; cannot merge.")
            return
        
        # Get all original txt files
        all_txt_files = sorted([f for f in os.listdir(book_dir) if f.endswith('.txt') and os.path.isfile(os.path.join(book_dir, f))])

        if not all_txt_files:
            print("⚠️ Warning: No chapter files found for merging.")
            return

        # Filter out files >= 3KB for merging
        files_to_merge = []
        for filename in all_txt_files:
            file_path = os.path.join(book_dir, filename)
            # Change: condition from 800 bytes to 3 KB (3 * 1024 bytes)
            if os.path.getsize(file_path) < 3 * 1024:
                print(f"  - [Skip merge] File '{filename}' is smaller than 3 KB and considered non-content.")
            else:
                files_to_merge.append(filename)

        if not files_to_merge:
            print("⚠️ Warning: After filtering, there are no chapter files meeting the size requirement for merging.")
        else:
            with open(merged_filename, 'w', encoding='utf-8') as outfile:
                for i, filename in enumerate(files_to_merge):
                    file_path = os.path.join(book_dir, filename)
                    with open(file_path, 'r', encoding='utf-8') as infile:
                        outfile.write(infile.read())
                    
                    if i < len(files_to_merge) - 1:
                        outfile.write("\n\n\n==========\n\n\n")
            
            print(f"✅ Merge complete! Novel saved to: {os.path.abspath(merged_filename)}")
        
        # Move all original txt files to the chapters subdirectory
        chapters_subdir = os.path.join(book_dir, "chapters")
        os.makedirs(chapters_subdir, exist_ok=True)
        
        for filename in all_txt_files:
            src_path = os.path.join(book_dir, filename)
            dest_path = os.path.join(chapters_subdir, filename)
            if os.path.exists(src_path) and src_path != merged_filename:
                shutil.move(src_path, dest_path)

        print(f"📂 Chapter files moved to subdirectory: {os.path.abspath(chapters_subdir)}")
        
    except Exception as e:
        print(f"❌ Error occurred while merging or moving files: {e}")

def print_book_report(stats, novel_title):
    """Print execution report for a single book"""
    print("\n" + "="*40)
    print(f"📋 Single Book Report: {novel_title or 'Unknown Book'}")
    print("="*40)
    print(f"✅ Successfully downloaded: {stats['successful']} chapters")
    print(f"⏭️ Skipped: {stats['skipped']} chapters (already exists)")
    print(f"❌ Failed: {stats['failed']} chapters")
    
    if stats['failed_items']:
        print("\n--- Failed Item Details ---")
        for item in stats['failed_items']:
            print(f"  - URL: {item['url']}")
    print("="*40)

def print_total_report(all_book_stats):
    """Print total report for all tasks"""
    total_stats = {
        'books_processed': len(all_book_stats),
        'books_completed_successfully': 0,
        'books_with_failures': 0,
        'total_successful': 0,
        'total_skipped': 0,
        'total_failed': 0,
    }

    for stats in all_book_stats:
        total_stats['total_successful'] += stats['successful']
        total_stats['total_skipped'] += stats['skipped']
        total_stats['total_failed'] += stats['failed']
        if stats['failed'] > 0:
            total_stats['books_with_failures'] += 1
        else:
            total_stats['books_completed_successfully'] += 1

    print("\n" + "#"*50)
    print("📊 Total Report for All Tasks")
    print("#"*50)
    print(f"Total books processed: {total_stats['books_processed']}")
    print(f"✅ Books completed successfully: {total_stats['books_completed_successfully']}")
    print(f"⚠️ Books with partial failures: {total_stats['books_with_failures']}")
    print("-" * 20)
    print(f"Total successful chapter downloads: {total_stats['total_successful']}")
    print(f"Total skipped chapters: {total_stats['total_skipped']}")
    print(f"Total failed chapters: {total_stats['total_failed']}")
    print("#"*50)


if __name__ == "__main__":
    default_download_path = load_default_download_path()
    print(f"[Info] Current download path set to: {default_download_path}")
    
    print("\nPlease input one or more Diritto novel URLs (paste multiple lines; press Enter twice when done):")
    lines = []
    while True:
        try:
            line = input()
            if not line:
                break
            lines.append(line)
        except EOFError:
            break
    
    urls_input = " ".join(lines)
    url_list = [url for url in urls_input.split() if url.startswith("http")]

    if not url_list:
        print("❌ Error: No valid URLs entered.")
    else:
        if not os.path.exists(default_download_path):
            os.makedirs(default_download_path)
            print(f"Created download directory: {default_download_path}")
        
        driver = setup_driver()
        if driver:
            all_book_stats = []
            try:
                # --- 顺序处理书籍 ---
                for i, novel_url in enumerate(url_list):
                    print("\n" + "#"*60)
                    print(f"# Start processing book {i + 1} / {len(url_list)}: {novel_url}")
                    print("#"*60 + "\n")

                    novel_title, book_dir, book_stats = process_book(driver, novel_url, default_download_path)
                    
                    if book_stats:
                        all_book_stats.append(book_stats)
                        print_book_report(book_stats, novel_title)

                    if novel_title and book_dir:
                        if book_stats and book_stats['failed'] > 0:
                            print(f"\n⚠️ '{novel_title}' has failed download items; skipping file merge.")
                            print(f"Source files remain in directory: {os.path.abspath(book_dir)}")
                        else:
                            merge_chapters(novel_title, book_dir)
            finally:
                if all_book_stats:
                    print_total_report(all_book_stats)
                print("\nAll tasks completed. You may close the browser manually.")
