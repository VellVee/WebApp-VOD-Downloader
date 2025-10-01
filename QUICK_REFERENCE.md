# Quick Reference Guide - YT-DLP Web Downloader

## 🚀 Quick Start

1. **Start the App**
   ```bash
   python app.py
   ```
   Access at: `http://localhost:5000`

2. **Download a Video**
   - Paste URL in the input field
   - Click "Download" for regular downloads
   - Click "VOD Download" for VOD with date folder

3. **Track Progress**
   - See real-time progress, speed, and ETA
   - Progress bar shows percentage and file size
   - Output can be toggled for details

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+K` (Mac: `Cmd+K`) | Focus search box |
| `Ctrl+/` (Mac: `Cmd+/`) | Focus URL input |
| `Esc` | Clear focus |

## 🔍 Search & Filter

### Search Tasks
- **Where**: Top of "Active Downloads" section
- **What**: Search by video title or URL
- **How**: Just start typing, results update instantly

### Filter by Status
- **All Status**: Show everything
- **Started**: Show newly started downloads
- **Processing**: Show actively downloading
- **Finished**: Show completed downloads
- **Errors**: Show failed downloads
- **Cancelled**: Show user-cancelled downloads

## 📊 Understanding Statistics

The statistics bar shows:
- **Total**: Total number of tasks
- **Active**: Currently downloading (Started + Processing)
- **Finished**: Successfully completed
- **Errors**: Failed downloads
- **Cancelled**: User-cancelled tasks

## 🎮 Task Controls

### Per-Task Actions
- **Toggle Output**: Show/hide detailed yt-dlp output
- **Cancel**: Stop an active download (disabled when finished)
- **Remove**: Delete task from list (cancels if active)

### Bulk Actions
- **Clear All**: Remove all tasks (asks for confirmation)

## 📈 Progress Information

### What You See
- **Progress Bar**: Visual representation with percentage
- **File Size**: Total size of the download
- **Speed**: Current download speed (e.g., "2.34MiB/s")
- **ETA**: Estimated time remaining (e.g., "00:30")

### Status Meanings
- **started**: Task created, waiting to begin
- **processing**: Actively downloading
- **finished**: Download completed successfully
- **error**: Download failed (check output for details)
- **cancelled**: User stopped the download

## 🎨 Color Coding

### Task Status
- **Blue border**: Active (started/processing)
- **Green border**: Finished successfully
- **Red border**: Error occurred
- **Yellow border**: Cancelled by user

### Statistics
- **Blue**: Active tasks
- **Green**: Finished tasks
- **Red**: Error tasks
- **Yellow**: Cancelled tasks

## 🔧 Download Types

### Regular Download
- Uses default configuration
- Downloads to: `\\192.168.42.3\VaultStorage\ALL TO SORT`
- Format: Best AV1 video + best audio
- Creates folder with video title

### VOD Download
- Includes date in folder structure
- Downloads to: `\\192.168.42.3\VaultStorage\WorkMedia\VODS`
- Format: `[DATE] Video Title\Video Title.ext`
- Restricts filenames to 50 characters

## 💡 Tips & Tricks

### Efficient Workflow
1. Paste URL and press Enter (starts regular download)
2. Use Ctrl+/ to quickly focus URL input
3. Use Ctrl+K to search existing downloads
4. Filter by "Processing" to see only active downloads

### Monitoring Downloads
- Check statistics for overview
- Toggle output for detailed progress
- Speed and ETA update every 2 seconds
- Progress bar fills as download proceeds

### Managing Tasks
- Remove finished downloads to keep list clean
- Search for specific downloads by title
- Filter errors to see what failed
- Use "Clear All" to start fresh

## 🐛 Troubleshooting

### Task Stuck on "started"
- Check output for errors
- Verify network connectivity
- Ensure yt-dlp is installed: `pip install yt-dlp`

### No Progress Updates
- Wait 2 seconds (update interval)
- Refresh page to reload tasks
- Check browser console for errors

### Download Failed
- Click "Toggle Output" to see error
- Common issues:
  - Video unavailable/private
  - Network path not accessible
  - Insufficient disk space
  - yt-dlp needs update

### Remove Button Not Working
- Task must exist on server
- Check console for error messages
- Try refreshing the page

## 🔗 API Endpoints

For developers/automation:

- `POST /start_download`: Start regular download
- `POST /start_vod_download`: Start VOD download
- `GET /status/<client_id>`: Get task status
- `POST /cancel_download/<client_id>`: Cancel download
- `POST /remove_task/<client_id>`: Remove task
- `GET /get_tasks`: Get all tasks
- `POST /clear_tasks`: Remove all tasks
- `GET /statistics`: Get statistics
- `POST /batch_remove`: Remove multiple tasks
- `GET /health`: Health check

## 📱 Mobile Usage

### Supported
- ✅ Download videos
- ✅ Monitor progress
- ✅ Search and filter
- ✅ View statistics
- ✅ Cancel/remove tasks

### Optimized For
- Touch-friendly buttons
- Responsive layout
- Readable on small screens
- No horizontal scrolling

### Note
- Keyboard shortcuts not available on mobile
- Use search and filter dropdowns instead

## 🔐 Security Notes

- Change `SECRET_KEY` in production
- App listens on `0.0.0.0` (all interfaces)
- No authentication by default
- Consider adding auth for public deployment

## ⚙️ Configuration

### Modify Download Paths
Edit in `app.py`:
```python
DOWNLOAD_PATH = r'\\192.168.42.3\VaultStorage\ALL TO SORT'
VOD_DOWNLOAD_PATH = r'\\192.168.42.3\VaultStorage\WorkMedia\VODS'
```

### Adjust Update Frequency
Edit in `index.html`:
```javascript
setInterval(() => {
    this.updateAllActiveTasks();
}, 2000); // Change 2000 to desired milliseconds
```

### Change Save Throttle
Edit in `app.py`:
```python
if not force and (current_time - _last_save_time) < 1.0:  # Change 1.0
```

## 📞 Getting Help

1. **Check Logs**: Look at `app.log` for errors
2. **Browser Console**: Check for JavaScript errors
3. **Health Check**: Visit `/health` endpoint
4. **Test yt-dlp**: Run `python -m yt_dlp --version`

## 🎓 Best Practices

### Regular Use
- Remove completed downloads periodically
- Check for yt-dlp updates monthly
- Monitor disk space on network storage
- Keep browser tab open during downloads

### Power User
- Use keyboard shortcuts for speed
- Master search and filter
- Monitor statistics dashboard
- Use batch operations for cleanup

### System Admin
- Monitor health endpoint
- Check app.log regularly
- Verify network path accessibility
- Update dependencies quarterly

---

**Need more help?** Check the detailed [IMPROVEMENTS.md](IMPROVEMENTS.md) and [CHANGELOG.md](CHANGELOG.md) files.
