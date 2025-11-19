import os
import re
import json
import time
import shutil
import sys
import threading
from pathlib import Path
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import pandas as pd
import concurrent.futures
import requests
from itertools import groupby
from PIL import Image, ImageDraw, ImageFont, ImageFile
import base64
import io
from collections import Counter

# --- Helper Functions ---
def load_config(default_url, default_path):
    config_file = 'manga_downloader_config.json'
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, KeyError): pass
    return {'url': default_url, 'path': default_path}

def save_config(data):
    with open('manga_downloader_config.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

def sanitize_for_filename(name):
    if not name: return "Untitled"
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    name = name.replace(':', ' - ')
    name = name.strip().rstrip('. ')
    return " ".join(name.split())

def parse_chapter_selection(selection_str, max_chapters):
    if selection_str.lower() == 'all':
        return list(range(1, max_chapters + 1))
    indices = set()
    for part in selection_str.split(','):
        part = part.strip()
        if '-' in part:
            try:
                start, end = map(int, part.split('-'))
                indices.update(range(start, end + 1))
            except ValueError: pass
        else:
            try:
                indices.add(int(part))
            except ValueError: pass
    return sorted([i for i in indices if 1 <= i <= max_chapters])

def get_timed_input(prompt, timeout=30):
    sys.stdout.write(prompt); sys.stdout.flush()
    input_str = [None]
    def read_input(target): target[0] = sys.stdin.readline().strip()
    thread = threading.Thread(target=read_input, args=(input_str,))
    thread.daemon = True; thread.start(); thread.join(timeout)
    if thread.is_alive():
        print("\n[!] Input timed out, using default value.")
        return None
    return input_str[0]

class ErrorTracker:
    def __init__(self):
        self.warnings = []
        self.errors = []
        self.manga_path = None
        self.failed_chapters = set()  # Record failed chapters

    def add_warning(self, chapter_name, message):
        self.warnings.append({'chapter': chapter_name, 'message': message})

    def add_error(self, chapter_name, error):
        self.errors.append({'chapter': chapter_name, 'error': str(error)})
        self.failed_chapters.add(chapter_name)

    def set_manga_path(self, path):
        self.manga_path = path

    def _categorize_errors(self):
        """Categorize errors by type"""
        error_categories = {
            'Network Timeout': [],
            'Connection Interrupted': [],
            'Proxy Error': [],
            'Other Errors': []
        }
        
        for error in self.errors:
            error_msg = error['error'].lower()
            chapter = error['chapter']
            
            if 'read timed out' in error_msg or 'timeout' in error_msg:
                error_categories['Network Timeout'].append(chapter)
            elif 'connection aborted' in error_msg or 'connection reset' in error_msg:
                error_categories['Connection Interrupted'].append(chapter)
            elif 'proxy' in error_msg or 'unable to connect to proxy' in error_msg:
                error_categories['Proxy Error'].append(chapter)
            else:
                error_categories['Other Errors'].append(chapter)
        
        return error_categories

    def _clean_failed_chapters(self, progress_data):
        """Clean failed chapters: reset status to pending and remove folders"""
        if not self.manga_path or not self.failed_chapters:
            return
        
        print(f"\n[*] Cleaning {len(self.failed_chapters)} failed chapters...")
        
        manga_title = self.manga_path.name
        cleaned_count = 0
        
        for chapter_name in self.failed_chapters:
            try:
                # Reset chapter status to pending
                if manga_title in progress_data and 'chapters' in progress_data[manga_title]:
                    if chapter_name in progress_data[manga_title]['chapters']:
                        progress_data[manga_title]['chapters'][chapter_name]['status'] = 'pending'
                        print(f"    [✓] Status reset: {chapter_name}")
                
                # Remove chapter folder
                chapter_folder = self.manga_path / sanitize_for_filename(chapter_name)
                if chapter_folder.exists() and chapter_folder.is_dir():
                    shutil.rmtree(chapter_folder)
                    print(f"    [✓] Folder deleted: {chapter_name}")
                    cleaned_count += 1
                    
            except Exception as e:
                print(f"    [!] Error cleaning chapter {chapter_name}: {e}")
        
        # Save updated progress
        if cleaned_count > 0:
            save_progress(self.manga_path, progress_data)
            print(f"    [✓] Cleaned {cleaned_count} chapter folders and reset status")

    def print_summary(self, progress_data=None):
        print("\n" + "="*25 + " [Task Summary Report] " + "="*25)

        if self.manga_path:
            print(f"\n[+] Manga save directory:\n    -> {self.manga_path.resolve()}")
        
        if not self.warnings and not self.errors:
            print("\n[🎉] All tasks completed successfully, no issues found.")
            print("\n" + "="*68)
            return

        if self.warnings:
            print("\n[!] Warnings (please check the following chapters manually):")
            for warning in self.warnings:
                print(f"    - Chapter [{warning['chapter']}]: {warning['message']}")

        if self.errors:
            print("\n[✗] Failure Report (concise):")
            
            # Display by error category
            error_categories = self._categorize_errors()
            
            for category, chapters in error_categories.items():
                if chapters:
                    unique_chapters = list(set(chapters))  # de-duplicate
                    print(f"\n    [{category}] Affected chapters ({len(unique_chapters)}):")
                    for i, chapter in enumerate(unique_chapters):
                        if i < 5:  # show first 5 only
                            print(f"      • {chapter}")
                        elif i == 5:
                            print(f"      • ... and {len(unique_chapters) - 5} more chapters")
                            break
            
            print(f"\n    [📊] Total failed chapters: {len(self.failed_chapters)}")
            
            # Execute cleanup of failed chapters
            if progress_data:
                self._clean_failed_chapters(progress_data)
        
        print("\n" + "="*68)


class MangaScraper:
    def __init__(self, driver):
        self.driver = driver

    def get_info_from_chapter_page(self, chapter_url):
        print(f"[*] Visiting: {chapter_url} to retrieve manga info...")
        try:
            self.driver.get(chapter_url)
            wait = WebDriverWait(self.driver, 20)
            breadcrumb_selector = ".c-breadcrumb ol.breadcrumb li a"
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, breadcrumb_selector)))
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            breadcrumb_links = soup.select(breadcrumb_selector)
            if len(breadcrumb_links) >= 2:
                manga_title = sanitize_for_filename(breadcrumb_links[-1].get_text(strip=True))
                print(f"[+] Manga title obtained: {manga_title}")
                # The base URL for resolving relative chapter URLs
                base_url = self.driver.current_url
                return manga_title, base_url
        except Exception as e:
            print(f"[!] Failed to get info from chapter page: {e}")
        return None, None

    def get_chapters_from_dropdown(self, base_url):
        try:
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            chapters = []
            seen_urls = set()
            chapter_options = soup.select('select.single-chapter-select option')
            
            # Use a temporary list to add chapters in order, then reverse at the end
            temp_chapters = []
            for option in chapter_options:
                url = option.get('data-redirect')
                name = sanitize_for_filename(option.get_text(strip=True))
                
                if url and name:
                    # Resolve relative URLs to be absolute
                    full_url = urljoin(base_url, url)
                    if full_url not in seen_urls:
                        temp_chapters.append({'url': full_url, 'name': name})
                        seen_urls.add(full_url)
            
            # Reverse to get chronological order (Chapter 1, 2, 3...)
            chapters = list(reversed(temp_chapters))
            
            print(f"[+] 成功解析到 {len(chapters)} 个唯一章节。")
            return chapters
        except Exception as e:
            print(f"[!] 从下拉菜单获取章节列表失败: {e}")
            return []

