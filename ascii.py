import cv2
import pygame
import numpy as np
import subprocess
import tempfile
import os
import time
import shutil
from functools import lru_cache

# ============================================================
# ASCII RENDERING 3.1
# Brighter Image | Punchy Colors | Audio Sync | Fullscreen
# ============================================================

VIDEO_PATH = "Caramelldansen.mp4"

ASCII_WIDTH = 140
MAX_ASCII_WIDTH = 200

FONT_SIZE = 11
FONT_NAME = "Menlo"

CHAR_RAMP = " .'`^,:;~-_!|/\\()[]{}<>iIlrcvunxzXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$"

TARGET_LOOP_FPS = 120
SHOW_STATS = True

BACKGROUND = (5, 6, 9)


def locate_ffmpeg():
    found = shutil.which("ffmpeg")
    if found:
        return found

    for path in (
        "/opt/homebrew/bin/ffmpeg",
        "/usr/local/bin/ffmpeg",
    ):
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path

    return None


def main():
    if not os.path.isfile(VIDEO_PATH):
        raise FileNotFoundError(
            f"Cannot find {VIDEO_PATH}. Put it beside ascii.py."
        )

    cap = cv2.VideoCapture(VIDEO_PATH)

    if not cap.isOpened():
        raise RuntimeError("Could not open the video.")

    source_fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    if not source_fps or source_fps <= 0:
        source_fps = 30.0

    duration = total_frames / source_fps if total_frames > 0 else 0

    print(f"Video FPS: {source_fps:.2f}")
    print(f"Video length: {duration:.2f} seconds")

    pygame.init()
    pygame.mixer.init()

    font = pygame.font.SysFont(FONT_NAME, FONT_SIZE)
    char_width = max(1, font.size("M")[0])
    char_height = max(1, font.get_linesize())

    screen = pygame.display.set_mode((1280, 800), pygame.RESIZABLE)
    pygame.display.set_caption(
        "ASCII RENDERING 3.1 | F11 Fullscreen | ESC Quit"
    )

    clock = pygame.time.Clock()

    @lru_cache(maxsize=12000)
    def get_glyph(character, red, green, blue):
        return font.render(character, True, (red, green, blue))

    # Image contrast enhancement
    clahe = cv2.createCLAHE(
        clipLimit=1.35,
        tileGridSize=(8, 8)
    )

    # Brighter gamma correction, calculated once for performance
    gamma = 0.85
    gamma_table = np.array(
        [
            min(255, int(((i / 255.0) ** gamma) * 255))
            for i in range(256)
        ],
        dtype=np.uint8
    )

    # Extract audio using FFmpeg
    audio_path = None
    audio_ready = False
    ffmpeg = locate_ffmpeg()

    try:
        if ffmpeg:
            audio_file = tempfile.NamedTemporaryFile(
                suffix=".wav",
                delete=False
            )
            audio_path = audio_file.name
            audio_file.close()

            result = subprocess.run(
                [
                    ffmpeg, "-y", "-i", VIDEO_PATH,
                    "-vn",
                    "-acodec", "pcm_s16le",
                    "-ar", "44100",
                    "-ac", "2",
                    audio_path,
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )

            if (
                result.returncode == 0
                and os.path.exists(audio_path)
                and os.path.getsize(audio_path) > 44
            ):
                try:
                    pygame.mixer.music.load(audio_path)
                    audio_ready = True
                except pygame.error as error:
                    print(f"Audio loading failed: {error}")
        else:
            print("FFmpeg not found. Playing without audio.")

        playback_started = time.perf_counter()

        if audio_ready:
            pygame.mixer.music.play()

        running = True
        fullscreen = False
        last_frame = -1

        fps_started = time.perf_counter()
        fps_frame_count = 0
        measured_fps = 0.0
        title_update = 0.0

        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                elif event.type == pygame.VIDEORESIZE and not fullscreen:
                    screen = pygame.display.set_mode(
                        (max(640, event.w), max(400, event.h)),
                        pygame.RESIZABLE
                    )

                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False

                    elif event.key == pygame.K_F11:
                        fullscreen = not fullscreen

                        if fullscreen:
                            screen = pygame.display.set_mode(
                                (0, 0), pygame.FULLSCREEN
                            )
                        else:
                            screen = pygame.display.set_mode(
                                (1280, 800), pygame.RESIZABLE
                            )

            if not running:
                break

            # Synchronize video with audio
            audio_ms = (
                pygame.mixer.music.get_pos()
                if audio_ready else -1
            )

            if audio_ready and audio_ms >= 0:
                elapsed = audio_ms / 1000.0
            else:
                elapsed = time.perf_counter() - playback_started

            # Loop video and audio
            if duration > 0 and elapsed >= duration:
                if audio_ready:
                    pygame.mixer.music.stop()
                    pygame.mixer.music.play()

                playback_started = time.perf_counter()
                last_frame = -1
                elapsed = 0.0

            target_frame = int(elapsed * source_fps)

            if total_frames > 0:
                target_frame = min(target_frame, total_frames - 1)

            # Avoid rendering the same frame repeatedly
            if target_frame == last_frame:
                clock.tick(TARGET_LOOP_FPS)
                continue

            next_frame = int(cap.get(cv2.CAP_PROP_POS_FRAMES))

            if target_frame != next_frame:
                cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)

            success, frame = cap.read()

            if not success:
                if total_frames > 0:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    last_frame = -1
                    continue
                break

            last_frame = target_frame

            frame_h, frame_w = frame.shape[:2]

            desired_width = screen.get_width() // char_width
            columns = max(
                ASCII_WIDTH,
                min(MAX_ASCII_WIDTH, desired_width)
            )
            columns = min(columns, MAX_ASCII_WIDTH)

            rows = max(
                1,
                int(columns * frame_h / frame_w * 0.48)
            )

            small = cv2.resize(
                frame,
                (columns, rows),
                interpolation=cv2.INTER_AREA
            )

            # Punchier colors
            rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)

            hsv = cv2.cvtColor(
                rgb, cv2.COLOR_RGB2HSV
            ).astype(np.float32)

            hsv[:, :, 1] *= 1.30
            hsv[:, :, 2] = hsv[:, :, 2] * 1.10 + 12

            hsv[:, :, 1] = np.clip(hsv[:, :, 1], 0, 255)
            hsv[:, :, 2] = np.clip(hsv[:, :, 2], 0, 255)

            rgb = cv2.cvtColor(
                hsv.astype(np.uint8),
                cv2.COLOR_HSV2RGB
            )

            # Brighter shading and improved details
            gray = cv2.cvtColor(
                small, cv2.COLOR_BGR2GRAY
            )

            gray = clahe.apply(gray)

            gray = cv2.convertScaleAbs(
                gray,
                alpha=1.08,
                beta=12
            )

            gray = cv2.LUT(gray, gamma_table)

            ramp_last = len(CHAR_RAMP) - 1

            char_indices = (
                gray.astype(np.uint16) * ramp_last // 256
            ).clip(0, ramp_last)

            screen.fill(BACKGROUND)

            rendered_w = columns * char_width
            rendered_h = rows * char_height

            offset_x = max(
                0, (screen.get_width() - rendered_w) // 2
            )

            offset_y = max(
                0, (screen.get_height() - rendered_h) // 2
            )

            # Render colorful ASCII characters
            for y in range(rows):
                py = offset_y + y * char_height

                for x in range(columns):
                    char = CHAR_RAMP[int(char_indices[y, x])]

                    red, green, blue = (
                        int(value) for value in rgb[y, x]
                    )

                    # Preserve more color detail
                    red = (red // 8) * 8
                    green = (green // 8) * 8
                    blue = (blue // 8) * 8

                    glyph = get_glyph(
                        char, red, green, blue
                    )

                    screen.blit(
                        glyph,
                        (
                            offset_x + x * char_width,
                            py,
                        )
                    )

            pygame.display.flip()

            # Measure rendering FPS
            fps_frame_count += 1
            now = time.perf_counter()

            if now - fps_started >= 1.0:
                measured_fps = (
                    fps_frame_count / (now - fps_started)
                )
                fps_frame_count = 0
                fps_started = now

            if SHOW_STATS and now - title_update >= 0.5:
                pygame.display.set_caption(
                    f"ASCII RENDERING 3.1 | "
                    f"{measured_fps:.1f} render FPS | "
                    f"Source {source_fps:.1f} FPS | "
                    f"{columns} columns | "
                    f"F11 Fullscreen | ESC Quit"
                )
                title_update = now

            clock.tick(TARGET_LOOP_FPS)

    finally:
        try:
            pygame.mixer.music.stop()
        except pygame.error:
            pass

        cap.release()
        pygame.quit()

        if audio_path and os.path.exists(audio_path):
            try:
                os.remove(audio_path)
            except OSError:
                pass

    print("===== ASCII RENDERING 3.1 COMPLETE =====")


if __name__ == "__main__":
    main() 