# SceneSnap

A Windows 10/11 (64-bit) desktop app that turns pasted scene timestamps and a local video into **PNG snapshot images**. Runs locally without a website login or upload.

## Download
Open **Actions → Build Windows EXE → latest successful run → Artifacts → SceneSnap-Windows-x64**. Extract the downloaded ZIP and open **SceneSnap.exe**. Python and FFmpeg are bundled; no separate installation is needed. The executable is unsigned.

## Use
Choose a video and output folder, paste the website's scene list, validate it, then generate snapshots. The app saves exactly **one PNG per scene**, capturing the first frame at or after its start timestamp. Files are named `videoframe_1_1.png`, `videoframe_2_1.png`, etc. Each run creates a new folder with PNGs, a CSV index and an offline gallery.

This version seeks directly to each scene start instead of indexing every frame in the entire video. Progress appears before extraction begins and after each saved image. Cancel interrupts the current operation. Metadata and individual image operations have a 60-second timeout with a visible error, instead of waiting indefinitely. Completed images are retained if cancelled or an error occurs.

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

The app preserves time gaps and rejects malformed/conflicting ranges and videos shorter than the scene list. Use the same video edit as the website; duration cannot establish content identity. The first frame starts at or after the start timestamp. Very short scenes may repeat frames.

## Building
GitHub Actions builds a single-file executable with PyInstaller and tests the **packaged EXE** on Windows: bundled FFmpeg and FFprobe, first-frame image pixels, non-aligned starts and EOF, filenames, progress, cancellation and timeout, CSV/gallery, and window initialization. The GUI also supports running directly with Python and external FFmpeg/FFprobe.

## Third-party components
FFmpeg is a separate subprocess, bundled from Gyan's Windows essentials build. Its GPLv3 license and vendor/source information are included in the artifact and embedded in the executable. FFmpeg: https://ffmpeg.org/ ; binaries and build/source details: https://www.gyan.dev/ffmpeg/builds/ . Python, Tcl/Tk and PyInstaller retain their respective licenses. The build records the FFmpeg archive SHA256 and executable SHA256.

No private assignment files or user videos are included in this repository.
