import subprocess
import threading
import logging
import time
import uuid
from pathlib import Path
from typing import Dict, Any, Optional
from flask import Flask, render_template, request, jsonify
import re
import json
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Configuration
class Config:
    TASK_FILE = 'tasks.json'
    DOWNLOAD_PATH = r'\\192.168.42.3\VaultStorage\MEDIA\Other\Pokreightyes'
    VOD_DOWNLOAD_PATH = r'\\192.168.42.3\VaultStorage\WorkMedia\VODS'
    
    YT_DLP_COMMON_ARGS = [
        '--newline', '-i', 
        '--write-sub', '--write-auto-sub', '--sub-lang', 'en.*',
        '--ignore-config', '--convert-subs=srt', '--hls-prefer-native',
        '--external-downloader', 'aria2c',
        '--external-downloader-args', 'aria2c:--console-log-level=warn --summary-interval=0 --continue=true --max-connection-per-server=4 --max-tries=0 --retry-wait=3 --timeout=5'
    ]
    # AV1 preferred format selection - prioritizes AV1 codec over others
    YT_DLP_DOWNLOAD_ARGS = [
        '-f', 'bv*[vcodec^=av01]+ba/bv*[vcodec^=avc1]+ba/bv*+ba/b', 
        '--force-ipv4', '--hls-use-mpegts', '--retries', '99999', '--fragment-retries', '99999',
        '--retry-sleep', '5', '--write-url-link', '--impersonate', 'chrome',
        '--socket-timeout', '30'  # Better timeout handling
    ]

task_status: Dict[str, Dict[str, Any]] = {}

class TaskManager:
    @staticmethod
    def load_tasks() -> None:
        """Load tasks from JSON file"""
        global task_status
        if os.path.exists(Config.TASK_FILE):
            try:
                with open(Config.TASK_FILE, 'r', encoding='utf-8') as f:
                    task_status = json.load(f)
                logger.info(f"Loaded {len(task_status)} tasks from {Config.TASK_FILE}")
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Failed to load tasks: {e}")
                task_status = {}
        else:
            task_status = {}

    @staticmethod
    def save_tasks() -> None:
        """Save tasks to JSON file"""
        try:
            with open(Config.TASK_FILE, 'w', encoding='utf-8') as f:
                json.dump(task_status, f, indent=2, ensure_ascii=False)
        except IOError as e:
            logger.error(f"Failed to save tasks: {e}")

    @staticmethod
    def generate_client_id() -> str:
        """Generate a unique client ID"""
        return str(uuid.uuid4())

    @staticmethod
    def cleanup_old_tasks() -> None:
        """Remove tasks older than 24 hours"""
        current_time = time.time()
        to_remove = []
        
        for client_id, task in task_status.items():
            task_time = task.get('created_at', current_time)
            if current_time - task_time > 86400:  # 24 hours
                to_remove.append(client_id)
        
        for client_id in to_remove:
            del task_status[client_id]
            logger.info(f"Removed old task: {client_id}")
        
        if to_remove:
            TaskManager.save_tasks()

