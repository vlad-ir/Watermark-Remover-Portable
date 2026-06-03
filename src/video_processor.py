import cv2
import numpy as np
from pathlib import Path
import tqdm

class VideoProcessor:
    def __init__(self, inpainter, device="cpu"):
        self.inpainter = inpainter
        self.device = device

    def process_video(self, input_path, output_path, mask, fps=None):
        """Process entire video with given mask"""
        cap = cv2.VideoCapture(str(input_path))

        if fps is None:
            fps = cap.get(cv2.CAP_PROP_FPS)

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))

        for i in tqdm(range(total), desc="Processing"):
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

        cap.release()
        out.release()
        return output_path

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