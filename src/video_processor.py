import cv2
import numpy as np
from pathlib import Path
import subprocess
import tempfile
import os


class VideoProcessor:
    def __init__(self, inpainter, device="cpu"):
        self.inpainter = inpainter
        self.device = device

    def process_video(self, input_path, output_path, mask, fps=None, progress_callback=None):
        """Process entire video with given mask, preserving audio via ffmpeg"""
        input_path = str(input_path)
        output_path = str(output_path)

        cap = cv2.VideoCapture(input_path)

        if fps is None:
            fps = cap.get(cv2.CAP_PROP_FPS)

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        # Create temporary video without audio
        temp_video = tempfile.mktemp(suffix='.mp4')

        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(temp_video, fourcc, fps, (width, height))

        for i in range(total):
            ret, frame = cap.read()
            if not ret:
                break

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            if np.any(mask > 0):
                from inpainter import inpaint_img_with_lama
                result = inpaint_img_with_lama(frame_rgb, mask, self.inpainter, self.device)
            else:
                result = frame_rgb

            result_bgr = cv2.cvtColor(result, cv2.COLOR_RGB2BGR)
            out.write(result_bgr)

            # Report progress every 10 frames
            if progress_callback and i % 10 == 0:
                progress_callback(i + 1, total)

        cap.release()
        out.release()

        # Final progress
        if progress_callback:
            progress_callback(total, total)

        # Merge video with audio from original using ffmpeg
        self._merge_audio(input_path, temp_video, output_path, fps)

        # Cleanup temp file
        if os.path.exists(temp_video):
            os.remove(temp_video)

        return output_path

    def _merge_audio(self, original_path, processed_video, output_path, fps):
        """Copy audio from original video to processed video using ffmpeg"""
        try:
            # Check if ffmpeg is available
            subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            # ffmpeg not found, just copy the video without audio
            import shutil
            shutil.copy(processed_video, output_path)
            print("[WARN] ffmpeg not found. Video saved without audio.")
            return

        # Use ffmpeg to copy video from processed, audio from original
        cmd = [
            'ffmpeg', '-y',
            '-i', processed_video,      # processed video (no audio)
            '-i', original_path,        # original video (with audio)
            '-c:v', 'copy',             # copy video without re-encoding
            '-c:a', 'copy',             # copy audio without re-encoding
            '-map', '0:v:0',            # video from first input
            '-map', '1:a:0?',           # audio from second input (optional)
            '-shortest',                # trim to shortest stream
            output_path
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"[WARN] ffmpeg merge failed: {result.stderr}")
                # Fallback: copy without audio
                import shutil
                shutil.copy(processed_video, output_path)
            else:
                print(f"[INFO] Audio preserved: {output_path}")
        except Exception as e:
            print(f"[WARN] ffmpeg error: {e}")
            import shutil
            shutil.copy(processed_video, output_path)

    def extract_frames(self, video_path, output_dir, every_n=1):
        """Extract frames from video"""
        cap = cv2.VideoCapture(str(video_path))
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True)

        frame_count = 0
        saved = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_count % every_n == 0:
                path = output_dir / f"frame_{saved:06d}.png"
                cv2.imwrite(str(path), frame)
                saved += 1

            frame_count += 1

        cap.release()
        return saved