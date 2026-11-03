# SceneSnap

A Windows 10/11 (64-bit) desktop app that turns pasted scene timestamps and a local video into **PNG snapshot images**. Runs locally without a website login or upload.

## Download
Open **Actions → Build Windows EXE → latest successful run → Artifacts → SceneSnap-Windows-x64**. Extract the downloaded ZIP and open **SceneSnap.exe**. Python and FFmpeg are bundled; no separate installation is needed. The executable is unsigned.

## Use
Choose a video and output folder, paste the website's scene list, validate it, choose 1–20 images per scene, then generate snapshots. One image captures the first frame; two capture first and last; three capture first, middle, and last. Larger counts sample evenly between the scene boundaries. Files are named `videoframe_1_1.png`, `videoframe_1_2.png`, etc. The last frame is strictly before the end timestamp so it does not belong to the next scene. The app indexes actual frame timestamps before exporting, including variable-frame-rate video. Output PNGs keep source resolution. Each run saves a fresh folder with images, a CSV index and an offline gallery. Cancel keeps completed images.

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

The app preserves time gaps and rejects malformed/conflicting ranges and videos shorter than the scene list. Use the same video edit as the website; duration cannot establish content identity. The first frame starts at or after the start timestamp; the middle is the frame nearest the time midpoint (earlier frame on a tie). Very short scenes may repeat frames.

## Building
GitHub Actions builds a single-file executable with PyInstaller and tests the **packaged EXE** on Windows: bundled FFmpeg and FFprobe, first/middle/last image pixels for counts 1, 2 and 3, boundary exclusion, filenames, CSV/gallery, and window initialization. The GUI also supports running directly with Python and external FFmpeg/FFprobe.

## Third-party components
FFmpeg is a separate subprocess, bundled from Gyan's Windows essentials build. Its GPLv3 license and vendor/source information are included in the artifact and embedded in the executable. FFmpeg: https://ffmpeg.org/ ; binaries and build/source details: https://www.gyan.dev/ffmpeg/builds/ . Python, Tcl/Tk and PyInstaller retain their respective licenses. The build records the FFmpeg archive SHA256 and executable SHA256.

No private assignment files or user videos are included in this repository.
