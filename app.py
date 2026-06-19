import os
import sys
import re
import json
import uuid
import time
import subprocess
import threading
import logging
from datetime import datetime
# pyrefly: ignore [missing-import]
from flask import Flask, render_template, request, jsonify

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(BASE_DIR, 'settings.json')
TASKS_FILE = os.path.join(BASE_DIR, 'tasks.json')

DEFAULT_SETTINGS = {
    "default_path": "C:\\Downloads\\YT-DLP_Default" if os.name == 'nt' else os.path.expanduser("~/Downloads/YT-DLP_Default"),
    "vod_path": "C:\\Downloads\\YT-DLP_VODs" if os.name == 'nt' else os.path.expanduser("~/Downloads/YT-DLP_VODs"),
    "admin_password": "admin",
    "port": 5557
}

task_status = {}
active_downloaders = {}
tasks_lock = threading.Lock()

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading settings: {e}")
    return DEFAULT_SETTINGS

def save_settings(settings):
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=4)
        return True
    except Exception as e:
        logger.error(f"Error saving settings: {e}")
        return False

def save_tasks():
    try:
        with tasks_lock:
            status_copy = dict(task_status)
            with open(TASKS_FILE, 'w') as f:
                json.dump(status_copy, f, indent=4)
    except Exception as e:
        logger.error(f"Error saving tasks: {e}")

def load_tasks():
    global task_status
    if os.path.exists(TASKS_FILE):
        try:
            with open(TASKS_FILE, 'r') as f:
                task_status = json.load(f)
            # Reset active statuses on reboot
            for k, v in task_status.items():
                if v['status'] in ['started', 'waiting']:
                    v['status'] = 'error (interrupted)'
        except Exception:
            task_status = {}

