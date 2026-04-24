# Web Video Downloader

Web interface for yt-dlp with real-time download tracking.

## Features

- **Web UI**: Shows all the downloads that are currently running or waiting in the queue.
- **Full Control**: Cancel active downloads, stop all threads, or clear finished items cleanly from the UI.
- **Two Profiles**: 
  - 🟧 **Regular Download**: Standard download.
  - 🟪 **VOD Download**: Prepends the selected date to both the folder and filename for archival purposes.
- **Delayed Downloads**: Optionally set a time delay before the download begins (for streams or videos that are still processing/unfinished).

## Installation

### Prerequisites
- Python 3.8+
- [FFmpeg](https://ffmpeg.org/download.html)
- [Git](https://git-scm.com/downloads) (For automatic updates on startup)

### Setup (Windows)
Double click `start.bat`. This script will:
1. Validate your Python installation.
2. Ensure `pip` and other requirements are up to date.
3. Start the production `waitress` server on `localhost:5557`.

### Setup (Linux)
Execute the `start.sh` script:
```bash
chmod +x start.sh
./start.sh
```
This script acts similarly, automatically checking and building a python `venv`, upgrading `yt-dlp`, and launching `waitress`.

## Usage
Once the server is running, navigate to `http://localhost:5557` or the hosted machine's IP address on your LAN.

1. Click the top right menu icon to set your LAN `Default Save Path` and `VOD Save Path`. By default, the admin password is `admin` (adjustable in `settings.json` - created on first run).
2. Paste link into the input field.
3. Select profile - Regular or VOD

## Built With
- `Flask` & `Waitress` WSGI server 
- `yt-dlp`
- CSS & Javascript
