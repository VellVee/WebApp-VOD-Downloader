"""
YT-DLP Web Downloader - Robust Video Download Application
Supports multiple video platforms with aria2c acceleration and AV1 codec preference
"""

import subprocess
import threading
import logging
import time
import uuid
import shutil
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify
import re
import json
import os

# Fix Windows console encoding for emoji support
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass

# Configure logging with rotation
from logging.handlers import RotatingFileHandler

# Create custom handler that handles encoding issues
class SafeStreamHandler(logging.StreamHandler):
    def emit(self, record):
        try:
            super().emit(record)
        except UnicodeEncodeError:
            # Fallback: remove emojis and try again
            record.msg = str(record.msg).encode('ascii', 'ignore').decode('ascii')
            super().emit(record)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s:%(lineno)d] - %(message)s',
    handlers=[
        RotatingFileHandler('app.log', maxBytes=10*1024*1024, backupCount=5, encoding='utf-8'),
        SafeStreamHandler()
    ]
)
logger = logging.getLogger(__name__)


app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', os.urandom(32).hex())
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max request size

# Configuration with validation
class Config:
    """Application configuration with path validation and defaults"""
    TASK_FILE = 'tasks.json'
    DOWNLOAD_PATH = os.environ.get('DOWNLOAD_PATH', r'\\192.168.42.3\VaultStorage\ALL TO SORT')
    VOD_DOWNLOAD_PATH = os.environ.get('VOD_DOWNLOAD_PATH', r'\\192.168.42.3\VaultStorage\WorkMedia\VODS')
    FALLBACK_PATH = os.path.join(os.getcwd(), 'downloads')
    MAX_FILENAME_LENGTH = 50  # Reduced from 80 to handle long network paths
    MAX_TASKS = 50
    TASK_RETENTION_HOURS = 24
    
    # Optimized yt-dlp arguments for best quality with AV1 preference
    YT_DLP_COMMON_ARGS = [
        '--newline',
        '-i',  # Ignore errors
        '--no-warnings',
        # Removed --no-write-url-link as it doesn't exist in yt-dlp
        '--write-sub',
        '--write-auto-sub',
        '--sub-lang', 'en,en-US,en-GB',
        '--embed-subs',
        '--convert-subs=srt',
        # Note: --write-url-link removed due to network path issues, handled manually
        '--ignore-config',
        '--no-mtime',  # Don't use Last-modified header for file timestamp
        '--force-ipv4',
        '--socket-timeout', '30',
        '--retries', '10',
        '--fragment-retries', '10',
        '--retry-sleep', '3',
    ]
    
    # aria2c configuration for optimal download performance with ETA
    ARIA2C_ARGS = (
        'aria2c:'
        '--console-log-level=error '
        '--summary-interval=1 '  # Show progress every second for ETA
        '--continue=true '
        '--max-connection-per-server=16 '
        '--min-split-size=1M '
        '--split=16 '
        '--max-concurrent-downloads=16 '
        '--max-tries=10 '
        '--retry-wait=3 '
        '--timeout=30 '
        '--connect-timeout=30 '
        '--max-file-not-found=5 '
        '--allow-overwrite=false '
        '--auto-file-renaming=true '
        '--file-allocation=none '
    )
    
    # AV1 first, then VP9, then H.265, then H.264 with best audio
    # Format selection prioritizing AV1 codec and highest quality
    FORMAT_STRING = (
        'bestvideo[vcodec^=av01][height>=1080]+bestaudio/'  # AV1 1080p+
        'bestvideo[vcodec^=av01]+bestaudio/'  # Any AV1
        'bestvideo[vcodec=vp9.2][height>=1080]+bestaudio/'  # VP9.2 1080p+
        'bestvideo[vcodec=vp9][height>=1080]+bestaudio/'  # VP9 1080p+
        'bestvideo[vcodec^=hev][height>=1080]+bestaudio/'  # HEVC 1080p+
        'bestvideo[vcodec^=avc][height>=1080]+bestaudio/'  # H.264 1080p+
        'bestvideo+bestaudio/'  # Best video + best audio
        'best'  # Fallback to best combined format
    )
    
    YT_DLP_DOWNLOAD_ARGS = [
        '-f', FORMAT_STRING,
        '--merge-output-format', 'mkv',  # MKV for best compatibility
        '--external-downloader', 'aria2c',
        '--external-downloader-args', ARIA2C_ARGS,
        '--embed-thumbnail',
        '--embed-metadata',
        '--embed-chapters',
    ]
    
    @classmethod
    def validate_paths(cls) -> None:
        """Validate and create download paths if needed"""
        for path in [cls.DOWNLOAD_PATH, cls.VOD_DOWNLOAD_PATH]:
            try:
                if not os.path.exists(path):
                    logger.warning(f"Path not accessible: {path}, will use fallback")
            except Exception as e:
                logger.error(f"Error checking path {path}: {e}")
        
        # Ensure fallback path exists
        os.makedirs(cls.FALLBACK_PATH, exist_ok=True)
        logger.info(f"Fallback download path: {cls.FALLBACK_PATH}")
    
    @classmethod
    def get_download_path(cls, download_type: str = 'regular') -> str:
        """Get appropriate download path with fallback"""
        target_path = cls.VOD_DOWNLOAD_PATH if download_type == 'vod' else cls.DOWNLOAD_PATH
        
        try:
            if os.path.exists(target_path) and os.access(target_path, os.W_OK):
                return target_path
        except Exception as e:
            logger.error(f"Error accessing {target_path}: {e}")
        
        logger.warning(f"Using fallback path for {download_type} download")
        return cls.FALLBACK_PATH