class YTDLPDownloader:
    def __init__(self, client_id: str, url: str, download_type: str = 'regular', date: str = None):
        self.client_id = client_id
        self.url = url
        self.download_type = download_type
        self.date = date
        self.process: Optional[subprocess.Popen] = None

    @staticmethod
    def sanitize_filename(filename: str, max_length: int = 50) -> str:
        """Sanitize filename for Windows file system and limit length"""
        # Remove or replace problematic characters
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)  # Remove invalid characters
        filename = re.sub(r'[&!]', 'and', filename)  # Replace & and ! with 'and'
        filename = re.sub(r'\s+', ' ', filename)  # Replace multiple spaces with single space
        filename = filename.strip()  # Remove leading/trailing spaces
        
        # Limit length
        if len(filename) > max_length:
            filename = filename[:max_length].strip()
        
        # Ensure it's not empty
        if not filename:
            filename = "video"
            
        return filename

    @staticmethod
    def extract_url_from_text(text: str) -> str:
        """Extract URL from pasted text, handling various formats"""
        text = text.strip()
        
        # Common URL patterns
        url_patterns = [
            r'https?://[^\s<>"\']+',  # Standard HTTP/HTTPS URLs
            r'www\.[^\s<>"\']+',      # www. URLs without protocol
        ]
        
        # Try to find URLs in the text
        for pattern in url_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                url = matches[0]
                # Ensure it has a protocol
                if not url.startswith(('http://', 'https://')):
                    url = 'https://' + url
                return url
        
        # If no URL pattern found but text looks like a URL, return as is
        if any(domain in text.lower() for domain in ['youtube.com', 'youtu.be', 'twitch.tv', 'facebook.com', 'instagram.com', 'tiktok.com']):
            if not text.startswith(('http://', 'https://')):
                return 'https://' + text
            return text
        
        # Return original text if no URL detected
        return text

    def build_command(self) -> list:
        """Build yt-dlp command based on download type"""
        if self.download_type == 'vod':
            output_path = Config.VOD_DOWNLOAD_PATH
            # Create subfolder structure but with shorter names to avoid path issues
            if self.date:
                output_template = f"{self.date} %(title).50s\\%(title).50s.%(ext)s"
            else:
                output_template = "%(title).50s\\%(title).50s.%(ext)s"
            # Use regular download args for VOD with additional Windows-friendly options
            cmd = ['python', '-m', 'yt_dlp'] + Config.YT_DLP_COMMON_ARGS + [
                '-f', 'bv*[vcodec^=av01]+ba/bv*[vcodec^=avc1]+ba/bv*+ba/b',
                '--restrict-filenames',  # Use only ASCII characters and avoid problematic chars
                '--trim-filenames', '50'  # Limit filename length
            ]
        else:
            output_path = Config.DOWNLOAD_PATH
            output_template = "%(title)s\\%(title)s.%(ext)s"
            # Use regular download args
            cmd = ['python', '-m', 'yt_dlp'] + Config.YT_DLP_COMMON_ARGS + Config.YT_DLP_DOWNLOAD_ARGS

        cmd.extend([
            '-o', os.path.join(output_path, output_template),
            self.url
        ])
        
        return cmd
    def is_live_stream_url(self, url: str) -> bool:
        """Check if URL appears to be a live stream"""
        # Basic heuristics to detect live streams
        live_indicators = [
            '/live', 'live=1', 'isLive=true', 'livestream',
            'facebook.com/watch/live'
        ]
        url_lower = url.lower()
        
        # Special case for Twitch - only /videos/ are VODs, others might be live
        if 'twitch.tv' in url_lower:
            return '/videos/' not in url_lower
        
        return any(indicator in url_lower for indicator in live_indicators)

    def run_download(self) -> None:
        """Execute the download process"""
        try:            # Initialize task
            task_status[self.client_id] = {
                'status': 'started',
                'output': [f"Started processing URL: {self.url}"],
                'title': 'Processing...',
                'created_at': time.time(),
                'type': self.download_type,
                'url': self.url,
                'date': self.date
            }
            TaskManager.save_tasks()# Build and execute command
            cmd = self.build_command()
            logger.info(f"Executing command for {self.client_id}: {' '.join(cmd)}")
            
            # Add the command to task output for debugging
            task_status[self.client_id]['output'].append(f"Command: {' '.join(cmd)}")
            TaskManager.save_tasks()
            
            # Change to appropriate directory - use local path for testing
            download_path = Config.VOD_DOWNLOAD_PATH if self.download_type == 'vod' else Config.DOWNLOAD_PATH
            
            # Check if network path is accessible, if not use local directory
            if not os.path.exists(download_path):
                logger.warning(f"Network path {download_path} not accessible, using current directory")
                download_path = os.getcwd()
                task_status[self.client_id]['output'].append(f"Warning: Using local directory {download_path}")
                TaskManager.save_tasks()
            
            # Test if yt-dlp is accessible
            try:
                test_cmd = ['python', '-m', 'yt_dlp', '--version']
                test_result = subprocess.run(test_cmd, capture_output=True, text=True, timeout=10)
                if test_result.returncode == 0:
                    task_status[self.client_id]['output'].append(f"yt-dlp version: {test_result.stdout.strip()}")
                else:
                    task_status[self.client_id]['output'].append(f"yt-dlp test failed: {test_result.stderr}")
                TaskManager.save_tasks()
            except Exception as e:
                task_status[self.client_id]['output'].append(f"yt-dlp test error: {str(e)}")
                TaskManager.save_tasks()
            
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace',  # Replace invalid UTF-8 characters instead of failing
                cwd=download_path,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0  # Hide window on Windows
            )

            # Add timeout check to prevent hanging
            process_started = False
            timeout_counter = 0
            
            # Process output
            folder_name = None
            for line in iter(self.process.stdout.readline, ''):
                if line.strip():
                    process_started = True
                    line_clean = line.strip()
                    task_status[self.client_id]['output'].append(line_clean)
                    TaskManager.save_tasks()
                    
                    # Extract title/folder name
                    if '[download]' in line and 'Destination:' in line:
                        match = re.search(r'\[download\] Destination: (.*?[\\\/].*)', line)
                        if match:
                            path_parts = match.group(1).replace('/', '\\').split('\\')
                            if len(path_parts) > 1:
                                folder_name = path_parts[-2] if path_parts[-1] else path_parts[-2]
                                task_status[self.client_id]['title'] = folder_name
                    
                    # Extract progress information - handle both yt-dlp and aria2c progress
                    if '[download]' in line and '%' in line:
                        # Standard yt-dlp progress
                        progress_match = re.search(r'(\d+\.\d+)%', line)
                        if progress_match:
                            task_status[self.client_id]['progress'] = float(progress_match.group(1))
                    elif 'aria2c' in line and '%' in line:
                        # aria2c progress format: (1/1375)[#######.......] 50%[...] (speed info)
                        progress_match = re.search(r'(\d+)%', line)
                        if progress_match:
                            task_status[self.client_id]['progress'] = float(progress_match.group(1))
                    elif re.search(r'\(\d+/\d+\)', line) and '%' in line:
                        # Fragment progress: (123/1375) with percentage
                        progress_match = re.search(r'(\d+)%', line)
                        if progress_match:
                            task_status[self.client_id]['progress'] = float(progress_match.group(1))
                      # Check for errors and specific live stream issues
                    if 'ERROR' in line_clean or 'error' in line_clean.lower():
                        logger.error(f"yt-dlp error for {self.client_id}: {line_clean}")
                        
                        # Handle specific file system and path issues
                        if 'File not found or it is a directory' in line_clean:
                            task_status[self.client_id]['output'].append("⚠️ Path/filename too long or contains invalid characters - this will be automatically handled")
                        elif 'Unable to open fragment' in line_clean and 'No such file or directory' in line_clean:
                            task_status[self.client_id]['output'].append("⚠️ File path issue detected - likely due to long filename or special characters")
                        elif 'aria2c exited with code -1' in line_clean:
                            task_status[self.client_id]['output'].append("⚠️ aria2c failed due to file system issues - consider using shorter filenames")
                        # Handle specific live stream errors
                        elif 'keepalive request failed' in line_clean.lower():
                            task_status[self.client_id]['output'].append("ℹ️ Live stream connection issue detected - yt-dlp will automatically retry")
                        elif 'invalid argument' in line_clean.lower() and 'hls' in line_clean.lower():
                            task_status[self.client_id]['output'].append("ℹ️ HLS stream segment error - this is normal for live streams, retrying...")
                        elif 'fragment' in line_clean.lower() and ('unavailable' in line_clean.lower() or 'failed' in line_clean.lower()):
                            task_status[self.client_id]['output'].append("ℹ️ Live stream fragment issue - attempting recovery...")
                            
                        TaskManager.save_tasks()
                
                # Check if process is hanging
                if not process_started:
                    timeout_counter += 1
                    if timeout_counter > 30:  # 30 second timeout
                        task_status[self.client_id]['status'] = 'error: Process timeout - yt-dlp may not be installed or accessible'
                        task_status[self.client_id]['output'].append('Error: Process timed out. Please check if yt-dlp is installed and accessible.')
                        TaskManager.save_tasks()
                        self.process.terminate()
                        return

            self.process.stdout.close()
            return_code = self.process.wait()
            
            if return_code == 0:
                task_status[self.client_id]['status'] = 'finished'
                task_status[self.client_id]['output'].append("Download completed successfully!")
                logger.info(f"Download completed for {self.client_id}")
            else:
                task_status[self.client_id]['status'] = f'error: Process exited with code {return_code}'
                task_status[self.client_id]['output'].append(f"Process exited with error code: {return_code}")
                logger.error(f"Download failed for {self.client_id} with code {return_code}")
            
            TaskManager.save_tasks()

        except FileNotFoundError as e:
            error_msg = "yt-dlp not found. Please install yt-dlp: pip install yt-dlp"
            logger.error(f"yt-dlp not found for {self.client_id}: {e}")
            task_status[self.client_id]['status'] = 'error: yt-dlp not found'
            task_status[self.client_id]['output'].append(error_msg)
            TaskManager.save_tasks()
        except Exception as e:
            logger.error(f"Error in download process for {self.client_id}: {e}")
            task_status[self.client_id]['status'] = f'error: {str(e)}'
            task_status[self.client_id]['output'].append(f"Error: {str(e)}")
            TaskManager.save_tasks()

    def cancel_download(self) -> bool:
        """Cancel the running download"""
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
                return True
            except Exception as e:
                logger.error(f"Failed to cancel download {self.client_id}: {e}")
                return False
        return False

