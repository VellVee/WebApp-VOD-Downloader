# Web Video Downloader

Web interface for yt-dlp with real-time download tracking.

## Features

- **Web UI**: Displays task lists with in-place updates. Includes:
  - Real-time download metrics (file size, download speed, ETA, and progress).
  - Expandable terminal log drawers for each task.
  - Search bar and status filters (All, Active, Waiting, Completed, Failed).
  - Dark and light mode toggle.
- **Task Controls**: Stop individual downloads, cancel all, or dismiss completed/failed tasks from the list.
- **Download Profiles**:
  - **Regular Download**: Downloads video with subtitle tracks and thumbnails using `mp4`.
  - **VOD Download**: Prepends a date to the output directory and filename using `mov` format and PCM audio.
  - **Audio Download**: Extracts audio and converts it to `mp3`.
- **Scheduling & Stream Monitoring**:
  - **Delayed Start**: Schedules downloads to start after a set number of minutes or hours.
  - **Wait for Live**: Waits for an offline or scheduled live stream to start and downloads it from the beginning.
- **Input Validation & Security**:
  - Rejects URLs containing shell metacharacters or whitespace.
  - Automatically prepends `https://` if the protocol prefix is missing from a link.
  - Blocks requests to local and private addresses (localhost, loopback, private/local IPs, and resolved IPs) to prevent SSRF.
- **Performance & Safety**:
  - Downloads run concurrently in separate threads.
  - Thread-safe task state tracking.
  - Disk writes to `tasks.json` occur only during task status transitions.

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
This script automatically checks and builds a python `venv`, upgrades `yt-dlp`, and launches `waitress`.

## Usage
Once the server is running, navigate to `http://localhost:5557` or the hosted machine's IP address on your LAN.

1. Click the top right menu icon to set your LAN `Default Save Path` and `VOD Save Path`. By default, the admin password is `admin` (adjustable in `settings.json` - created on first run).
2. Paste link into the input field.
3. Select profile - Regular, VOD, or Audio.

## Built With
- `Flask` & `Waitress` WSGI server 
- `yt-dlp`
- CSS & Javascript