class YTDLPRunner:
    def __init__(self, client_id, url, profile, delay_mins=0, date_str=None):
        self.client_id = client_id
        self.url = url
        self.profile = profile # 'default' or 'vod'
        self.delay_mins = int(delay_mins)
        self.date_str = date_str
        self.process = None
        self.cancelled = False

    def build_command(self):
        settings = load_settings()
        base_path = settings.get('vod_path') if self.profile == 'vod' else settings.get('default_path')
        
        if not os.path.exists(base_path):
            try:
                os.makedirs(base_path, exist_ok=True)
            except Exception as e:
                logger.error(f"Failed to create path {base_path}: {e}")

        date_prefix = self.date_str if self.date_str else datetime.now().strftime("%Y-%m-%d")
        
        cmd = [
            sys.executable, '-m', 'yt_dlp',
            '--newline',
            '--progress',
            '--hls-prefer-native',
            '-f', 'bv*+ba/b',
            '--windows-filenames',
            '-O', 'YT-DLP-TITLE:%(title)s',
            '--no-simulate',
        ]

        if self.profile == 'vod':
            output_template = f"{date_prefix} %(title,id).200B/{date_prefix} %(title,id).200B.%(ext)s"
            cmd.extend([
                '--merge-output-format', 'mov',
                '--remux-video', 'mov',
                '--postprocessor-args', 'ffmpeg:-c:a pcm_s16le',
                '-o', os.path.join(base_path, output_template).replace('\\', '/')
            ])
        else:
            output_template = "%(title,id).200B/%(title,id).200B.%(ext)s"
            cmd.extend([
                '--write-subs',
                '--write-thumbnail',
                '--write-auto-subs',
                '--sub-langs', 'en.*',
                '--write-link',
                '--merge-output-format', 'mp4',
                '--remux-video', 'mp4',
                '-o', os.path.join(base_path, output_template).replace('\\', '/')
            ])

        cmd.extend([
            '--',
            self.url
        ])
        return cmd

    def run(self):
        try:
            target_start_time = time.time() + (self.delay_mins * 60)
            task_status[self.client_id] = {
                'id': self.client_id,
                'url': self.url,
                'profile': self.profile,
                'status': 'waiting' if self.delay_mins > 0 else 'started',
                'progress': 0.0,
                'title': 'Waiting...' if self.delay_mins > 0 else 'Starting...',
                'log': [],
                'created_at': time.time(),
                'target_start_time': target_start_time
            }
            active_downloaders[self.client_id] = self
            save_tasks()

            if self.delay_mins > 0:
                wait_time = self.delay_mins * 60
                elapsed = 0
                while elapsed < wait_time:
                    if self.cancelled:
                        task_status[self.client_id]['status'] = 'cancelled'
                        task_status[self.client_id]['title'] = 'Cancelled'
                        save_tasks()
                        return
                    time.sleep(1)
                    elapsed += 1
                
                task_status[self.client_id]['status'] = 'started'
                task_status[self.client_id]['title'] = 'Starting...'
                save_tasks()

            cmd = self.build_command()
            task_status[self.client_id]['log'].append("Command: " + " ".join(cmd))
            
            # Hide window on Windows
            creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace',
                bufsize=1,
                creationflags=creationflags
            )

            for line in iter(self.process.stdout.readline, ''):
                if self.cancelled:
                    break
                line_clean = line.strip()
                if not line_clean:
                    continue
                
                task_status[self.client_id]['log'].append(line_clean)
                
                # Keep log size reasonable
                if len(task_status[self.client_id]['log']) > 50:
                    task_status[self.client_id]['log'] = task_status[self.client_id]['log'][-50:]

                # Extract title
                if line_clean.startswith('YT-DLP-TITLE:'):
                    title = line_clean.split('YT-DLP-TITLE:', 1)[1].strip()
                    if self.profile == 'vod' and self.date_str:
                        task_status[self.client_id]['title'] = f"{self.date_str} {title}"
                    else:
                        task_status[self.client_id]['title'] = title
                
                # Extract progress
                if '[download]' in line_clean and '%' in line_clean:
                    progress_match = re.search(r'(\d+\.\d+)%', line_clean)
                    if progress_match:
                        task_status[self.client_id]['progress'] = float(progress_match.group(1))
                        
                current_time = time.time()
                if not hasattr(self, 'last_save_time') or (current_time - self.last_save_time) > 2.0:
                    save_tasks()
                    self.last_save_time = current_time

            if self.cancelled:
                if self.process:
                    self.process.terminate()
                task_status[self.client_id]['status'] = 'cancelled'
                task_status[self.client_id]['title'] = 'Cancelled'
            else:
                self.process.wait()
                if self.process.returncode == 0:
                    task_status[self.client_id]['status'] = 'finished'
                    task_status[self.client_id]['progress'] = 100.0
                else:
                    task_status[self.client_id]['status'] = f'error (code {self.process.returncode})'
            
            save_tasks()
            
        except Exception as e:
            logger.error(f"Task runtime error: {e}")
            task_status[self.client_id]['status'] = 'error'
            task_status[self.client_id]['log'].append(str(e))
        finally:
            if self.client_id in active_downloaders:
                del active_downloaders[self.client_id]
            save_tasks()

    def cancel(self):
        self.cancelled = True
        if self.process:
            try:
                self.process.terminate()
            except Exception:
                pass

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/download', methods=['POST'])
def add_download():
    data = request.json
    url = data.get('url', '').strip()
    profile = data.get('profile', 'default') # 'default' or 'vod'
    delay_mins = int(data.get('delay_mins', 0))
    date_str = data.get('date', '').strip()

    if not url:
        return jsonify({"error": "URL required"}), 400

    if not url.startswith(('http://', 'https://')):
        return jsonify({"error": "Invalid URL protocol. Must be http:// or https://"}), 400


    if date_str:
        date_str = re.sub(r'[^a-zA-Z0-9_\-]', '', date_str)

    client_id = str(uuid.uuid4())
    runner = YTDLPRunner(client_id, url, profile, delay_mins, date_str)
    t = threading.Thread(target=runner.run, daemon=True)
    t.start()
    return jsonify({"id": client_id})

