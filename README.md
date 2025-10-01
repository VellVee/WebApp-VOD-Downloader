# YT-DLP Web Downloader

Web interface for yt-dlp with real-time download tracking.

## Requirements

- Python 3.8+
- yt-dlp
- Flask
- aria2c (optional, for faster downloads)

## Installation

Install dependencies:
```bash
pip install -r requirements.txt
pip install yt-dlp
```

## Usage

Start server:
```bash
python app.py
```

Access at `http://localhost:5000`

## Configuration

Edit `Config` class in `app.py`:

```python
class Config:
    DOWNLOAD_PATH = r'\\your\download\path'
    VOD_DOWNLOAD_PATH = r'\\your\vod\path'
```

## API Endpoints

- `POST /start_download` - Start regular download
- `POST /start_vod_download` - Start VOD download  
- `GET /status/<client_id>` - Get download status
- `POST /cancel_download/<client_id>` - Cancel download
- `POST /remove_task/<client_id>` - Remove task
- `GET /get_tasks` - Get all tasks
- `POST /clear_tasks` - Clear all tasks

## Features

- Real-time progress tracking
- Persistent task storage
- Multiple simultaneous downloads
- Process cancellation with cleanup
- Automatic timeout handling
- Mobile responsive interface

## Troubleshooting

Check `app.log` for errors.

Ensure yt-dlp is in PATH and download directories are accessible.

