# SceneSnap

A Windows 10/11 (64-bit) desktop app that turns pasted scene timestamps and a local video into **PNG snapshot images**. Runs locally without a website login or upload.

## Download
Open **Actions → Build Windows EXE → latest successful run → Artifacts → SceneSnap-Windows-x64**. Extract the downloaded ZIP and open **SceneSnap.exe**. Python and FFmpeg are bundled; no separate installation is needed. The executable is unsigned.

## Use
Choose a video and output folder, paste the website's scene list, validate it, choose 1–20 images per scene, then generate snapshots. One image uses the midpoint; three use 25%, 50%, and 75% of the range. Output PNGs keep source resolution. Each run saves a fresh folder with images, a CSV index and an offline gallery. Cancel keeps completed images.

Supported input:
```
Preview unavailable
Scene 1
0:00.0 to 0:05.3
Edited
Complete

Scene 2
0:05.6 to 0:06.1
```

The app preserves time gaps and rejects malformed/conflicting ranges and videos shorter than the scene list. Use the same video edit as the website; duration cannot establish content identity. Snapshot times are requested times, subject to source frame rate. Very short scenes may repeat frames.

## Building
GitHub Actions builds a single-file executable with PyInstaller and tests the **packaged EXE** on Windows: bundled FFmpeg and FFprobe, six real PNGs, CSV/gallery, and window initialization. The GUI also supports running directly with Python and external FFmpeg/FFprobe.

## Third-party components
FFmpeg is a separate subprocess, bundled from Gyan's Windows essentials build. Its GPLv3 license and vendor/source information are included in the artifact and embedded in the executable. FFmpeg: https://ffmpeg.org/ ; binaries and build/source details: https://www.gyan.dev/ffmpeg/builds/ . Python, Tcl/Tk and PyInstaller retain their respective licenses. The build records the FFmpeg archive SHA256 and executable SHA256.

No private assignment files or user videos are included in this repository.
