import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import cv2
import numpy as np
from PIL import Image, ImageTk
import os
import threading
from pathlib import Path


class WatermarkRemover:
    def __init__(self, root):
        self.root = root
        self.root.title("Watermark Remover - Portable")
        self.root.geometry("1400x900")
        self.root.minsize(800, 600)

        # Paths
        self.root_path = Path(__file__).parent.parent
        self.models_path = self.root_path / "models"
        self.outputs_path = self.root_path / "outputs"
        self.outputs_path.mkdir(exist_ok=True)

        # Media state
        self.cap = None
        self.is_image = False
        self.image_path = None
        self.original_frame = None
        self.display_frame = None
        self.mask = None
        self.frame_idx = 0
        self.total_frames = 0
        self.fps = 30
        self.frame_width = 0
        self.frame_height = 0

        # Scaling & Zoom
        self.base_scale = 1.0
        self.zoom_level = 0
        self.scale = 1.0
        self.offset_x = 0
        self.offset_y = 0

        # Panning state (for zoomed view)
        self.panning = False
        self.pan_start_x = 0
        self.pan_start_y = 0
        self.scroll_start_x = 0
        self.scroll_start_y = 0

        # Drawing state
        self.drawing = False
        self.brush_size = 15
        self.cursor_id = None

        # Inpainting state
        self.inpainter = None
        self.processing = False

        self.setup_ui()
        self.load_inpainter()

        # Bind resize event
        self.root.bind("<Configure>", self.on_window_resize)

    def setup_ui(self):
        # Top control panel
        control_frame = ttk.Frame(self.root)
        control_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(control_frame, text="Load Video", command=self.load_video).pack(side=tk.LEFT, padx=2)
        ttk.Button(control_frame, text="Load Image", command=self.load_image).pack(side=tk.LEFT, padx=2)
        ttk.Button(control_frame, text="Save Mask", command=self.save_mask).pack(side=tk.LEFT, padx=2)
        ttk.Button(control_frame, text="Process", command=self.process_current).pack(side=tk.LEFT, padx=2)
        ttk.Button(control_frame, text="Process All", command=self.process_all).pack(side=tk.LEFT, padx=2)
        ttk.Button(control_frame, text="Save", command=self.save_result).pack(side=tk.LEFT, padx=2)

        # Zoom controls
        ttk.Label(control_frame, text="Zoom:").pack(side=tk.LEFT, padx=(20, 0))
        self.zoom_label = ttk.Label(control_frame, text="100%")
        self.zoom_label.pack(side=tk.LEFT, padx=2)
        ttk.Button(control_frame, text="Reset", command=self.reset_zoom, width=6).pack(side=tk.LEFT, padx=2)

        # Brush settings
        ttk.Label(control_frame, text="Brush:").pack(side=tk.LEFT, padx=(20, 0))
        self.brush_scale = ttk.Scale(control_frame, from_=1, to=100, orient=tk.HORIZONTAL, length=150)
        self.brush_scale.set(15)
        self.brush_scale.pack(side=tk.LEFT, padx=2)
        self.brush_label = ttk.Label(control_frame, text="15px")
        self.brush_label.pack(side=tk.LEFT)
        self.brush_scale.config(command=self.on_brush_change)

        ttk.Label(control_frame, text="Mode:").pack(side=tk.LEFT, padx=(20, 0))
        self.mode_var = tk.StringVar(value="brush")
        ttk.Radiobutton(control_frame, text="Brush", variable=self.mode_var, value="brush").pack(side=tk.LEFT)
        ttk.Radiobutton(control_frame, text="Eraser", variable=self.mode_var, value="eraser").pack(side=tk.LEFT)

        # Frame info
        self.info_label = ttk.Label(control_frame, text="No media loaded")
        self.info_label.pack(side=tk.RIGHT, padx=10)

        # Main canvas frame
        self.canvas_frame = ttk.Frame(self.root)
        self.canvas_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Canvas with scrollbars
        self.h_scroll = ttk.Scrollbar(self.canvas_frame, orient=tk.HORIZONTAL)
        self.v_scroll = ttk.Scrollbar(self.canvas_frame, orient=tk.VERTICAL)

        self.canvas = tk.Canvas(
            self.canvas_frame,
            bg="#1a1a1a",
            cursor="crosshair",
            xscrollcommand=self.h_scroll.set,
            yscrollcommand=self.v_scroll.set
        )

        self.h_scroll.config(command=self.canvas.xview)
        self.v_scroll.config(command=self.canvas.yview)

        self.h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        self.v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Bind events
        self.canvas.bind("<Button-1>", self.start_draw)
        self.canvas.bind("<B1-Motion>", self.draw)
        self.canvas.bind("<ButtonRelease-1>", self.stop_draw)
        self.canvas.bind("<Motion>", self.on_mouse_move)
        self.canvas.bind("<MouseWheel>", self.on_mousewheel)
        self.canvas.bind("<Leave>", self.on_mouse_leave)

        # Zoom events (Ctrl + wheel)
        self.canvas.bind("<Control-MouseWheel>", self.on_zoom)
        self.root.bind("<Control-plus>", lambda e: self.zoom_in())
        self.root.bind("<Control-minus>", lambda e: self.zoom_out())
        self.root.bind("<Control-0>", lambda e: self.reset_zoom())

        # Pan events (middle mouse button or Space+drag)
        self.canvas.bind("<Button-2>", self.start_pan)  # middle button
        self.canvas.bind("<B2-Motion>", self.do_pan)
        self.canvas.bind("<ButtonRelease-2>", self.stop_pan)

        # Bottom frame navigation
        self.nav_frame = ttk.Frame(self.root)
        self.nav_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(self.nav_frame, text="<< Prev", command=self.prev_frame).pack(side=tk.LEFT, padx=2)
        self.frame_slider = ttk.Scale(self.nav_frame, from_=0, to=100, orient=tk.HORIZONTAL, command=self.on_slider_change)
        self.frame_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(self.nav_frame, text="Next >>", command=self.next_frame).pack(side=tk.LEFT, padx=2)

        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)

    def on_brush_change(self, value):
        self.brush_size = int(float(value))
        self.brush_label.config(text=f"{self.brush_size}px")

    def on_window_resize(self, event=None):
        if self.original_frame is not None:
            self.calculate_scale()
            self.show_frame()

    def calculate_scale(self):
        if self.original_frame is None:
            return

        canvas_w = self.canvas.winfo_width() - 20
        canvas_h = self.canvas.winfo_height() - 20

        if canvas_w <= 1 or canvas_h <= 1:
            return

        img_h, img_w = self.original_frame.shape[:2]

        scale_w = canvas_w / img_w
        scale_h = canvas_h / img_h
        self.base_scale = min(scale_w, scale_h, 1.0)

        # Apply zoom
        zoom_factor = 1.2 ** self.zoom_level
        self.scale = self.base_scale * zoom_factor

        new_w = int(img_w * self.scale)
        new_h = int(img_h * self.scale)

        self.offset_x = max(0, (canvas_w - new_w) // 2)
        self.offset_y = max(0, (canvas_h - new_h) // 2)

        self.canvas.config(scrollregion=(0, 0, new_w + self.offset_x * 2, new_h + self.offset_y * 2))

    def load_inpainter(self):
        try:
            from inpainter import load_model, inpaint_img_with_lama
            self.inpaint_func = inpaint_img_with_lama
            self.inpainter = load_model(str(self.models_path))
            self.status_var.set("Inpainter loaded")
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            print(tb)
            self.inpainter = None
            self.inpaint_func = None
            self.status_var.set(f"Warning: Inpainter not loaded: {e}")

    def has_cuda(self):
        try:
            import torch
            return torch.cuda.is_available()
        except:
            return False

    def reset_media_state(self):
        if self.cap:
            self.cap.release()
            self.cap = None
        self.is_image = False
        self.image_path = None
        self.original_frame = None
        self.mask = None
        self.frame_idx = 0
        self.total_frames = 0
        self.fps = 30
        self.frame_width = 0
        self.frame_height = 0
        self.zoom_level = 0

    def load_video(self):
        path = filedialog.askopenfilename(
            title="Select Video",
            filetypes=[
                ("Video files", "*.mp4 *.avi *.mov *.mkv *.wmv *.flv"),
                ("All files", "*.*")
            ]
        )
        if not path:
            return

        self.reset_media_state()

        self.cap = cv2.VideoCapture(path)
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.frame_idx = 0

        self.frame_slider.config(to=max(0, self.total_frames - 1), state=tk.NORMAL)
        self.nav_frame.pack(fill=tk.X, padx=5, pady=5)
        self.load_frame(0)
        self.status_var.set(f"Loaded: {os.path.basename(path)} | {self.total_frames} frames")

    def load_image(self):
        path = filedialog.askopenfilename(
            title="Select Image",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.bmp *.tiff *.webp"),
                ("All files", "*.*")
            ]
        )
        if not path:
            return

        self.reset_media_state()

        try:
            pil_img = Image.open(path).convert('RGB')
            self.original_frame = np.array(pil_img)
        except Exception as e:
            messagebox.showerror("Error", f"Cannot load image: {path}\n{e}")
            return

        self.is_image = True
        self.image_path = path
        self.frame_height, self.frame_width = self.original_frame.shape[:2]
        self.total_frames = 1
        self.frame_idx = 0

        self.mask = np.zeros(self.original_frame.shape[:2], dtype=np.uint8)
        self.nav_frame.pack_forget()

        self.calculate_scale()
        self.show_frame()
        self.update_info()
        self.status_var.set(f"Loaded image: {os.path.basename(path)} | {self.frame_width}x{self.frame_height}")

    def load_frame(self, idx):
        if not self.cap or idx < 0 or idx >= self.total_frames:
            return

        self.cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = self.cap.read()
        if not ret:
            return

        self.original_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        if self.mask is None or self.mask.shape[:2] != self.original_frame.shape[:2]:
            self.mask = np.zeros(self.original_frame.shape[:2], dtype=np.uint8)

        self.frame_idx = idx
        self.calculate_scale()
        self.show_frame()
        self.update_info()

    def show_frame(self):
        if self.original_frame is None:
            return

        new_w = int(self.frame_width * self.scale)
        new_h = int(self.frame_height * self.scale)

        if new_w == 0 or new_h == 0:
            return

        display_img = cv2.resize(self.original_frame, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)

        if np.any(self.mask > 0):
            mask_small = cv2.resize(self.mask, (new_w, new_h), interpolation=cv2.INTER_NEAREST)
            overlay = display_img.copy()
            overlay[mask_small > 0] = [255, 0, 0]
            display_img = cv2.addWeighted(display_img, 0.7, overlay, 0.3, 0)

        self.photo = ImageTk.PhotoImage(Image.fromarray(display_img))

        self.canvas.delete("all")
        self.canvas.create_image(self.offset_x, self.offset_y, anchor=tk.NW, image=self.photo, tags="image")
        self.canvas.config(scrollregion=(0, 0, new_w + self.offset_x * 2, new_h + self.offset_y * 2))

    def update_info(self):
        zoom_pct = int((1.2 ** self.zoom_level) * 100)
        if self.is_image:
            self.info_label.config(
                text=f"Image | Size: {self.frame_width}x{self.frame_height} | Scale: {self.scale:.1%} | Zoom: {zoom_pct}%"
            )
        else:
            self.info_label.config(
                text=f"Frame: {self.frame_idx + 1}/{self.total_frames} | "
                     f"Size: {self.frame_width}x{self.frame_height} | "
                     f"Scale: {self.scale:.1%} | Zoom: {zoom_pct}%"
            )

    # ========== ZOOM ==========

    def on_zoom(self, event):
        """Ctrl + колёсико мыши — зум"""
        if event.delta > 0:
            self.zoom_in()
        else:
            self.zoom_out()

    def zoom_in(self):
        self.zoom_level = min(self.zoom_level + 1, 10)  # max ~6x
        self.calculate_scale()
        self.show_frame()
        self.update_info()

    def zoom_out(self):
        self.zoom_level = max(self.zoom_level - 1, -5)  # min ~0.4x
        self.calculate_scale()
        self.show_frame()
        self.update_info()

    def reset_zoom(self):
        self.zoom_level = 0
        self.calculate_scale()
        self.show_frame()
        self.update_info()

    # ========== PAN ==========

    def start_pan(self, event):
        """Средняя кнопка мыши — начало панорамирования"""
        self.panning = True
        self.pan_start_x = event.x
        self.pan_start_y = event.y
        self.scroll_start_x = self.h_scroll.get()[0] if self.h_scroll.get() else 0
        self.scroll_start_y = self.v_scroll.get()[0] if self.v_scroll.get() else 0
        self.canvas.config(cursor="fleur")

    def do_pan(self, event):
        if not self.panning:
            return
        dx = self.pan_start_x - event.x
        dy = self.pan_start_y - event.y
        self.canvas.xview_moveto(self.scroll_start_x + dx / self.canvas.winfo_width())
        self.canvas.yview_moveto(self.scroll_start_y + dy / self.canvas.winfo_height())

    def stop_pan(self, event):
        self.panning = False
        self.canvas.config(cursor="crosshair")

    # ========== DRAWING ==========

    def canvas_to_image_coords(self, canvas_x, canvas_y):
        """Преобразует координаты canvas в координаты исходного изображения с учётом зума и скролла"""
        # Учитываем скролл: canvasx/canvasy возвращают позицию в логических координатах canvas
        logical_x = self.canvas.canvasx(canvas_x)
        logical_y = self.canvas.canvasy(canvas_y)

        img_x = int((logical_x - self.offset_x) / self.scale)
        img_y = int((logical_y - self.offset_y) / self.scale)

        img_x = max(0, min(img_x, self.frame_width - 1))
        img_y = max(0, min(img_y, self.frame_height - 1))

        return img_x, img_y


    def start_draw(self, event):
        if self.panning:
            return
        self.drawing = True
        self.last_x, self.last_y = self.canvas_to_image_coords(event.x, event.y)
        self.draw(event)

    def draw(self, event):
        if not self.drawing or self.original_frame is None:
            return

        img_x, img_y = self.canvas_to_image_coords(event.x, event.y)
        brush = int(self.brush_size)

        if self.mode_var.get() == "brush":
            color = 255
        else:
            color = 0

        cv2.line(self.mask, (img_x, img_y), (self.last_x, self.last_y), color, brush * 2)
        cv2.circle(self.mask, (img_x, img_y), brush, color, -1)

        self.last_x, self.last_y = img_x, img_y
        self.show_frame()

    def stop_draw(self, event):
        self.drawing = False

    def on_mouse_move(self, event):
        if self.original_frame is None:
            return

        if self.cursor_id:
            self.canvas.delete(self.cursor_id)

        # Используем логические координаты (с учётом скролла) для позиционирования круга
        logical_x = self.canvas.canvasx(event.x)
        logical_y = self.canvas.canvasy(event.y)

        display_brush = max(2, int(self.brush_size * self.scale))

        self.cursor_id = self.canvas.create_oval(
            logical_x - display_brush, logical_y - display_brush,
            logical_x + display_brush, logical_y + display_brush,
            outline="yellow", width=2, tags="cursor"
        )

    def on_mouse_leave(self, event):
        if self.cursor_id:
            self.canvas.delete(self.cursor_id)
            self.cursor_id = None

    def on_mousewheel(self, event):
        """Без Ctrl — изменение размера кисти"""
        delta = event.delta // 120
        current = self.brush_scale.get()
        new_val = max(1, min(100, current + delta * 2))
        self.brush_scale.set(new_val)
        self.on_brush_change(new_val)

    def on_slider_change(self, value):
        if self.cap and not self.is_image:
            self.load_frame(int(float(value)))

    def prev_frame(self):
        if not self.is_image and self.frame_idx > 0:
            self.load_frame(self.frame_idx - 1)
            self.frame_slider.set(self.frame_idx)

    def next_frame(self):
        if not self.is_image and self.frame_idx < self.total_frames - 1:
            self.load_frame(self.frame_idx + 1)
            self.frame_slider.set(self.frame_idx)

    def save_mask(self):
        if self.mask is None:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png"), ("All files", "*.*")]
        )
        if path:
            mask_img = Image.fromarray(self.mask)
            mask_img.save(path)
            self.status_var.set(f"Mask saved: {path}")

    def process_current(self):
        if self.original_frame is None:
            messagebox.showwarning("Warning", "No image or video loaded")
            return

        if not np.any(self.mask > 0):
            messagebox.showwarning("Warning", "Draw mask first!")
            return

        if self.inpainter is None or self.inpaint_func is None:
            self.load_inpainter()
            if self.inpainter is None:
                messagebox.showerror("Error", "Inpainter not available. Check models folder.")
                return

        self.processing = True
        self.status_var.set("Processing...")
        self.root.update()

        try:
            result = self.inpaint_func(
                self.original_frame,
                self.mask,
                self.inpainter,
                device="cuda" if self.has_cuda() else "cpu"
            )
            self.original_frame = result
            self.mask = np.zeros_like(self.mask)
            self.show_frame()
            self.status_var.set("Processed successfully")
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            print(tb)
            self.status_var.set(f"Error: {e}")
            messagebox.showerror("Error", f"{e}\n\n{tb}")
        finally:
            self.processing = False

    def process_all(self):
        if self.is_image:
            self.process_current()
            return

        if self.cap is None:
            messagebox.showwarning("Warning", "No video loaded")
            return

        if not np.any(self.mask > 0):
            messagebox.showwarning("Warning", "Draw mask on first frame first!")
            return

        if self.inpainter is None or self.inpaint_func is None:
            self.load_inpainter()
            if self.inpainter is None:
                messagebox.showerror("Error", "Inpainter not available. Check models folder.")
                return

        output_path = filedialog.asksaveasfilename(
            defaultextension=".mp4",
            filetypes=[("MP4 files", "*.mp4"), ("AVI files", "*.avi"), ("All files", "*.*")]
        )
        if not output_path:
            return

        self.processing = True
        self.status_var.set("Processing all frames...")

        def process_thread():
            import traceback
            try:
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                out = cv2.VideoWriter(output_path, fourcc, self.fps,
                                      (self.frame_width, self.frame_height))

                global_mask = self.mask.copy()

                for i in range(self.total_frames):
                    if not self.processing:
                        break

                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, i)
                    ret, frame = self.cap.read()
                    if not ret:
                        break

                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                    if np.any(global_mask > 0):
                        result = self.inpaint_func(
                            frame_rgb, global_mask, self.inpainter,
                            device="cuda" if self.has_cuda() else "cpu"
                        )
                    else:
                        result = frame_rgb

                    result_bgr = cv2.cvtColor(result, cv2.COLOR_RGB2BGR)
                    out.write(result_bgr)

                    if i % 10 == 0:
                        def update_status(idx=i):
                            self.status_var.set(f"Processing: {idx + 1}/{self.total_frames}")
                        self.root.after(0, update_status)

                out.release()
                self.root.after(0, lambda: self.status_var.set(f"Saved: {output_path}"))
                self.root.after(0, lambda: messagebox.showinfo("Done", "Video processing complete!"))

            except Exception as e:
                tb = traceback.format_exc()
                print(tb)
                self.root.after(0, lambda: self.status_var.set(f"Error: {e}"))
                self.root.after(0, lambda: messagebox.showerror("Error", f"{e}\n\n{tb}"))
            finally:
                self.processing = False

        threading.Thread(target=process_thread, daemon=True).start()

    def save_result(self):
        if self.original_frame is None:
            return

        if self.is_image:
            path = filedialog.asksaveasfilename(
                defaultextension=".png",
                filetypes=[
                    ("PNG files", "*.png"),
                    ("JPEG files", "*.jpg"),
                    ("All files", "*.*")
                ]
            )
            if path:
                pil_img = Image.fromarray(self.original_frame)
                pil_img.save(path)
                self.status_var.set(f"Image saved: {path}")
        else:
            self.process_all()


if __name__ == "__main__":
    root = tk.Tk()
    app = WatermarkRemover(root)
    root.mainloop()