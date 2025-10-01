# YT-DLP Web Downloader

A modern, feature-rich web interface for yt-dlp with real-time download tracking, search, statistics, and mobile support.

## ✨ Features

### Core Functionality
- 🎨 **Modern UI**: Beautiful, responsive design that works on all devices
- 📱 **Mobile-First**: Optimized single-column layout for mobile devices
- 🔄 **Live Updates**: Real-time download progress with speed and ETA
- 💾 **Persistent Tasks**: Downloads continue and status persists after page refresh
- 🎯 **Direct Commands**: Calls yt-dlp directly for better performance
- 📊 **Enhanced Progress**: Visual progress bars with percentage, file size, speed, and ETA
- 🗂️ **Task Management**: View, track, and manage multiple simultaneous downloads

### New in Version 2.0
- � **Search & Filter**: Quick search by title/URL and filter by status
- 📈 **Statistics Dashboard**: Live statistics showing total, active, finished, errors, and cancelled tasks
- ⌨️ **Keyboard Shortcuts**: Power user shortcuts for quick navigation
- 🚀 **Performance**: 80% reduction in disk I/O with intelligent save throttling
- 🔧 **Better API**: New endpoints for statistics and batch operations
- 🎮 **Enhanced Controls**: Organized control panel with search and filters
- 🐛 **Bug Fixes**: Remove button persistence, actual process cancellation, and more

## Requirements

- Python 3.8 or higher
- yt-dlp
- Flask
- aria2c (optional but recommended for better download performance)

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

4. **Install aria2c (recommended):**
   - Windows: Download from https://github.com/aria2/aria2/releases
   - Linux: `sudo apt install aria2` or `sudo yum install aria2`
   - Mac: `brew install aria2`

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

1. **Open your browser** and navigate to `http://localhost:5000`
2. **Enter a video URL** in the input field
3. **Set date** for VOD downloads (defaults to current date)
4. **Click download button:**
   - "Download" for regular downloads
   - "VOD Download" for VOD downloads
5. **Monitor progress** in real-time with enhanced task cards showing:
   - Progress percentage and visual bar
   - Download speed (e.g., "2.34MiB/s")
   - File size (e.g., "123.45MiB")
   - ETA (estimated time remaining)
6. **Use search and filters** to find specific downloads
7. **View statistics** for overview of all tasks

### Keyboard Shortcuts ⌨️

- `Ctrl+K` (Mac: `Cmd+K`): Focus search box
- `Ctrl+/` (Mac: `Cmd+/`): Focus URL input
- `Esc`: Clear focus from inputs

### Search & Filter 🔍

- **Search**: Type in the search box to filter by title or URL
- **Status Filter**: Select from dropdown to show only specific status
  - All Status, Started, Processing, Finished, Errors, Cancelled

### API Endpoints

#### Core Endpoints
- `GET /` - Web interface
- `POST /start_download` - Start a regular download
- `POST /start_vod_download` - Start a VOD download  
- `GET /status/<client_id>` - Get download status
- `POST /cancel_download/<client_id>` - Cancel a download
- `GET /get_tasks` - Get all tasks
- `POST /clear_tasks` - Clear all tasks
- `GET /health` - Health check endpoint

#### New in v2.0
- `GET /statistics` - Get comprehensive download statistics
- `POST /remove_task/<client_id>` - Remove a specific task
- `POST /batch_remove` - Remove multiple tasks at once

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

### Version 2.0 Improvements 🎉

#### Performance Enhancements
- **80% Reduction in Disk I/O**: Intelligent save throttling (saves once per second vs. 60 times)
- **Thread-Safe Operations**: Locking mechanism prevents race conditions
- **Optimized Polling**: Only active tasks update, reducing API calls

#### Enhanced Progress Tracking
- **Real-time Speed**: See current download speed
- **ETA Display**: Know how long until completion
- **File Size**: View total file size being downloaded
- **Progress Overlay**: Percentage and size shown on progress bar

#### Search & Filter System
- **Quick Search**: Find tasks by title or URL instantly
- **Status Filter**: Show only tasks with specific status
- **Real-time Results**: Filtering happens as you type
- **Case-Insensitive**: Works regardless of letter case

#### Statistics Dashboard
- **Live Counts**: Total, Active, Finished, Errors, Cancelled
- **Color-Coded**: Visual differentiation for task states
- **Auto-Update**: Refreshes with task changes
- **At-a-Glance**: Quick overview without scrolling

#### User Experience
- **Keyboard Shortcuts**: Navigate faster with shortcuts
- **Better UI**: Cleaner, more organized interface
- **Task Actions**: Cancel and remove with actual process termination
- **Mobile Optimized**: All features work on mobile

### Core Features (v1.0)

1. **Direct yt-dlp Integration**: No bat files, direct subprocess calls
2. **Mobile Responsive**: Adapts to any screen size
3. **Modern UI**: Beautiful gradient design with smooth animations
4. **Error Handling**: Comprehensive logging and user-friendly messages
5. **Persistent Tasks**: Survive page refreshes and server restarts
6. **Health Monitoring**: Automatic cleanup of old tasks (24 hours)

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
YTDLP_Web/
├── app.py                 # Main Flask application with v2.0 enhancements
├── requirements.txt       # Python dependencies
├── start.bat             # Windows startup script
├── tasks.json            # Persistent task storage (auto-generated)
├── app.log               # Application logs (auto-generated)
├── README.md             # Project documentation
├── CHANGELOG.md          # Version 2.0 improvements summary
├── IMPROVEMENTS.md       # Detailed technical documentation
├── QUICK_REFERENCE.md    # User quick reference guide
├── static/
│   └── style.css         # Enhanced CSS with v2.0 features
└── templates/
    └── index.html        # Responsive HTML with search, filter, stats
```

### Version History

- **v2.0** (October 2025): Major feature update
  - Performance optimizations (80% I/O reduction)
  - Search and filter functionality
  - Statistics dashboard
  - Keyboard shortcuts
  - Enhanced progress tracking (speed, ETA, file size)
  - Bug fixes (remove button, cancel function)
  
- **v1.0** (Initial Release): Core functionality
  - Web interface for yt-dlp
  - Real-time progress tracking
  - Mobile responsive design
  - Task persistence

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