task_status: Dict[str, Dict[str, Any]] = {}
active_processes: Dict[str, 'YTDLPDownloader'] = {}
_last_save_time = 0
_save_lock = threading.Lock()

class DependencyChecker:
    """Check for required external dependencies"""
    
    @staticmethod
    def check_yt_dlp() -> Tuple[bool, str]:
        """Check if yt-dlp is installed and get version"""
        try:
            result = subprocess.run(
                ['yt-dlp', '--version'],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            if result.returncode == 0:
                version = result.stdout.strip()
                logger.info(f"yt-dlp found: {version}")
                return True, version
            return False, "yt-dlp command failed"
        except FileNotFoundError:
            logger.error("yt-dlp not found in PATH")
            return False, "yt-dlp not found"
        except Exception as e:
            logger.error(f"Error checking yt-dlp: {e}")
            return False, str(e)
    
    @staticmethod
    def check_aria2c() -> Tuple[bool, str]:
        """Check if aria2c is installed and get version"""
        try:
            result = subprocess.run(
                ['aria2c', '--version'],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            if result.returncode == 0:
                # Extract version from first line
                version = result.stdout.split('\n')[0]
                logger.info(f"aria2c found: {version}")
                return True, version
            return False, "aria2c command failed"
        except FileNotFoundError:
            logger.error("aria2c not found in PATH")
            return False, "aria2c not found"
        except Exception as e:
            logger.error(f"Error checking aria2c: {e}")
            return False, str(e)
    
    @staticmethod
    def check_all() -> Dict[str, Any]:
        """Check all dependencies"""
        yt_dlp_ok, yt_dlp_info = DependencyChecker.check_yt_dlp()
        aria2c_ok, aria2c_info = DependencyChecker.check_aria2c()
        
        return {
            'yt_dlp': {'installed': yt_dlp_ok, 'info': yt_dlp_info},
            'aria2c': {'installed': aria2c_ok, 'info': aria2c_info},
            'all_ok': yt_dlp_ok and aria2c_ok
        }


class TaskManager:
    """Manage task persistence and lifecycle with error handling"""
    
    @staticmethod
    def load_tasks() -> None:
        """Load tasks from JSON file with error recovery"""
        global task_status
        if os.path.exists(Config.TASK_FILE):
            try:
                with open(Config.TASK_FILE, 'r', encoding='utf-8') as f:
                    task_status = json.load(f)
                logger.info(f"Loaded {len(task_status)} tasks from {Config.TASK_FILE}")
                
                # Clean up corrupted tasks
                TaskManager._validate_tasks()
            except json.JSONDecodeError as e:
                logger.error(f"Corrupted task file, backing up and starting fresh: {e}")
                try:
                    backup_file = f"{Config.TASK_FILE}.backup.{int(time.time())}"
                    shutil.copy2(Config.TASK_FILE, backup_file)
                    logger.info(f"Backed up corrupted file to {backup_file}")
                except Exception as be:
                    logger.error(f"Could not backup corrupted file: {be}")
                task_status = {}
            except Exception as e:
                logger.error(f"Failed to load tasks: {e}")
                task_status = {}
        else:
            task_status = {}
            logger.info("No existing task file, starting fresh")
    
    @staticmethod
    def _validate_tasks() -> None:
        """Validate loaded tasks and remove invalid ones"""
        global task_status
        invalid_tasks = []
        
        for client_id, task in task_status.items():
            # Check required fields
            if not isinstance(task, dict):
                invalid_tasks.append(client_id)
                continue
            
            # Ensure required fields exist
            required_fields = ['status', 'output', 'created_at']
            if not all(field in task for field in required_fields):
                invalid_tasks.append(client_id)
                continue
        
        for client_id in invalid_tasks:
            logger.warning(f"Removing invalid task: {client_id}")
            del task_status[client_id]
        
        if invalid_tasks:
            TaskManager.save_tasks(force=True)
    
    @staticmethod
    def save_tasks(force: bool = False) -> bool:
        """Save tasks to JSON file with throttling and error handling"""
        global _last_save_time
        current_time = time.time()
        
        if not force and (current_time - _last_save_time) < 1.0:
            return False
        
        with _save_lock:
            try:
                # Write to temp file first, then rename for atomic operation
                temp_file = f"{Config.TASK_FILE}.tmp"
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(task_status, f, indent=2, ensure_ascii=False)
                
                # Atomic rename
                if os.path.exists(Config.TASK_FILE):
                    os.replace(temp_file, Config.TASK_FILE)
                else:
                    os.rename(temp_file, Config.TASK_FILE)
                
                _last_save_time = current_time
                return True
            except Exception as e:
                logger.error(f"Failed to save tasks: {e}")
                # Try to cleanup temp file
                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                except:
                    pass
                return False
    
    @staticmethod
    def generate_client_id() -> str:
        """Generate a unique client ID"""
        return f"task_{uuid.uuid4().hex[:16]}_{int(time.time())}"
    
    @staticmethod
    def cleanup_old_tasks() -> int:
        """Remove tasks older than retention period"""
        global active_processes
        current_time = time.time()
        retention_seconds = Config.TASK_RETENTION_HOURS * 3600
        to_remove = []
        
        for client_id, task in task_status.items():
            task_time = task.get('created_at', current_time)
            if current_time - task_time > retention_seconds:
                to_remove.append(client_id)
        
        for client_id in to_remove:
            if client_id in active_processes:
                try:
                    active_processes[client_id].cancel_download()
                    del active_processes[client_id]
                except Exception as e:
                    logger.error(f"Error cancelling old task {client_id}: {e}")
            
            del task_status[client_id]
            logger.info(f"Removed old task: {client_id}")
        
        if to_remove:
            TaskManager.save_tasks(force=True)
        
        return len(to_remove)
    
    @staticmethod
    def limit_task_count() -> None:
        """Limit total number of tasks to prevent memory issues"""
        if len(task_status) > Config.MAX_TASKS:
            # Remove oldest finished/error/cancelled tasks
            finished_tasks = [
                (cid, task) for cid, task in task_status.items()
                if task.get('status') in ['finished', 'cancelled'] or 
                task.get('status', '').startswith('error')
            ]
            
            # Sort by creation time
            finished_tasks.sort(key=lambda x: x[1].get('created_at', 0))
            
            # Remove oldest ones
            to_remove = len(task_status) - Config.MAX_TASKS
            for client_id, _ in finished_tasks[:to_remove]:
                logger.info(f"Removing task to maintain limit: {client_id}")
                del task_status[client_id]
            
            TaskManager.save_tasks(force=True)


class URLValidator:
    """Validate and normalize URLs"""
    
    SUPPORTED_DOMAINS = [
        'youtube.com', 'youtu.be', 'twitch.tv', 'facebook.com',
        'instagram.com', 'tiktok.com', 'vimeo.com', 'dailymotion.com',
        'twitter.com', 'x.com', 'reddit.com', 'streamable.com',
        'bilibili.com', 'nicovideo.jp', 'soundcloud.com'
    ]
    
    @staticmethod
    def extract_url(text: str) -> Optional[str]:
        """Extract and validate URL from text"""
        text = text.strip()
        
        # Remove common prefixes that might be copied with URL
        text = re.sub(r'^(url[:\s]+|link[:\s]+)', '', text, flags=re.IGNORECASE)
        
        # URL patterns
        url_pattern = r'https?://[^\s<>"\'{}|\\^`\[\]]+|www\.[^\s<>"\'{}|\\^`\[\]]+'
        
        matches = re.findall(url_pattern, text, re.IGNORECASE)
        if matches:
            url = matches[0]
            # Clean up trailing punctuation
            url = re.sub(r'[.,;:!?)]+$', '', url)
            
            # Ensure protocol
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            return url
        
        # If no pattern match but looks like a domain
        if any(domain in text.lower() for domain in URLValidator.SUPPORTED_DOMAINS):
            if not text.startswith(('http://', 'https://')):
                return 'https://' + text
            return text
        
        return None
    
    @staticmethod
    def is_valid_url(url: str) -> bool:
        """Check if URL is valid and supported"""
        if not url:
            return False
        
        # Basic URL structure check
        url_pattern = r'^https?://[^\s<>"\']+\.[^\s<>"\']+$'
        if not re.match(url_pattern, url):
            return False
        
        # Check if from supported domain (optional - yt-dlp supports many more)
        return True


class FilenameUtils:
    """Utilities for safe filename handling"""
    
    # Windows forbidden characters
    FORBIDDEN_CHARS = r'[<>:"/\\|?*\x00-\x1f]'
    # Additional problematic characters
    REPLACE_CHARS = {
        '&': 'and',
        '#': 'num',
        '@': 'at',
        '!': '',
        '%': 'pct',
    }
    
    @staticmethod
    def sanitize(filename: str, max_length: int = 80) -> str:
        """Sanitize filename for Windows/Linux compatibility"""
        if not filename:
            return "video"
        
        # Remove forbidden characters
        filename = re.sub(FilenameUtils.FORBIDDEN_CHARS, '', filename)
        
        # Replace problematic characters
        for old, new in FilenameUtils.REPLACE_CHARS.items():
            filename = filename.replace(old, new)
        
        # Replace multiple spaces with single space
        filename = re.sub(r'\s+', ' ', filename)
        
        # Remove leading/trailing spaces and dots (Windows issue)
        filename = filename.strip(' .')
        
        # Limit length (reserve space for extension)
        if len(filename) > max_length:
            filename = filename[:max_length].strip(' .')
        
        # Ensure not empty
        if not filename:
            filename = "video"
        
        return filename
    
    @staticmethod
    def create_safe_path(base_path: str, *parts: str) -> str:
        """Create a safe file path with sanitized components"""
        safe_parts = [FilenameUtils.sanitize(part) for part in parts if part]
        return os.path.join(base_path, *safe_parts)


class YTDLPDownloader:
    """Robust video downloader with error handling and progress tracking"""
    
    def __init__(self, client_id: str, url: str, download_type: str = 'regular', date: str = None):
        self.client_id = client_id
        self.url = url
        self.download_type = download_type
        self.date = FilenameUtils.sanitize(date) if date else None
        self.process: Optional[subprocess.Popen] = None
        self.cancelled = False
        self.start_time = time.time()
        self.downloaded_file: Optional[str] = None  # Track downloaded file path
    
    def build_command(self) -> List[str]:
        """Build optimized yt-dlp command"""
        download_path = Config.get_download_path(self.download_type)
        
        # Build output template with reduced filename length for network paths
        # Network paths can be very long, so we limit titles to 50 chars max
        if self.download_type == 'vod' and self.date:
            # For VODs with custom date: Date - Title/Title.ext
            output_template = os.path.join(
                download_path,
                f'{self.date} - %(title).30s',  # Include date and truncated title in folder name
                '%(title).50s.%(ext)s'
            )
        elif self.download_type == 'vod':
            output_template = os.path.join(
                download_path,
                '%(upload_date>%Y-%m-%d)s - %(title).30s',  # Include upload date and truncated title in folder name
                '%(title).50s.%(ext)s'
            )
        else:
            # For regular: Title/Title.ext
            output_template = os.path.join(
                download_path,
                '%(title).50s',
                '%(title).50s.%(ext)s'
            )
        
        # Build command
        cmd = ['yt-dlp'] + Config.YT_DLP_COMMON_ARGS + Config.YT_DLP_DOWNLOAD_ARGS + [
            '-o', output_template,
            '--restrict-filenames',  # ASCII only for compatibility
            '--windows-filenames',  # Windows-safe filenames
            '--trim-filenames', str(Config.MAX_FILENAME_LENGTH),
            # IMPORTANT: Do NOT add --write-url-link here - URL shortcuts are created manually
            # to avoid network path issues. See create_url_shortcut() method.
            self.url
        ]
        
        return cmd
    
    def parse_progress(self, line: str) -> None:
        """Parse progress information from yt-dlp/aria2c output"""
        task = task_status.get(self.client_id, {})
        
        # yt-dlp download progress: [download]  45.2% of 123.45MiB at 2.34MiB/s ETA 00:30
        if '[download]' in line:
            # Extract percentage
            progress_match = re.search(r'(\d+\.?\d*)%', line)
            if progress_match:
                task['progress'] = float(progress_match.group(1))
            
            # Extract file size
            size_match = re.search(r'of\s+([\d.]+\s*[KMGT]i?B)', line)
            if size_match:
                task['file_size'] = size_match.group(1)
            
            # Extract speed
            speed_match = re.search(r'at\s+([\d.]+\s*[KMGT]i?B/s)', line)
            if speed_match:
                task['speed'] = speed_match.group(1)
            
            # Extract ETA
            eta_match = re.search(r'ETA\s+(\d+:\d+(?::\d+)?)', line)
            if eta_match:
                task['eta'] = eta_match.group(1)
            
            # Detect destination to extract title and file path
            if 'Destination:' in line:
                dest_match = re.search(r'Destination:\s+(.+)', line)
                if dest_match:
                    path = dest_match.group(1).strip()
                    # Store the file path for URL shortcut creation
                    self.downloaded_file = path
                    title = os.path.basename(os.path.dirname(path))
                    if title and title != '.':
                        task['title'] = FilenameUtils.sanitize(title, 50)
        
        # aria2c progress
        elif 'aria2' in line.lower() and '%' in line:
            progress_match = re.search(r'(\d+)%', line)
            if progress_match:
                task['progress'] = float(progress_match.group(1))
            
            # Parse aria2c speed format: [DL:1.2MiB/s]
            speed_match = re.search(r'\[DL:([^\]]+)\]', line)
            if speed_match:
                task['speed'] = speed_match.group(1)
        
        # ffmpeg progress (for post-processing)
        elif 'frame=' in line and 'time=' in line:
            time_match = re.search(r'time=(\d+:\d+:\d+\.\d+)', line)
            if time_match:
                task['processing_time'] = time_match.group(1)
            
            speed_match = re.search(r'speed=\s*([\d.]+x)', line)
            if speed_match:
                task['processing_speed'] = speed_match.group(1)
    
    def handle_errors(self, line: str) -> bool:
        """Handle and log errors, return True if critical"""
        line_lower = line.lower()
        
        # Ignore non-critical errors (we handle these ourselves)
        non_critical_patterns = [
            'cannot write internet shortcut',  # We create .url files manually
            'write url link',  # Related to shortcut creation
        ]
        
        for pattern in non_critical_patterns:
            if pattern in line_lower:
                # Silently ignore these, we handle them ourselves
                return False
        
        # Critical errors
        critical_errors = [
            'error: unable to download',
            'error: video not available',
            'error: private video',
            'error: this video is not available',
            'http error 404',
            'http error 403',
        ]
        
        for error in critical_errors:
            if error in line_lower:
                logger.error(f"Critical error for {self.client_id}: {line}")
                return True
        
        # Non-critical warnings
        if 'warning' in line_lower or 'error' in line_lower:
            logger.warning(f"Warning for {self.client_id}: {line}")
            return False
        
        return False
    
    def create_url_shortcut(self, video_path: str) -> bool:
        """Create Windows .url shortcut file for the video"""
        try:
            # Create .url file in same directory as video
            url_file = os.path.splitext(video_path)[0] + '.url'
            
            # Windows .url format
            content = f"""[InternetShortcut]
URL={self.url}
"""
            
            # Try to ensure directory exists
            os.makedirs(os.path.dirname(url_file), exist_ok=True)
            
            # Try with retry mechanism for network locations
            max_retries = 3
            retry_delay = 1  # seconds
            
            for attempt in range(max_retries):
                try:
                    with open(url_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    logger.info(f"Created URL shortcut: {url_file}")
                    return True
                except PermissionError:
                    # Could be a transient network issue - wait and retry
                    if attempt < max_retries - 1:
                        logger.warning(f"Permission error writing .url shortcut, retrying in {retry_delay}s...")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                    else:
                        raise
            
            return False
            
        except Exception as e:
            logger.warning(f"Could not create URL shortcut for {self.client_id}: {e}")
            # Try local fallback if network path failed
            try:
                if '\\\\' in url_file:  # Network path
                    fallback_file = os.path.join(self.config.FALLBACK_PATH, os.path.basename(url_file))
                    with open(fallback_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                    logger.info(f"Created URL shortcut in fallback location: {fallback_file}")
                    return True
            except Exception as fallback_e:
                logger.error(f"Fallback URL shortcut creation also failed: {fallback_e}")
            return False
    
    def run_download(self) -> None:
        """Execute download with comprehensive error handling"""
        global active_processes
        
        try:
            # Register as active
            active_processes[self.client_id] = self
            
            # Initialize task
            task_status[self.client_id] = {
                'status': 'initializing',
                'output': [f"[{datetime.now().strftime('%H:%M:%S')}] Initializing download..."],
                'title': 'Processing...',
                'created_at': time.time(),
                'type': self.download_type,
                'url': self.url,
                'date': self.date,
                'progress': 0,
            }
            TaskManager.save_tasks()
            
            # Validate URL
            if not URLValidator.is_valid_url(self.url):
                raise ValueError(f"Invalid URL: {self.url}")
            
            task_status[self.client_id]['output'].append(f"[{datetime.now().strftime('%H:%M:%S')}] URL validated")
            
            # Build command
            cmd = self.build_command()
            logger.info(f"Command for {self.client_id}: {' '.join(cmd)}")
            task_status[self.client_id]['output'].append(f"[{datetime.now().strftime('%H:%M:%S')}] Starting yt-dlp with aria2c")
            task_status[self.client_id]['status'] = 'starting'
            TaskManager.save_tasks()
            
            # Execute command
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace',
                bufsize=1,  # Line buffered
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            task_status[self.client_id]['status'] = 'downloading'
            output_buffer = []
            last_update = time.time()
            critical_error_found = False
            
            # Process output
            for line in iter(self.process.stdout.readline, ''):
                if self.cancelled:
                    logger.info(f"Download {self.client_id} cancelled by user")
                    break
                
                if not line:
                    break
                
                line_clean = line.strip()
                if not line_clean:
                    continue
                
                output_buffer.append(f"[{datetime.now().strftime('%H:%M:%S')}] {line_clean}")
                
                # Parse progress
                self.parse_progress(line_clean)
                
                # Check for errors
                if self.handle_errors(line_clean):
                    critical_error_found = True
                
                # Update task periodically - more frequent for real-time output
                current_time = time.time()
                if len(output_buffer) >= 2 or (current_time - last_update) >= 0.5:  # Update every 0.5s or 2 lines
                    task_status[self.client_id]['output'].extend(output_buffer)
                    # Keep only last 200 lines for better real-time display
                    if len(task_status[self.client_id]['output']) > 200:
                        task_status[self.client_id]['output'] = task_status[self.client_id]['output'][-200:]
                    output_buffer = []
                    TaskManager.save_tasks()
                    last_update = current_time
            
            # Flush remaining output
            if output_buffer:
                task_status[self.client_id]['output'].extend(output_buffer)
                TaskManager.save_tasks(force=True)
            
            # Get return code
            self.process.stdout.close()
            return_code = self.process.wait(timeout=30)
            
            # Calculate duration
            duration = time.time() - self.start_time
            duration_str = str(timedelta(seconds=int(duration)))
            
            # Update final status
            if self.cancelled:
                task_status[self.client_id]['status'] = 'cancelled'
                task_status[self.client_id]['output'].append(f"[{datetime.now().strftime('%H:%M:%S')}] [CANCELLED] Download cancelled by user")
            elif return_code == 0 and not critical_error_found:
                task_status[self.client_id]['status'] = 'finished'
                task_status[self.client_id]['progress'] = 100
                
                # Create URL shortcut if we have the file path
                if self.downloaded_file:
                    if self.create_url_shortcut(self.downloaded_file):
                        task_status[self.client_id]['output'].append(f"[{datetime.now().strftime('%H:%M:%S')}] [LINK] Created URL shortcut")
                
                task_status[self.client_id]['output'].append(f"[{datetime.now().strftime('%H:%M:%S')}] [SUCCESS] Download completed! (Duration: {duration_str})")
                logger.info(f"Download completed for {self.client_id} in {duration_str}")
            else:
                task_status[self.client_id]['status'] = f'error: Exit code {return_code}'
                task_status[self.client_id]['output'].append(f"[{datetime.now().strftime('%H:%M:%S')}] [ERROR] Download failed with error code {return_code}")
                logger.error(f"Download failed for {self.client_id} with code {return_code}")
            
            TaskManager.save_tasks(force=True)
        
        except subprocess.TimeoutExpired:
            error_msg = "Download process timed out"
            logger.error(f"{error_msg} for {self.client_id}")
            task_status[self.client_id]['status'] = 'error: timeout'
            task_status[self.client_id]['output'].append(f"[{datetime.now().strftime('%H:%M:%S')}] [ERROR] {error_msg}")
            TaskManager.save_tasks(force=True)
        
        except FileNotFoundError:
            error_msg = "yt-dlp not found. Please install: pip install yt-dlp"
            logger.error(f"yt-dlp not found for {self.client_id}")
            task_status[self.client_id]['status'] = 'error: yt-dlp not found'
            task_status[self.client_id]['output'].append(f"[{datetime.now().strftime('%H:%M:%S')}] [ERROR] {error_msg}")
            TaskManager.save_tasks(force=True)
        
        except ValueError as e:
            logger.error(f"Validation error for {self.client_id}: {e}")
            task_status[self.client_id]['status'] = 'error: validation failed'
            task_status[self.client_id]['output'].append(f"[{datetime.now().strftime('%H:%M:%S')}] [ERROR] {str(e)}")
            TaskManager.save_tasks(force=True)
        
        except Exception as e:
            logger.error(f"Unexpected error for {self.client_id}: {e}", exc_info=True)
            task_status[self.client_id]['status'] = f'error: {type(e).__name__}'
            task_status[self.client_id]['output'].append(f"[{datetime.now().strftime('%H:%M:%S')}] [ERROR] Unexpected error: {str(e)}")
            TaskManager.save_tasks(force=True)
        
        finally:
            # Cleanup
            if self.client_id in active_processes:
                del active_processes[self.client_id]
            
            # Ensure process is terminated
            if self.process and self.process.poll() is None:
                try:
                    self.process.terminate()
                    self.process.wait(timeout=5)
                except:
                    try:
                        self.process.kill()
                    except:
                        pass
    
    def cancel_download(self) -> bool:
        """Cancel the running download"""
        self.cancelled = True
        
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=2)
                
                logger.info(f"Successfully cancelled download {self.client_id}")
                return True
            except Exception as e:
                logger.error(f"Failed to cancel download {self.client_id}: {e}")
                return False
        
        return False


# Flask routes with robust error handling
@app.route('/')
def index():
    """Render main page"""
    return render_template('index.html')


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint with dependency status"""
    deps = DependencyChecker.check_all()
    
    return jsonify({
        'status': 'healthy' if deps['all_ok'] else 'degraded',
        'dependencies': deps,
        'active_tasks': len([t for t in task_status.values() 
                           if t.get('status') not in ['finished', 'cancelled'] 
                           and not t.get('status', '').startswith('error')]),
        'total_tasks': len(task_status),
        'active_processes': len(active_processes),
        'config': {
            'max_tasks': Config.MAX_TASKS,
            'retention_hours': Config.TASK_RETENTION_HOURS,
            'download_path': Config.DOWNLOAD_PATH,
            'vod_path': Config.VOD_DOWNLOAD_PATH,
        }
    }), 200 if deps['all_ok'] else 503


@app.route('/start_download', methods=['POST'])
def start_download():
    """Start a regular download"""
    try:
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({'error': 'URL is required'}), 400
        
        url_input = data['url'].strip()
        if not url_input:
            return jsonify({'error': 'URL cannot be empty'}), 400
        
        # Extract and validate URL
        url = URLValidator.extract_url(url_input)
        if not url or not URLValidator.is_valid_url(url):
            return jsonify({'error': 'Invalid URL format'}), 400
        
        # Check task limit
        TaskManager.limit_task_count()
        
        # Generate client ID
        client_id = data.get('client_id', TaskManager.generate_client_id())
        logger.info(f"Starting regular download for {client_id}: {url}")
        
        # Start download in background
        downloader = YTDLPDownloader(client_id, url, 'regular')
        thread = threading.Thread(target=downloader.run_download, daemon=True)
        thread.start()
        
        return jsonify({
            'message': 'Download started',
            'client_id': client_id,
            'status': 'initializing',
            'url': url
        }), 202
    
    except Exception as e:
        logger.error(f"Error starting download: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500


@app.route('/start_vod_download', methods=['POST'])
def start_vod_download():
    """Start a VOD download"""
    try:
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({'error': 'URL is required'}), 400
        
        url_input = data['url'].strip()
        date = data.get('date', '').strip()
        
        if not url_input:
            return jsonify({'error': 'URL cannot be empty'}), 400
        
        # Extract and validate URL
        url = URLValidator.extract_url(url_input)
        if not url or not URLValidator.is_valid_url(url):
            return jsonify({'error': 'Invalid URL format'}), 400
        
        # Validate date if provided
        if date:
            try:
                datetime.strptime(date, '%Y-%m-%d')
            except ValueError:
                return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        
        # Check task limit
        TaskManager.limit_task_count()
        
        # Generate client ID
        client_id = data.get('client_id', TaskManager.generate_client_id())
        logger.info(f"Starting VOD download for {client_id}: {url} (date: {date})")
        
        # Start download in background
        downloader = YTDLPDownloader(client_id, url, 'vod', date)
        thread = threading.Thread(target=downloader.run_download, daemon=True)
        thread.start()
        
        return jsonify({
            'message': 'VOD download started',
            'client_id': client_id,
            'status': 'initializing',
            'url': url,
            'date': date
        }), 202
    
    except Exception as e:
        logger.error(f"Error starting VOD download: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500


@app.route('/status/<client_id>', methods=['GET'])
def get_status(client_id):
    """Get status of a specific download"""
    if client_id in task_status:
        task = task_status[client_id].copy()
        # Add runtime information
        if 'created_at' in task:
            runtime = time.time() - task['created_at']
            task['runtime'] = str(timedelta(seconds=int(runtime)))
        return jsonify(task), 200
    else:
        return jsonify({'error': 'Task not found'}), 404


@app.route('/cancel_download/<client_id>', methods=['POST'])
def cancel_download(client_id):
    """Cancel a running download"""
    if client_id not in task_status:
        return jsonify({'error': 'Task not found'}), 404
    
    # Check if already finished
    status = task_status[client_id].get('status', '')
    if status in ['finished', 'cancelled'] or status.startswith('error'):
        return jsonify({'message': 'Task already completed', 'status': status}), 200
    
    # Try to terminate the process
    if client_id in active_processes:
        downloader = active_processes[client_id]
        if downloader.cancel_download():
            task_status[client_id]['status'] = 'cancelled'
            task_status[client_id]['output'].append(f"[{datetime.now().strftime('%H:%M:%S')}] Download cancelled by user")
            logger.info(f"Successfully cancelled download {client_id}")
        else:
            task_status[client_id]['status'] = 'cancelled'
            task_status[client_id]['output'].append(f"[{datetime.now().strftime('%H:%M:%S')}] Download marked as cancelled")
            logger.warning(f"Could not terminate process for {client_id}")
    else:
        task_status[client_id]['status'] = 'cancelled'
        task_status[client_id]['output'].append(f"[{datetime.now().strftime('%H:%M:%S')}] Download cancelled")
        logger.info(f"Marked task {client_id} as cancelled")
    
    TaskManager.save_tasks(force=True)
    return jsonify({'message': 'Download cancelled', 'status': 'cancelled'}), 200


@app.route('/remove_task/<client_id>', methods=['DELETE', 'POST'])
def remove_task(client_id):
    """Remove a task from the list"""
    global active_processes
    
    if client_id not in task_status:
        return jsonify({'error': 'Task not found'}), 404
    
    # Cancel if still active
    if client_id in active_processes:
        try:
            active_processes[client_id].cancel_download()
            del active_processes[client_id]
            logger.info(f"Cancelled active process for task {client_id}")
        except Exception as e:
            logger.error(f"Error cancelling process for task {client_id}: {e}")
    
    # Remove task
    del task_status[client_id]
    TaskManager.save_tasks(force=True)
    logger.info(f"Task {client_id} removed")
    
    return jsonify({'message': 'Task removed successfully'}), 200


@app.route('/get_tasks', methods=['GET'])
def get_tasks():
    """Get all tasks"""
    # Clean up old tasks
    removed = TaskManager.cleanup_old_tasks()
    if removed > 0:
        logger.info(f"Cleaned up {removed} old tasks")
    
    return jsonify(task_status), 200


@app.route('/clear_tasks', methods=['POST'])
def clear_tasks():
    """Clear all tasks"""
    global task_status, active_processes
    
    # Cancel all active processes
    for client_id in list(active_processes.keys()):
        try:
            active_processes[client_id].cancel_download()
            logger.info(f"Cancelled active download: {client_id}")
        except Exception as e:
            logger.error(f"Error cancelling download {client_id}: {e}")
    
    # Clear dictionaries
    active_processes = {}
    task_status = {}
    
    # Save empty state
    if TaskManager.save_tasks(force=True):
        logger.info("All tasks cleared successfully")
        return jsonify({'message': 'All tasks cleared successfully'}), 200
    else:
        return jsonify({'error': 'Failed to save cleared state'}), 500


@app.route('/info', methods=['GET'])
def get_info():
    """Get application information and supported features"""
    deps = DependencyChecker.check_all()
    
    return jsonify({
        'application': 'YT-DLP Web Downloader',
        'version': '2.0.0',
        'features': {
            'aria2c_acceleration': deps['aria2c']['installed'],
            'av1_codec_priority': True,
            'subtitle_download': True,
            'url_shortcut_saving': True,
            'metadata_embedding': True,
            'thumbnail_embedding': True,
            'chapter_embedding': True,
            'progress_tracking': True,
            'eta_display': True,
            'concurrent_downloads': True,
        },
        'supported_codecs_priority': ['AV1', 'VP9.2', 'VP9', 'HEVC/H.265', 'H.264'],
        'supported_platforms': [
            'YouTube', 'Twitch', 'Facebook', 'Instagram', 'TikTok',
            'Vimeo', 'Dailymotion', 'Twitter/X', 'Reddit', 'SoundCloud',
            'And 1000+ more via yt-dlp'
        ],
        'dependencies': deps,
        'configuration': {
            'max_concurrent_connections': 16,
            'max_tasks': Config.MAX_TASKS,
            'retention_hours': Config.TASK_RETENTION_HOURS,
            'max_filename_length': Config.MAX_FILENAME_LENGTH,
        }
    }), 200


# Error handlers
@app.errorhandler(400)
def bad_request(error):
    return jsonify({'error': 'Bad request', 'message': str(error)}), 400


@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}", exc_info=True)
    return jsonify({'error': 'Internal server error'}), 500


@app.errorhandler(Exception)
def handle_exception(error):
    logger.error(f"Unhandled exception: {error}", exc_info=True)
    return jsonify({
        'error': 'Unexpected error occurred',
        'type': type(error).__name__,
        'message': str(error)
    }), 500



if __name__ == '__main__':
    # Validate configuration
    Config.validate_paths()
    
    # Check dependencies
    logger.info("Checking dependencies...")
    deps = DependencyChecker.check_all()
    
    if not deps['yt_dlp']['installed']:
        logger.error("[X] yt-dlp not found! Install it with: pip install yt-dlp")
        logger.error("    Or download from: https://github.com/yt-dlp/yt-dlp/releases")
    else:
        logger.info(f"[OK] yt-dlp: {deps['yt_dlp']['info']}")
    
    if not deps['aria2c']['installed']:
        logger.warning("[!] aria2c not found! Downloads will be slower.")
        logger.warning("    Install aria2c from: https://github.com/aria2/aria2/releases")
        logger.warning("    Or use: winget install aria2.aria2 (Windows)")
    else:
        logger.info(f"[OK] aria2c: {deps['aria2c']['info']}")
    
    if not deps['all_ok']:
        logger.warning("[!] Some dependencies are missing. Application may not work correctly.")
    
    # Load existing tasks
    logger.info("Loading existing tasks...")
    TaskManager.load_tasks()
    logger.info(f"Loaded {len(task_status)} tasks")
    
    # Get configuration from environment
    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '0.0.0.0')
    debug = os.environ.get('DEBUG', 'false').lower() == 'true'
    
    logger.info("="*60)
    logger.info(f"Starting YT-DLP Web Downloader v2.0.0")
    logger.info(f"Server: http://{host}:{port}")
    logger.info(f"Debug mode: {debug}")
    logger.info(f"Download path: {Config.DOWNLOAD_PATH}")
    logger.info(f"VOD path: {Config.VOD_DOWNLOAD_PATH}")
    logger.info(f"Fallback path: {Config.FALLBACK_PATH}")
    logger.info("="*60)
    
    # Run the application
    try:
        app.run(host=host, port=port, debug=debug, threaded=True)
    except KeyboardInterrupt:
        logger.info("\nShutting down gracefully...")
        # Cancel all active downloads
        for client_id in list(active_processes.keys()):
            try:
                active_processes[client_id].cancel_download()
            except:
                pass
        # Save tasks
        TaskManager.save_tasks(force=True)
        logger.info("Shutdown complete")
    except Exception as e:
        logger.error(f"[X] Fatal error: {e}", exc_info=True)
        raise