class ChapterScanPipeline:
    def __init__(self, driver, max_refresh_attempts=2):
        self.driver = driver
        self.scraper = MangaScraper(driver=driver)
        self.max_refresh_attempts = max_refresh_attempts
    
    def run_scan(self, manga_url):
        manga_title, base_url = self.scraper.get_info_from_chapter_page(manga_url)
        if not manga_title: return [], "Unknown Manga", None
        chapters = self.scraper.get_chapters_from_dropdown(base_url)
        for i, c in enumerate(chapters): c['index'] = i + 1
        return chapters, manga_title, base_url

    def _scroll_to_bottom_and_wait(self):
        print("    [i] Scrolling page to load all images...")
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        scroll_attempts = 0
        max_scroll_attempts = 50  # Increase max scroll attempts
        
        for scroll_attempts in range(max_scroll_attempts):
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)  # Increase post-scroll wait time from 2s to 3s
            
            # Check if images are loading
            try:
                loading_images = self.driver.find_elements(By.CSS_SELECTOR, "img[src*='loading'], img[data-src], img[src='']")
                if loading_images:
                    print(f"    [i] Detected {len(loading_images)} images still loading, continuing to wait...")
                    time.sleep(5)  # Additional 5s to allow image loading
            except:
                pass
            
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                # Re-check if any images still loading
                try:
                    loading_images = self.driver.find_elements(By.CSS_SELECTOR, "img[src*='loading'], img[data-src], img[src='']")
                    if not loading_images:
                        break
                    else:
                        print(f"    [i] {len(loading_images)} images still loading, waiting...")
                        time.sleep(3)
                except:
                    break
            last_height = new_height
        
        # Final wait to ensure all images have loaded
        print("    [i] Page scroll completed, waiting for final image loads...")
        time.sleep(8)  # Increase final wait time
        
        # Check again and wait for any remaining loading images
        try:
            loading_images = self.driver.find_elements(By.CSS_SELECTOR, "img[src*='loading'], img[data-src], img[src='']")
            if loading_images:
                print(f"    [i] Final waiting for {len(loading_images)} images to finish loading...")
                time.sleep(10)  # Additional 10s
        except:
            pass
            
        print("    [✓] Page scrolled to bottom, image loading wait completed.")

    def scan_images_on_page(self):
        self._scroll_to_bottom_and_wait()
        print("    [i] Intelligently scanning page to extract manga image elements...")

        # 尝试多次扫描，每次间隔等待
        max_retries = 3
        for retry in range(max_retries):
            if retry > 0:
                print(f"    [i] 第 {retry + 1} 次重试扫描...")
                time.sleep(5)  # 重试前等待5秒
            
            # --- New, more robust selection strategy based on user feedback ---
            primary_selector = ".reading-content img.wp-manga-chapter-img"
            img_elements = []
            try:
                img_elements = self.driver.find_elements(By.CSS_SELECTOR, primary_selector)
            except Exception as e:
                print(f"    [!] Error finding primary selector '{primary_selector}': {e}")

            if img_elements:
                print(f"    [+] Using primary selector '{primary_selector}' found {len(img_elements)} image elements.")
                break
            else:
                print(f"    [!] Attempt {retry + 1}: primary selector found no images, falling back to generic container scan...")
                container_selectors = [".reading-content", ".read-container", "div.chapter-c", ".chapter-content", ".manga-reader"]
                for selector in container_selectors:
                    try:
                        container = self.driver.find_element(By.CSS_SELECTOR, selector)
                        elements = container.find_elements(By.TAG_NAME, 'img')
                        if elements:
                            print(f"    [+] Found {len(elements)} image elements in container '{selector}'.")
                            img_elements = elements
                            break
                    except:
                        continue
                
                if img_elements:
                    break
        
        if not img_elements:
            print("    [!] After multiple attempts, no image elements were found on the page.")
            return []

        # --- Final, simplified extraction. We trust the selectors and do not filter by visibility/size. ---
        final_images = []
        for i, element in enumerate(img_elements):
            try:
                img_data = element.get_attribute('src') or element.get_attribute('data-src')
                # Basic sanity check for valid image data/URL.
                if img_data and 'gif' not in img_data and 'data:image/svg+xml' not in img_data:
                    # We trust the selector and no longer check .is_displayed() or .size, as they are unreliable.
                    final_images.append({'element': element, 'index': i, 'size': {}, 'data': img_data})
            except StaleElementReferenceException:
                continue
        
        print(f"    [+] Finally extracted {len(final_images)} valid manga images.")
        return final_images

    def scan_images_with_refresh(self, chapter_url):
        """Scan images, automatically refresh and retry on failure"""
        for refresh_attempt in range(self.max_refresh_attempts + 1):
            if refresh_attempt > 0:
                print(f"    [🔄] Refresh attempt {refresh_attempt}/{self.max_refresh_attempts}...")
                try:
                    self.driver.refresh()
                    print(f"    [i] Page refreshed, waiting to reload...")
                    time.sleep(5)  # 刷新后等待页面重新加载
                except Exception as e:
                    print(f"    [!] Page refresh failed: {e}")
                    continue
            
            print(f"    [i] Scan attempt {refresh_attempt + 1}/{self.max_refresh_attempts + 1}...")
            infos = self.scan_images_on_page()
            if infos:
                if refresh_attempt > 0:
                    print(f"    [✓] Successfully found images on attempt {refresh_attempt + 1}!")
                return infos
            else:
                print(f"    [!] Attempt {refresh_attempt + 1} found no images")
                if refresh_attempt < self.max_refresh_attempts:
                    print(f"    [i] Preparing to refresh the page for attempt {refresh_attempt + 2}...")
                    time.sleep(3)  # 刷新前等待3秒
        
        print(f"    [!] After {self.max_refresh_attempts + 1} attempts (including {self.max_refresh_attempts} refreshes), still unable to find images")
        return []

