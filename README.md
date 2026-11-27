# ASCII Video Player (`ascii.py`)

A real-time, audio-synced color ASCII video renderer built with Python, OpenCV, Pygame, and FFmpeg.

Highlights:
Audio-Video Sync: Extracts audio via FFmpeg and syncs frame timing to the audio clock.
Visual Enhancement: Uses CLAHE contrast, gamma correction, and HSV saturation boosting for crisp output.
Performance: Quantizes RGB values and caches rendered glyphs (`lru_cache`) for smooth playback, with `F11` fullscreen support.

Run it:
1. Install dependencies: `pip install opencv-python pygame numpy` (and ensure `ffmpeg` is installed).
2. Place a video file beside `ascii.py` and set `VIDEO_PATH`, then run `python ascii.py`.

Demo:
https://github.com/user-attachments/assets/82c3efee-cc39-4cd7-8c86-133fb9e22569