@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    return jsonify(task_status)

@app.route('/api/stop/<client_id>', methods=['POST'])
def stop_task(client_id):
    if client_id in active_downloaders:
        active_downloaders[client_id].cancel()
        return jsonify({"success": True})
    elif client_id in task_status and task_status[client_id]['status'] in ['waiting']:
         task_status[client_id]['status'] = 'cancelled'
         save_tasks()
         return jsonify({"success": True})
    return jsonify({"error": "Task not found or not active"}), 404

@app.route('/api/stop_all', methods=['POST'])
def stop_all():
    global active_downloaders
    for cid, runner in active_downloaders.items():
        runner.cancel()
    
    for cid, t in task_status.items():
        if t['status'] == 'waiting':
             t['status'] = 'cancelled'
    save_tasks()
    return jsonify({"success": True})

@app.route('/api/remove/<client_id>', methods=['POST'])
def remove_task(client_id):
    if client_id in task_status and client_id not in active_downloaders:
        del task_status[client_id]
        save_tasks()
        return jsonify({"success": True})
    return jsonify({"error": "Task not found or still active"}), 404

@app.route('/api/clear_finished', methods=['POST'])
def clear_finished():
    global task_status
    include_cancelled = request.args.get('include_cancelled', 'false') == 'true'
    clearable = ['finished']
    if include_cancelled:
        clearable.extend(['cancelled', 'error', 'error (interrupted)'])
    to_remove = []
    for cid, task in task_status.items():
        if task['status'] in clearable or (include_cancelled and 'error' in task['status']):
            to_remove.append(cid)
    for cid in to_remove:
        del task_status[cid]
    save_tasks()
    return jsonify({"success": True})

@app.route('/api/settings', methods=['GET'])
def api_get_settings():
    settings = load_settings()
    # Don't expose the password to the frontend
    if 'admin_password' in settings:
        del settings['admin_password']
    return jsonify(settings)

@app.route('/api/settings', methods=['POST'])
def api_save_settings():
    new_settings = request.json
    current_settings = load_settings()
    provided_password = new_settings.get('password', '')
    
    # Check if the provided password matches the stored password
    if provided_password != current_settings.get('admin_password', 'admin'):
        return jsonify({"error": "Unauthorized. Invalid password."}), 401
    
    new_password = new_settings.get('new_password', '').strip()
    admin_password = current_settings.get("admin_password", "admin")
    if new_password:
        admin_password = new_password
        
    # We only update the paths and port, preserve the password
    updated_settings = {
        "default_path": new_settings.get("default_path", current_settings.get("default_path")),
        "vod_path": new_settings.get("vod_path", current_settings.get("vod_path")),
        "port": int(new_settings.get("port", current_settings.get("port", 5557))),
        "admin_password": admin_password
    }
    
    if save_settings(updated_settings):
        return jsonify({"success": True})
    return jsonify({"error": "Failed to save settings"}), 500

@app.route('/api/restart', methods=['POST'])
def api_restart():
    data = request.json or {}
    provided_password = data.get('password', '')
    current_settings = load_settings()
    
    if provided_password != current_settings.get('admin_password', 'admin'):
        return jsonify({"error": "Unauthorized. Invalid password."}), 401
        
    def restart_server():
        time.sleep(1)
        os.execv(sys.executable, [sys.executable, os.path.join(BASE_DIR, 'app.py')])
        
    t = threading.Thread(target=restart_server)
    t.start()
    return jsonify({"success": True})

if __name__ == '__main__':
    load_tasks()
    settings = load_settings()
    port = int(settings.get('port', 5557))
    
    try:
        from waitress import serve
        logger.info(f"Starting production server on http://0.0.0.0:{port} using Waitress")
        serve(app, host='0.0.0.0', port=port, threads=6)
    except ImportError:
        logger.info(f"Waitress not found, falling back to Flask dev server on http://0.0.0.0:{port}")
        app.run(host='0.0.0.0', port=port, debug=False)