class ImageProcessor:
    def analyze_image_layout(self, image_files):
        # 默认返回单列布局
        return {'layout': 'vertical', 'cols': 1, 'direction': 'ltr'}

    def stitch_image_tiles(self, image_files, output_path_base, stitch_info, max_height_px=10000):
        # 单列布局不需要拼接，直接返回成功
        return True, "单列布局，无需拼接。", []

    def remove_original_images(self, files):
        # 不删除原始图片
        pass

class DownloadPipeline:
    def __init__(self, scanner, processor, tracker):
        self.scanner = scanner
        self.processor = processor
        self.tracker = tracker
        self.enable_processing = True # This will be set by the main function
        self.errors = []
    
    def download_image(self, data, path, session, max_retries=3):
        for attempt in range(max_retries):
            try:
                if data.startswith('data:image'):
                    header, encoded = data.split(',', 1)
                    encoded += '=' * (-len(encoded) % 4)
                    path.write_bytes(base64.b64decode(encoded))
                    return {'status': 'success', 'path': path}
                else:
                    r = session.get(data, stream=True, timeout=20)
                    r.raise_for_status()
                    with open(path, 'wb') as f:
                        for chunk in r.iter_content(8192): f.write(chunk)
                    return {'status': 'success', 'path': path}
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"        [!] Image download failed, retry {attempt + 1}: {str(e)[:50]}...")
                    time.sleep(2)  # 重试前等待2秒
                else:
                    return {'status': 'failed', 'error': str(e)}
        return {'status': 'failed', 'error': 'Max retries exceeded'}

    def process_chapters(self, chapters, manga_path, base_url, progress_data):
        session = requests.Session()
        session.headers.update({'Referer': base_url}) 

        for chapter in chapters:
            chapter_display_name = f"{chapter['index']:03d} - {chapter['name']}"
            file_safe_chapter_name = f"{chapter['index']:03d}_{re.sub(r'[^a-zA-Z0-9]+', '', chapter['name'])}"
            
            # --- New JSON-based completion check ---
            if manga_path.name in progress_data and \
               chapter_display_name in progress_data[manga_path.name]['chapters'] and \
               progress_data[manga_path.name]['chapters'][chapter_display_name]['status'] == 'completed':
                print(f"\n[*] ({chapter['index']}/{len(chapters)}) [✓] Marked as completed in info.json, skipping: {chapter_display_name}")
                continue

            print(f"\n[*] ({chapter['index']}/{len(chapters)}) Checking: {chapter_display_name}")

            path = manga_path / chapter_display_name

            try:
                self.scanner.driver.get(chapter['url'])
                # Wait for basic page elements to load
                time.sleep(3)
                infos = self.scanner.scan_images_with_refresh(chapter['url'])

                if not infos:
                    msg = "After multiple refresh attempts, no images were found; could be a network issue or page structure change."
                    print(f"    [!] {msg}")
                    self.tracker.add_error(chapter_display_name, msg)
                    # Remove chapter folder and reset status
                    if path.exists() and path.is_dir():
                        shutil.rmtree(path)
                    if manga_path.name in progress_data and 'chapters' in progress_data[manga_path.name]:
                        progress_data[manga_path.name]['chapters'][chapter_display_name]['status'] = 'pending'
                    continue

                if len(infos) < 20:
                    msg = f"Found only {len(infos)} images; content may be incomplete."
                    print(f"    [!] {msg}")
                    self.tracker.add_warning(chapter_display_name, msg)
                
                path.mkdir(exist_ok=True, parents=True)
                
                paths, failed = [], []
                with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                    future_map = {executor.submit(self.download_image, info['data'], path / f"{info['index']:04d}.jpg", session): info for info in infos}
                    for future in concurrent.futures.as_completed(future_map):
                        res, info = future.result(), future_map[future]
                        if res['status'] == 'success':
                            paths.append(res['path'])
                        else:
                            failed.append(info)
                
                print(f"    [i] Download finished (with up to 3 retries). Success {len(paths)}, Failed {len(failed)}.")
                
                # 检查是否有下载失败的图片
                if failed:
                    print(f"    [!] {len(failed)} images failed to download (retried 3 times). Marking chapter as failed and cleaning up...")
                    # 记录失败的图片
                    for info in failed:
                        self.tracker.add_error(chapter_display_name, f"Image download failed (retried 3 times): {info.get('data', 'unknown')}")
                    
                    # Remove chapter folder and reset status
                    if path.exists() and path.is_dir():
                        shutil.rmtree(path)
                    if manga_path.name in progress_data and 'chapters' in progress_data[manga_path.name]:
                        progress_data[manga_path.name]['chapters'][chapter_display_name]['status'] = 'pending'
                    continue
                
                # Only mark as completed when all images are successfully downloaded
                if len(paths) == len(infos):
                    print(f"    [✓] All {len(paths)} images downloaded successfully. Chapter completed.")
                    update_progress(manga_path, chapter_display_name, 'completed', progress_data)
                    save_progress(manga_path, progress_data)
                else:
                    print(f"    [!] Image download incomplete: expected {len(infos)} , actual {len(paths)}")
                    print(f"    [!] Marking chapter as failed and cleaning up...")
                    # 记录错误
                    self.tracker.add_error(chapter_display_name, f"Image download incomplete: expected {len(infos)} , actual {len(paths)}")
                    
                    # 删除章节文件夹并重置状态
                    if path.exists() and path.is_dir():
                        shutil.rmtree(path)
                    if manga_path.name in progress_data and 'chapters' in progress_data[manga_path.name]:
                        progress_data[manga_path.name]['chapters'][chapter_display_name]['status'] = 'pending'
                        
            except Exception as e:
                print(f"    [!] Error while processing chapter: {e}")
                self.tracker.add_error(chapter_display_name, str(e))
                # 删除章节文件夹并重置状态
                if path.exists() and path.is_dir():
                    shutil.rmtree(path)
                if manga_path.name in progress_data and 'chapters' in progress_data[manga_path.name]:
                    progress_data[manga_path.name]['chapters'][chapter_display_name]['status'] = 'pending'

