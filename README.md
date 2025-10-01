# YT-DLP Web Downloader

A modern, responsive web interface for yt-dlp with real-time download tracking and mobile support.

## Features

- ✨ **Modern UI**: Beautiful, responsive design that works on all devices
- 📱 **Mobile-First**: Single column layout on mobile devices for optimal viewing
- 🔄 **Live Updates**: Real-time download progress and status updates
- 💾 **Persistent Tasks**: Downloads continue and status persists after page refresh
- 🎯 **Direct Commands**: No more .bat files - calls yt-dlp directly for better performance
- 📊 **Progress Tracking**: Visual progress bars and detailed download information
- 🗂️ **Task Management**: View, track, and manage multiple simultaneous downloads
- 🚀 **Better Performance**: Improved error handling, logging, and resource management

## Requirements

- Python 3.8 or higher
- yt-dlp
- Flask

## Installation

1. **Clone or download this repository**

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install yt-dlp:**
   ```bash
   pip install yt-dlp
   ```

## Usage

### Starting the Server

**Option 1: Using the batch file (Windows)**
```bash
start.bat
```

**Option 2: Direct Python command**
```bash
python app.py
```

The server will start on `http://localhost:5000`

### Using the Web Interface

1. Open your browser and navigate to `http://localhost:5000`
2. Enter a video URL in the input field
3. For VOD downloads, set the date (defaults to current date)
4. Click "Download" for regular downloads or "VOD Download" for VOD downloads
5. Monitor progress in real-time with the task cards
6. Downloads persist across page refreshes

### API Endpoints

- `GET /` - Web interface
- `POST /start_download` - Start a regular download
- `POST /start_vod_download` - Start a VOD download  
- `GET /status/<client_id>` - Get download status
- `POST /cancel_download/<client_id>` - Cancel a download
- `GET /get_tasks` - Get all tasks
- `POST /clear_tasks` - Clear all tasks
- `GET /health` - Health check endpoint

## Configuration

Edit the `Config` class in `app.py` to customize:

- Download paths
- yt-dlp arguments
- Server settings

```python
class Config:
    DOWNLOAD_PATH = r'\\your\download\path'
    VOD_DOWNLOAD_PATH = r'\\your\vod\path'
    # ... other settings
```

## Features Overview

### Improvements from Original Version

1. **No More .bat Files**: Direct subprocess calls for better performance and security
2. **Mobile Responsive**: Single column layout on mobile devices
3. **Modern UI**: Beautiful gradient design with smooth animations
4. **Better Error Handling**: Comprehensive logging and user-friendly error messages
5. **Progress Tracking**: Real-time progress bars and download statistics
6. **Persistent Tasks**: Tasks survive page refreshes and server restarts
7. **Task Management**: Better organization and control over downloads
8. **Health Monitoring**: Built-in health check and automatic cleanup of old tasks

### Mobile Features

- **Responsive Design**: Automatically adapts to screen size
- **Single Column Layout**: Optimal viewing on mobile devices
- **Touch-Friendly**: Large buttons and touch targets
- **Optimized Forms**: Prevents zoom on iOS when focusing inputs

### Technical Improvements

- **Type Hints**: Full type annotations for better code quality
- **Logging**: Comprehensive logging to file and console
- **Error Handling**: Graceful error handling with user feedback
- **Configuration**: Centralized configuration management
- **Security**: Environment-based secrets and input validation
- **Performance**: Optimized database operations and memory usage

## Development

### Project Structure

```
YTDLP_Web v0.0.4/
├── app.py              # Main Flask application
├── requirements.txt    # Python dependencies
├── start.bat          # Windows startup script
├── README.md          # This file
├── static/
│   └── style.css      # Modern CSS with mobile support
└── templates/
    └── index.html     # Responsive HTML template
```

### Environment Variables

- `SECRET_KEY`: Flask secret key (defaults to dev key)
- `PORT`: Server port (defaults to 5000)
- `DEBUG`: Debug mode (defaults to true)

## Troubleshooting

### Common Issues

1. **yt-dlp not found**: Make sure yt-dlp is installed and in your PATH
2. **Permission errors**: Check write permissions for download directories
3. **Port already in use**: Change the port in the environment or code
4. **Network paths**: Ensure network paths are accessible and properly formatted

### Logs

Check `app.log` for detailed server logs and error information.

## License

This project is open source and available under the MIT License.

## Contributing

Feel free to submit issues, feature requests, or pull requests to improve this application.