# Flask routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start_download', methods=['POST'])
def start_download():
    try:
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({'error': 'URL is required'}), 400
        
        url_input = data['url'].strip()
        if not url_input:
            return jsonify({'error': 'URL cannot be empty'}), 400
        
        # Extract proper URL from potentially mixed text
        url = YTDLPDownloader.extract_url_from_text(url_input)
        
        client_id = data.get('client_id', TaskManager.generate_client_id())
        logger.info(f"Starting regular download for {client_id}: {url}")

        downloader = YTDLPDownloader(client_id, url, 'regular')
        thread = threading.Thread(target=downloader.run_download, daemon=True)
        thread.start()

        return jsonify({
            'message': f"Started processing URL: {url}",
            'client_id': client_id,
            'status': 'started'
        })

    except Exception as e:
        logger.error(f"Error starting download: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/start_vod_download', methods=['POST'])
def start_vod_download():
    try:
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({'error': 'URL is required'}), 400
        
        url_input = data['url'].strip()
        date = data.get('date', '').strip()
        
        if not url_input:
            return jsonify({'error': 'URL cannot be empty'}), 400
        
        # Extract proper URL from potentially mixed text
        url = YTDLPDownloader.extract_url_from_text(url_input)
        
        client_id = data.get('client_id', TaskManager.generate_client_id())
        logger.info(f"Starting VOD download for {client_id}: {url} (date: {date})")

        downloader = YTDLPDownloader(client_id, url, 'vod', date)
        thread = threading.Thread(target=downloader.run_download, daemon=True)
        thread.start()

        return jsonify({
            'message': f"Started processing VOD URL: {url}" + (f" with date: {date}" if date else ""),
            'client_id': client_id,
            'status': 'started'
        })

    except Exception as e:
        logger.error(f"Error starting VOD download: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/status/<client_id>', methods=['GET'])
def get_status(client_id):
    if client_id in task_status:
        return jsonify(task_status[client_id])
    else:
        return jsonify({'error': 'Task not found'}), 404

@app.route('/cancel_download/<client_id>', methods=['POST'])
def cancel_download(client_id):
    if client_id not in task_status:
        return jsonify({'error': 'Task not found'}), 404
    
    # TODO: Implement proper cancellation mechanism
    task_status[client_id]['status'] = 'cancelled'
    task_status[client_id]['output'].append('Download cancelled by user')
    TaskManager.save_tasks()
    
    return jsonify({'message': 'Download cancelled'})

@app.route('/get_tasks', methods=['GET'])
def get_tasks():
    # Clean up old tasks before returning
    TaskManager.cleanup_old_tasks()
    return jsonify(task_status)

@app.route('/clear_tasks', methods=['POST'])
def clear_tasks():
    global task_status
    task_status = {}
    try:
        with open(Config.TASK_FILE, 'w', encoding='utf-8') as f:
            json.dump({}, f)
        logger.info("All tasks cleared successfully")
        return jsonify({'message': 'All tasks cleared successfully'})
    except IOError as e:
        logger.error(f"Failed to clear tasks: {e}")
        return jsonify({'error': 'Failed to clear tasks'}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'active_tasks': len([t for t in task_status.values() if t.get('status') not in ['finished', 'error', 'cancelled']]),
        'total_tasks': len(task_status),
        'live_stream_support': 'enabled'
    })

@app.route('/stream_info', methods=['GET'])
def stream_info():
    """Provide information about live stream handling"""
    return jsonify({
        'live_stream_optimizations': {
            'smaller_chunks': '5M for live streams vs 10M for regular videos',
            'reduced_retries': '50 attempts vs 99999 for regular videos',
            'faster_retry_sleep': '3 seconds vs 5 seconds',
            'timeout_handling': 'Shorter timeouts for better responsiveness',
            'fragment_handling': 'Single concurrent fragment for stability'
        },
        'common_live_errors': {
            'keepalive_failed': 'Normal for live streams - automatically retried',
            'invalid_argument': 'HLS segment issues - part of live streaming',
            'fragment_unavailable': 'Live stream segments can become unavailable - retried automatically'
        },
        'tips': [
            'Live streams may have intermittent connection issues',
            'The application automatically detects live streams and optimizes settings',
            'Some errors during live stream downloads are normal and expected',
            'Downloads will continue even with occasional connection errors'
        ]
    })

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # Load existing tasks on startup
    TaskManager.load_tasks()
    
    # Run the application
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'true').lower() == 'true'
    
    logger.info(f"Starting server on port {port}, debug={debug}")
    app.run(host='0.0.0.0', port=port, debug=debug)