def update_progress(manga_path, chapter_name, status, progress_data):
    """Updates the status of a chapter in the progress data."""
    manga_title = manga_path.name
    if manga_title not in progress_data:
        progress_data[manga_title] = {'chapters': {}}
    
    progress_data[manga_title]['chapters'][chapter_name] = {'status': status}

def save_progress(manga_path, progress_data):
    """Saves the progress data to info.json file."""
    manga_title = manga_path.name
    if manga_title in progress_data:
        info_file = manga_path / 'info.json'
        with open(info_file, 'w', encoding='utf-8') as f:
            json.dump(progress_data.get(manga_title, {}), f, indent=4, ensure_ascii=False)

def main():
    config = load_config('https://bakamh.com/manga/be-be/c-1/', 'manga_output')
    url = input(f"1. URL [{config['url']}]: ") or config['url']
    path_str = input(f"2. Root directory [{config['path']}]: ") or config['path']
    
    # Use timed input to get number of refresh retries
    max_refresh_input = get_timed_input(f"3. Page refresh retry count [5] (input within 5s, default if timeout): ", 5)
    if max_refresh_input is None:
        max_refresh = 5
        print(f"[*] Using default refresh count: {max_refresh}")
    else:
        try:
            max_refresh = int(max_refresh_input)
        except ValueError:
            max_refresh = 5
            print(f"[!] Invalid input, using default refresh count: {max_refresh}")
    
    save_config({'url': url, 'path': path_str})

    driver = None
    tracker = ErrorTracker()
    progress_data = {}
    manga_path = None # Define here for finally block

    try:
        options = uc.ChromeOptions()
        options.add_argument('--no-sandbox')
        driver = uc.Chrome(options=options)
        
        scanner = ChapterScanPipeline(driver, max_refresh_attempts=max_refresh)
        chapters, title, base_url = scanner.run_scan(url)
        if not chapters: 
            tracker.add_error("Initialization", "Failed to retrieve any chapter list.")
            return

        manga_path = Path(path_str) / title
        manga_path.mkdir(exist_ok=True, parents=True)
        tracker.set_manga_path(manga_path)
        
        # Load or initialize progress from info.json
        info_file = manga_path / 'info.json'
        if info_file.exists():
            with open(info_file, 'r', encoding='utf-8') as f:
                try:
                    progress_data[title] = json.load(f)
                except json.JSONDecodeError:
                    pass # Will be handled below
        
        # Ensure base structure exists and add new chapters
        if title not in progress_data or 'chapters' not in progress_data[title]:
             progress_data[title] = {'title': title, 'url': base_url, 'chapters': {}}
        
        existing_chapters = progress_data[title]['chapters']
        for c in chapters:
            chapter_display_name = f"{c['index']:03d} - {c['name']}"
            if chapter_display_name not in existing_chapters:
                existing_chapters[chapter_display_name] = {'status': 'pending'}

        df_data = []
        for c in chapters:
            chapter_display_name = f"{c['index']:03d} - {c['name']}"
            status = progress_data.get(title, {}).get('chapters', {}).get(chapter_display_name, {}).get('status', 'pending')
            df_data.append({"Index": c['index'], "Chapter Name": c['name'], "Status": status})
        
        df = pd.DataFrame(df_data)
        print(df.to_string(index=False))

        selection = get_timed_input("\nSelect chapters (e.g., 1, 3-5, all) [all]: ", 30) or 'all'
        
        to_dl = [chapters[i-1] for i in parse_chapter_selection(selection, len(chapters))]
        
        print(f"\n[*] Starting image processing (single-column layout, preserve original images).")
        print(f"[*] Page refresh retry count set to: {max_refresh}")
        print(f"[*] If the page fails to load, it will automatically refresh up to {max_refresh} times")
        proc = True
        
        pipeline = DownloadPipeline(scanner, ImageProcessor(), tracker)
        pipeline.enable_processing = proc # Set enable_processing for the pipeline
        pipeline.process_chapters(to_dl, manga_path, base_url, progress_data)

    except Exception as e:
        tracker.add_error("Fatal Error", str(e))
        print(f"An error occurred: {e}")
    finally:
        if driver: driver.quit()
        # Save final progress state
        if manga_path and progress_data:
            save_progress(manga_path, progress_data)

        tracker.print_summary(progress_data)

if __name__ == '__main__':
    main()
