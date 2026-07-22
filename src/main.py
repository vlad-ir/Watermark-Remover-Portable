"""
Watermark Remover - PyQt6 Edition
Modern UI with brush tool for marking watermarks on images and video frames.
"""

import sys
import os
import tempfile
import subprocess
import time
import threading
from pathlib import Path
from PIL import Image
import cv2
import numpy as np

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QSlider, QFileDialog, QMessageBox, QProgressDialog,
    QSpinBox, QFrame, QScrollArea, QSizePolicy, QGraphicsView, QGraphicsScene,
    QGraphicsPixmapItem, QGraphicsEllipseItem, QGraphicsProxyWidget,
    QDialog, QProgressBar, QToolButton, QStyle
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QPoint, QRectF, QSize, QSettings, QDir
from PyQt6.QtGui import (
    QPixmap, QImage, QPainter, QPen, QColor, QBrush, QFont,
    QIcon, QCursor, QWheelEvent, QMouseEvent, QKeyEvent,
    QPalette, QPainterPath, QShortcut, QKeySequence
)
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtCore import QByteArray

from inpainter import load_model, inpaint_img_with_lama


# =============================================================================
# STYLESHEET - Dark theme matching your Flet design
# =============================================================================
DARK_STYLESHEET = """
QMainWindow {
    background-color: #1A1A1A;
}

QWidget {
    background-color: #1A1A1A;
    color: #FFFFFF;
    font-family: 'Segoe UI', Arial, sans-serif;
}

/* Top Panel */
#topPanel {
    background-color: #1A1A1A;
    padding: 8px 16px;
}

#loadButton {
    background-color: #4F46E5;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 10px 20px;
    font-size: 14px;
    font-weight: 600;
}
#loadButton:hover {
    background-color: #5B54E8;
}
#loadButton:pressed {
    background-color: #4338CA;
}

#infoLabel {
    color: #9CA3AF;
    font-size: 13px;
}

#iconButton {
    background-color: transparent;
    border: none;
    padding: 0px;
    border-radius: 18px;
    width: 36px;
    height: 36px;
    max-width: 36px;
    max-height: 36px;
}
#iconButton:hover {
    background-color: rgba(255, 255, 255, 0.08);
}

/* Main Content / Canvas */
#canvasContainer {
    background-color: #2D2D2D;
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 12px;
    padding: 10px;
}

#placeholderLabel {
    color: rgba(255,255,255,0.54);
    font-size: 16px;
}

/* Player Panel */
#playerPanel {
    background-color: #1A1A1A;
    padding: 4px 16px;
    min-height: 50px;
}

#timeLabel, #frameLabel, #videoInfoLabel {
    color: #9CA3AF;
    font-size: 13px;
}


QSlider {
    height: 34px;
}

QSlider::groove:horizontal {
    height: 4px;
    background: rgba(255,255,255,0.24);
    border-radius: 1px;
    margin: 7px 0;
}
QSlider::sub-page:horizontal {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3B82F6, stop:1 #8B5CF6);
    border-radius: 1px;
    height: 4px;
    margin: 5px 0;
}
QSlider::handle:horizontal {
    width: 14px;
    height: 16px;
    margin: -7px 0;
    background: #1A1A1A;
    border-radius: 8px;
    border: 2px solid white;
}

#navButton {
    background-color: #252530;
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 8px;
    color: rgba(255,255,255,0.7);
    font-size: 14px;
    padding: 4px;
}
#navButton:hover {
    background-color: #2D2D3D;
    border: 1px solid rgba(255,255,255,0.24);
    color: white;
}
#navButton:pressed {
    background-color: #1E1E2E;
}

/* Image Info Panel */
#imageInfoPanel {
    background-color: #252530;
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 8px;
    min-height: 36px;
}
#imageInfoLabel {
    color: #9CA3AF;
    font-size: 13px;
    font-weight: 500;
}

/* Thumbnails */
#thumbnailScroll {
    background-color: #1A1A1A;
    border: none;
}
#thumbnailWidget {
    background-color: #1A1A1A;
}
#thumbButton {
    background-color: transparent;
    border: 1px solid rgba(255,255,255,0.24);
    border-radius: 4px;
    padding: 0;
}
#thumbButton:hover {
    border: 1px solid #8B5CF6;
}

/* Tools Panel */
#toolsPanel {
    background-color: #1A1A1A;
    padding: 4px 16px;
    min-height: 60px;
}

#toolLabel {
    color: #9CA3AF;
    font-size: 16px;
}

QSpinBox {
    background-color: #2A2A2A;
    border: 1px solid rgba(255,255,255,0.24);
    border-radius: 6px;
    color: white;
    font-size: 14px;
    padding: 2px 4px;
}

#zoomButtonLeft {
    background-color: transparent;
    border: none;
    padding: 0px 0px 2px 0px;
    border-top-left-radius: 7px;
    border-bottom-left-radius: 7px;
    border-top-right-radius: 0px;
    border-bottom-right-radius: 0px;
    width: 44px;
    height: 34px;
    max-width: 44px;
    max-height: 34px;
    color: rgba(255,255,255,0.7);
    font-size: 22px;
    font-weight: bold;
}
#zoomButtonLeft:hover {
    background-color: rgba(255, 255, 255, 0.08);
    color: white;
}
#zoomButtonRight {
    background-color: transparent;
    border: none;
    padding: 0px 0px 2px 0px;
    border-top-left-radius: 0px;
    border-bottom-left-radius: 0px;
    border-top-right-radius: 7px;
    border-bottom-right-radius: 7px;
    width: 44px;
    height: 34px;
    max-width: 44px;
    max-height: 34px;
    color: rgba(255,255,255,0.7);
    font-size: 22px;
    font-weight: bold;
}
#zoomButtonRight:hover {
    background-color: rgba(255, 255, 255, 0.08);
    color: white;
}
#zoomContainer {
    background-color: transparent;
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 8px;
}


#playButton {
    background-color: #252530;
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 12px;
    padding: 0px;
    width: 48px;
    height: 48px;
    max-width: 48px;
    max-height: 48px;
}
#playButton:hover {
    background-color: #2D2D3D;
    border: 1px solid rgba(255,255,255,0.24);
}
#playButton:pressed {
    background-color: #1E1E2E;
}

#clearButton {
    background-color: #DC2626;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 12px 20px;
    font-size: 14px;
    font-weight: 600;
}
#clearButton:hover {
    background-color: #EF4444;
}
#clearButton:pressed {
    background-color: #B91C1C;
}

#removeButton {
    background-color: #4F46E5;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 12px 20px;
    font-size: 14px;
    font-weight: 600;
}
#removeButton:hover {
    background-color: #5B54E8;
}
#removeButton:pressed {
    background-color: #4338CA;
}

/* Thumbnails scrollbar styling */
QScrollArea#thumbnailScroll {
    border: none;
    background-color: #1A1A1A;
}
QScrollBar:horizontal {
    background: transparent;
    height: 10px;
    margin: 0px;
}
QScrollBar::handle:horizontal {
    background: rgba(139, 92, 246, 0.5);
    min-width: 40px;
    border-radius: 5px;
}
QScrollBar::handle:horizontal:hover {
    background: rgba(139, 92, 246, 0.8);
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
    background: transparent;
}

QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background: rgba(139, 92, 246, 0.5);
    min-height: 40px;
    border-radius: 5px;
}
QScrollBar::handle:vertical:hover {
    background: rgba(139, 92, 246, 0.8);
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: transparent;
}

/* Progress Dialog */
QProgressDialog {
    background-color: #1E1E2E;
    border-radius: 16px;
}
QProgressDialog QLabel {
    color: white;
    font-size: 16px;
    padding: 8px;
}
QProgressDialog QPushButton {
    background-color: #4F46E5;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 10px 24px;
    font-size: 14px;
    font-weight: 600;
    margin-top: 16px;
}
QProgressDialog QPushButton:hover {
    background-color: #5B54E8;
}
QProgressBar {
    border: none;
    border-radius: 6px;
    background-color: #2D2D3D;
    height: 24px;
    text-align: center;
    color: white;
    font-size: 14px;
    font-weight: 600;
}
QProgressBar::chunk {
    background-color: #8B5CF6;
    border-radius: 6px;
}
"""


# =============================================================================
# VIDEO FRAME EXTRACTOR THREAD
# =============================================================================
class FrameExtractor(QThread):
    progress = pyqtSignal(int, int)  # current, total
    finished_extract = pyqtSignal(int)  # extracted_count

    def __init__(self, video_path, assets_dir, total_frames):
        super().__init__()
        self.video_path = video_path
        self.assets_dir = assets_dir
        self.total_frames = total_frames
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def run(self):
        cap = cv2.VideoCapture(self.video_path)
        idx = 0

        while not self._cancel:
            ret, frame = cap.read()
            if not ret:
                break

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil = Image.fromarray(frame_rgb)
            pil.save(
                os.path.join(self.assets_dir, f"frame_{idx:06d}.jpg"),
                "JPEG", quality=85
            )
            idx += 1

            if idx % 5 == 0 or idx >= self.total_frames - 3:
                self.progress.emit(idx, self.total_frames)

        cap.release()
        self.finished_extract.emit(idx)


# =============================================================================
# CANVAS WIDGET - Image/Video display with brush
# =============================================================================
class CanvasWidget(QGraphicsView):
    """Custom graphics view with brush tool support"""
    zoom_changed = pyqtSignal(float)  # zoom_percent

    def __init__(self, parent=None, main_window=None):
        super().__init__(parent)
        self._main_window = main_window
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        # Appearance
        self.setStyleSheet("background-color: #2D2D2D; border: 1px solid rgba(255,255,255,0.12); border-radius: 12px;")
        self.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)

        # Scrollbars - show when content doesn't fit
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Items
        self.pixmap_item = None
        self.frame_masks = {}
        self.current_mask = None
        self.current_frame_idx = 0
        self.mask_pixmap_item = None
        self.is_erasing = False
        self.undo_stack = []
        self.redo_stack = []
        self.undo_limit = 5
        self._stroke_mask_before = None
        self.cursor_item = None
        self.placeholder_item = None

        # Brush state
        self.brush_size = 45
        self.is_drawing = False
        self.has_media = False

        # Zoom state
        self.base_scale = 1.0
        self.zoom_percent = 100.0  # 100 = fit to view (base_scale)
        self.min_zoom = 10.0
        self.max_zoom = 900.0
        self.is_fit_to_view = True

        # Cursor
        self.setMouseTracking(True)
        self._setup_cursor()
        self._setup_placeholder()

    def _cursor_pen_width(self):
        """Return cursor pen width based on zoom level"""
        return 1 if self.zoom_percent > 200 else 3

    def _setup_cursor(self):
        """Setup brush cursor (yellow circle with crosshair)"""
        self.cursor_item = QGraphicsEllipseItem(0, 0, self.brush_size, self.brush_size)
        pen = QPen(QColor("#FFD700"))
        pen.setWidth(self._cursor_pen_width())
        self.cursor_item.setPen(pen)
        self.cursor_item.setBrush(QBrush(Qt.BrushStyle.NoBrush))
        self.cursor_item.setVisible(False)
        self.cursor_item.setZValue(1000)  # Always on top
        self.scene.addItem(self.cursor_item)

    def _set_cursor_color(self, color_hex):
        """Change cursor circle color (yellow for draw, red for erase)"""
        if self.cursor_item:
            pen = QPen(QColor(color_hex))
            pen.setWidth(self._cursor_pen_width())
            self.cursor_item.setPen(pen)

    def _update_cursor_appearance(self):
        """Update cursor pen width when zoom changes"""
        if not self.cursor_item:
            return
        color = "#FF4444" if self.is_erasing else "#FFD700"
        pen = QPen(QColor(color))
        pen.setWidth(self._cursor_pen_width())
        self.cursor_item.setPen(pen)

    def _setup_placeholder(self):
        """Setup placeholder icon and text when no media loaded"""
        # Create icon - use white color for visibility on dark background
        icon = create_icon_svg("image", "white", 80)
        icon_pixmap = icon.pixmap(QSize(80, 80))
        self.placeholder_icon = self.scene.addPixmap(icon_pixmap)
        self.placeholder_icon.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
        self.placeholder_icon.setZValue(100)
        self.placeholder_icon.setOpacity(0.24)

        # Create text
        self.placeholder_text = self.scene.addText("Load an image or video to get started")
        font = QFont("Segoe UI", 14)
        self.placeholder_text.setFont(font)
        self.placeholder_text.setDefaultTextColor(QColor(255, 255, 255, 138))
        self.placeholder_text.setZValue(100)

        self._center_placeholder()

    def _center_placeholder(self):
        """Center placeholder in the view"""
        if not self.placeholder_icon or not self.placeholder_text:
            return

        view_rect = self.viewport().rect()
        scene_rect = self.mapToScene(view_rect).boundingRect()
        center_x = scene_rect.center().x()
        center_y = scene_rect.center().y()

        # Center icon
        icon_rect = self.placeholder_icon.boundingRect()
        self.placeholder_icon.setPos(
            center_x - icon_rect.width() / 2,
            center_y - icon_rect.height() / 2 - 30
        )

        # Center text below icon
        text_rect = self.placeholder_text.boundingRect()
        self.placeholder_text.setPos(
            center_x - text_rect.width() / 2,
            center_y + icon_rect.height() / 2 - 10
        )

    def _update_transform(self):
        """Apply current zoom transform. Recalculates base_scale from current viewport size."""
        if not self.pixmap_item:
            return

        view_rect = self.viewport().rect()
        img_rect = self.pixmap_item.boundingRect()

        # Calculate base scale to fit image in view (KeepAspectRatio)
        scale_x = view_rect.width() / img_rect.width()
        scale_y = view_rect.height() / img_rect.height()
        self.base_scale = min(scale_x, scale_y)

        self.resetTransform()

        if self.is_fit_to_view:
            self.zoom_percent = 100.0
            self.scale(self.base_scale, self.base_scale)
        else:
            scale = self.base_scale * (self.zoom_percent / 100.0)
            self.scale(scale, scale)

        self._update_cursor_appearance()
        self.zoom_changed.emit(self.zoom_percent)

    def set_brush_size(self, size):
        self.brush_size = size
        if self.cursor_item:
            self.cursor_item.setRect(0, 0, size, size)

    def load_image(self, pixmap):
        self.scene.clear()
        self.frame_masks = {}
        self.current_frame_idx = 0
        self.current_mask = np.zeros((pixmap.height(), pixmap.width()), dtype=np.uint8)
        self.mask_pixmap_item = None
        self.placeholder_icon = None
        self.placeholder_text = None
        self.pixmap_item = self.scene.addPixmap(pixmap)
        self.pixmap_item.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
        self.setSceneRect(self.pixmap_item.boundingRect())
        self._setup_cursor()
        self.has_media = True
        self.is_fit_to_view = True
        self.zoom_percent = 100.0
        self._update_transform()

    def load_frame(self, pixmap, frame_idx=0):
        # Clear everything including placeholder
        self.scene.clear()
        self.current_frame_idx = frame_idx
        h, w = pixmap.height(), pixmap.width()
        self.current_mask = self._get_mask_for_frame(frame_idx, h, w)
        self.mask_pixmap_item = None
        self.placeholder_icon = None
        self.placeholder_text = None
        self.pixmap_item = self.scene.addPixmap(pixmap)
        self.pixmap_item.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
        self.setSceneRect(self.pixmap_item.boundingRect())
        self.has_media = True
        # Re-add cursor on top
        self._setup_cursor()
        self._update_mask_display()
        self._update_transform()

    def clear_mask(self):
        """Clear the mask for current frame — saves empty mask so later frames inherit empty"""
        if self.current_mask is not None:
            self.current_mask.fill(0)
            self.frame_masks[self.current_frame_idx] = self.current_mask.copy()
            self._update_mask_display()

    def _get_image_pos(self, pos):
        """Convert mouse position to image coordinates"""
        if not self.pixmap_item:
            return None
        img_rect = self.pixmap_item.boundingRect()
        scene_pos = self.mapToScene(pos)
        # Check if within image bounds
        if not img_rect.contains(scene_pos):
            return None
        return scene_pos

    def mouseMoveEvent(self, event: QMouseEvent):
        pos = event.pos()
        img_pos = self._get_image_pos(pos)

        if img_pos and self.has_media:
            self.cursor_item.setVisible(True)
            self.cursor_item.setPos(
                img_pos.x() - self.brush_size / 2,
                img_pos.y() - self.brush_size / 2
            )

            if event.buttons() == Qt.MouseButton.LeftButton and self.is_drawing:
                self._draw_stamp(img_pos)
            elif event.buttons() == Qt.MouseButton.RightButton and self.is_erasing:
                self._draw_stamp(img_pos)
        else:
            self.cursor_item.setVisible(False)

        super().mouseMoveEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
        if not self.has_media:
            super().mousePressEvent(event)
            return

        if event.button() == Qt.MouseButton.LeftButton:
            self.is_drawing = True
            self.is_erasing = False
            self._set_cursor_color("#FFD700")  # yellow
            self._stroke_mask_before = self.current_mask.copy() if self.current_mask is not None else None
            pos = self._get_image_pos(event.pos())
            if pos:
                self._draw_stamp(pos)
        elif event.button() == Qt.MouseButton.RightButton:
            self.is_erasing = True
            self.is_drawing = False
            self._set_cursor_color("#FF4444")  # red for eraser
            self._stroke_mask_before = self.current_mask.copy() if self.current_mask is not None else None
            pos = self._get_image_pos(event.pos())
            if pos:
                self._draw_stamp(pos)

        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_drawing = False
            self._push_undo()
        elif event.button() == Qt.MouseButton.RightButton:
            self.is_erasing = False
            self._push_undo()
            self._set_cursor_color("#FFD700")  # back to yellow
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event: QWheelEvent):
        """Ctrl+Wheel = zoom, Wheel = brush size"""
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.zoom_in()
            else:
                self.zoom_out()
            event.accept()
            return

        # Adjust brush size with mouse wheel
        delta = event.angleDelta().y()
        if delta > 0:
            self.brush_size = min(200, self.brush_size + 5)
        else:
            self.brush_size = max(3, self.brush_size - 5)
        self.set_brush_size(self.brush_size)
        # Emit signal to update spinbox and slider in main window
        if self._main_window is not None:
            self._main_window.brush_size_changed.emit(self.brush_size)
        event.accept()

    def zoom_in(self):
        if self.is_fit_to_view:
            self.is_fit_to_view = False
            self.zoom_percent = 100.0
        self.zoom_percent = min(self.max_zoom, self.zoom_percent * 1.2)
        self._update_transform()

    def zoom_out(self):
        if self.is_fit_to_view:
            return
        self.zoom_percent = max(self.min_zoom, self.zoom_percent / 1.2)
        self._update_transform()

    def reset_zoom(self):
        self.is_fit_to_view = True
        self.zoom_percent = 100.0
        self._update_transform()

    def _draw_stamp(self, pos):
        """Draw brush stamp on mask array and update display"""
        if self.pixmap_item is None or self.current_mask is None:
            return

        x = int(round(pos.x()))
        y = int(round(pos.y()))

        h, w = self.current_mask.shape
        radius = int(self.brush_size / 2)

        if x < 0 or x >= w or y < 0 or y >= h:
            return

        if self.is_erasing:
            cv2.circle(self.current_mask, (x, y), radius, 0, -1)
        else:
            cv2.circle(self.current_mask, (x, y), radius, 255, -1)

        self.frame_masks[self.current_frame_idx] = self.current_mask.copy()
        self._update_mask_display()

    def _get_mask_for_frame(self, frame_idx, h, w):
        """Return mask for given frame: own, inherited from previous, or empty"""
        if frame_idx in self.frame_masks:
            return self.frame_masks[frame_idx].copy()
        prev_indices = [idx for idx in self.frame_masks if idx < frame_idx]
        if prev_indices:
            nearest = max(prev_indices)
            return self.frame_masks[nearest].copy()
        return np.zeros((h, w), dtype=np.uint8)

    def set_current_frame(self, idx):
        """Set current frame index for mask storage"""
        self.current_frame_idx = idx

    def _push_undo(self):
        """Save current stroke to undo stack if mask changed"""
        if self._stroke_mask_before is None or self.current_mask is None:
            return
        if np.array_equal(self._stroke_mask_before, self.current_mask):
            return
        self.undo_stack.append({
            'frame_idx': self.current_frame_idx,
            'before': self._stroke_mask_before.copy(),
            'after': self.current_mask.copy(),
        })
        if len(self.undo_stack) > self.undo_limit:
            self.undo_stack.pop(0)
        self.redo_stack.clear()
        self._stroke_mask_before = None

    def undo(self):
        """Undo last stroke (Ctrl+Z)"""
        if not self.undo_stack:
            return
        action = self.undo_stack.pop()
        self.redo_stack.append(action)
        self._restore_mask(action['frame_idx'], action['before'])

    def redo(self):
        """Redo last undone stroke (Ctrl+Shift+Z)"""
        if not self.redo_stack:
            return
        action = self.redo_stack.pop()
        self.undo_stack.append(action)
        self._restore_mask(action['frame_idx'], action['after'])

    def _restore_mask(self, frame_idx, mask):
        """Restore mask for a specific frame"""
        self.frame_masks[frame_idx] = mask.copy()
        if frame_idx == self.current_frame_idx:
            self.current_mask = mask.copy()
            self._update_mask_display()

    def _update_mask_display(self):
        """Convert mask array to semi-transparent pink overlay"""
        if self.current_mask is None:
            return

        h, w = self.current_mask.shape

        rgba = np.zeros((h, w, 4), dtype=np.uint8)
        mask = self.current_mask > 0
        rgba[mask] = [255, 105, 180, 110]  # R, G, B, A (more visible)

        # Safe: convert numpy array to Python bytes before passing to QImage
        # This avoids "memory not pinned" errors in PyQt6
        image = QImage(rgba.tobytes(), w, h, w * 4, QImage.Format.Format_RGBA8888)
        pixmap = QPixmap.fromImage(image)

        if self.mask_pixmap_item is None:
            self.mask_pixmap_item = self.scene.addPixmap(pixmap)
            self.mask_pixmap_item.setZValue(500)
        else:
            self.mask_pixmap_item.setPixmap(pixmap)

    def get_mask(self):
        """Return current mask as numpy array (0-255)"""
        return self.current_mask

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.pixmap_item:
            self._update_transform()
        else:
            self._center_placeholder()


# =============================================================================
# MAIN WINDOW
# =============================================================================
def create_icon_svg(name, color="white", size=24):
    """Create QIcon from inline SVG path data (outline style)"""

    # SVG paths for outline icons (white lines on transparent)
    paths = {
        "folder": """<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>""",

        "info": """<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>""",

        "settings": """<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.6 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.6a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>""",

        "more": """<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/><circle cx="5" cy="12" r="1"/></svg>""",

        "play": """<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 3 19 12 5 21 5 3"/></svg>""",

        "pause": """<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="9" y1="4" x2="9" y2="20"/><line x1="15" y1="4" x2="15" y2="20"/></svg>""",

        "prev": """<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/></svg>""",

        "next": """<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>""",

        "zoom_in": """<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/><line x1="11" y1="8" x2="11" y2="14"/><line x1="8" y1="11" x2="14" y2="11"/></svg>""",

        "zoom_out": """<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/><line x1="8" y1="11" x2="14" y2="11"/></svg>""",

        "trash": """<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>""",

        "x": """<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>""",

        "image": """<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>""",
    }

    svg_str = paths.get(name, "").format(color=color, size=size)
    svg_bytes = QByteArray(svg_str.encode('utf-8'))
    renderer = QSvgRenderer(svg_bytes)

    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()

    return QIcon(pixmap)


class WatermarkRemoverWindow(QMainWindow):
    brush_size_changed = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Watermark Remover")
        self.setMinimumSize(800, 600)
        self.resize(1100, 800)

        # Directories
        self.script_dir = Path(__file__).resolve().parent
        self.assets_dir = self.script_dir.parent / "assets"
        self.assets_dir.mkdir(exist_ok=True)
        self.temp_dir = Path(tempfile.mkdtemp())
        self.counter = 0

        # Settings: remember last directory across sessions
        self.settings = QSettings("WatermarkRemover", "App")
        self.last_directory = self.settings.value("last_directory", QDir.homePath())

        # Video state
        self.cap = None
        self.is_video = False
        self.total_frames = 0
        self.current_frame = 0
        self.fps = 30
        self.frames_extracted = False
        self.extracted_count = 0
        self.is_playing = False
        self.play_timer = QTimer(self)
        self.play_timer.timeout.connect(self._next_frame)

        # Frame extractor thread
        self.extractor = None

        # Model
        self.model = None
        self._check_model()

        # Setup UI
        self._setup_ui()
        self._apply_styles()
        # Install global event filter for keyboard shortcuts
        QApplication.instance().installEventFilter(self)

        # Enable keyboard focus for arrow key navigation
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def _setup_ui(self):
        """Setup all UI components"""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # ===== 1. TOP PANEL =====
        top_panel = QWidget()
        top_panel.setObjectName("topPanel")
        top_layout = QHBoxLayout(top_panel)
        top_layout.setContentsMargins(0, 0, 0, 0)

        self.load_btn = QPushButton("  Load Media")
        self.load_btn.setObjectName("loadButton")
        self.load_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.load_btn.setIcon(create_icon_svg("folder", "white", 18))
        self.load_btn.setIconSize(QSize(18, 18))
        self.load_btn.clicked.connect(self._on_load_click)
        top_layout.addWidget(self.load_btn)

        info_label = QLabel("Supports photos and videos (JPG, PNG, MP4, MOV, etc.)")
        info_label.setObjectName("infoLabel")
        top_layout.addWidget(info_label, 1)

        # Info icon
        btn_info = QToolButton()
        btn_info.setObjectName("iconButton")
        btn_info.setIcon(create_icon_svg("info", "#9CA3AF", 20))
        btn_info.setIconSize(QSize(20, 20))
        btn_info.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_info.clicked.connect(self._show_info_dialog)
        top_layout.addWidget(btn_info)

        # Settings icon
        btn_settings = QToolButton()
        btn_settings.setObjectName("iconButton")
        btn_settings.setIcon(create_icon_svg("settings", "#9CA3AF", 20))
        btn_settings.setIconSize(QSize(20, 20))
        btn_settings.setCursor(Qt.CursorShape.PointingHandCursor)
        top_layout.addWidget(btn_settings)

        # More icon
        btn_more = QToolButton()
        btn_more.setObjectName("iconButton")
        btn_more.setIcon(create_icon_svg("more", "#9CA3AF", 20))
        btn_more.setIconSize(QSize(20, 20))
        btn_more.setCursor(Qt.CursorShape.PointingHandCursor)
        top_layout.addWidget(btn_more)

        layout.addWidget(top_panel)

        # ===== 2. MAIN CONTENT / CANVAS =====
        self.canvas = CanvasWidget(self, main_window=self)
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.canvas.zoom_changed.connect(self._update_zoom_label)
        layout.addWidget(self.canvas, 1)

        # ===== 3. PLAYER PANEL (video only) =====
        self.player_panel = QWidget()
        self.player_panel.setObjectName("playerPanel")
        self.player_panel.setVisible(False)
        player_layout = QHBoxLayout(self.player_panel)
        player_layout.setContentsMargins(0, 0, 0, 0)

        self.play_btn = QPushButton()
        self.play_btn.setObjectName("playButton")
        self.play_btn.setFixedSize(36, 36)
        self.play_btn.setIcon(create_icon_svg("play", "white", 22))
        self.play_btn.setIconSize(QSize(22, 22))
        self.play_btn.clicked.connect(self._on_play_click)
        player_layout.addWidget(self.play_btn)

        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(8, 0, 8, 0)
        info_layout.setSpacing(2)

        self.time_label = QLabel("00:00:00 / 00:00:00")
        self.time_label.setObjectName("timeLabel")
        info_layout.addWidget(self.time_label)

        self.frame_label = QLabel("Frame: 0 / 0")
        self.frame_label.setObjectName("frameLabel")
        info_layout.addWidget(self.frame_label)

        self.video_info_label = QLabel("")
        self.video_info_label.setObjectName("videoInfoLabel")
        info_layout.addWidget(self.video_info_label)

        player_layout.addWidget(info_widget)

        self.timeline = QSlider(Qt.Orientation.Horizontal)
        self.timeline.setRange(0, 100)
        self.timeline.setValue(0)
        self.timeline.sliderMoved.connect(self._on_timeline_change)
        player_layout.addWidget(self.timeline, 1)

        self.prev_btn = QToolButton()
        self.prev_btn.setObjectName("navButton")
        self.prev_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        self.prev_btn.setText("Previous")
        self.prev_btn.setIcon(create_icon_svg("prev", "white", 26))
        self.prev_btn.setIconSize(QSize(26, 26))
        self.prev_btn.setFixedSize(110, 60)
        self.prev_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.prev_btn.clicked.connect(self._on_prev_frame)
        player_layout.addWidget(self.prev_btn)

        self.next_btn = QToolButton()
        self.next_btn.setObjectName("navButton")
        self.next_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        self.next_btn.setText("Next")
        self.next_btn.setIcon(create_icon_svg("next", "white", 26))
        self.next_btn.setIconSize(QSize(26, 26))
        self.next_btn.setFixedSize(110, 60)
        self.next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.next_btn.clicked.connect(self._on_next_frame)
        player_layout.addWidget(self.next_btn)

        layout.addWidget(self.player_panel)

        # ===== 4. IMAGE INFO PANEL (images only) =====
        # Image info panel - full width, centered content
        self.image_info_panel = QWidget()
        self.image_info_panel.setObjectName("imageInfoPanel")
        self.image_info_panel.setVisible(False)
        img_info_layout = QHBoxLayout(self.image_info_panel)
        img_info_layout.setContentsMargins(16, 8, 16, 8)
        img_info_layout.setSpacing(8)

        img_info_layout.addStretch()

        img_icon = QLabel()
        img_icon.setPixmap(create_icon_svg("image", "#8B5CF6", 18).pixmap(QSize(18, 18)))
        img_icon.setFixedWidth(24)
        img_icon.setStyleSheet("background-color: transparent;")
        img_info_layout.addWidget(img_icon)

        self.image_info_label = QLabel("")
        self.image_info_label.setObjectName("imageInfoLabel")
        self.image_info_label.setStyleSheet("background-color: transparent;")
        img_info_layout.addWidget(self.image_info_label)

        img_info_layout.addStretch()

        layout.addWidget(self.image_info_panel)

        # ===== 5. THUMBNAILS (video only) =====
        self.thumbnail_scroll = QScrollArea()
        self.thumbnail_scroll.setObjectName("thumbnailScroll")
        self.thumbnail_scroll.setWidgetResizable(True)
        self.thumbnail_scroll.setFixedHeight(60)
        self.thumbnail_scroll.setVisible(False)
        self.thumbnail_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.thumbnail_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.thumbnail_widget = QWidget()
        self.thumbnail_widget.setObjectName("thumbnailWidget")
        self.thumbnail_layout = QHBoxLayout(self.thumbnail_widget)
        self.thumbnail_layout.setContentsMargins(4, 4, 4, 4)
        self.thumbnail_layout.setSpacing(4)
        self.thumbnail_layout.addStretch()

        self.thumbnail_scroll.setWidget(self.thumbnail_widget)
        layout.addWidget(self.thumbnail_scroll)

        # ===== 6. TOOLS PANEL =====
        tools_panel = QWidget()
        tools_panel.setObjectName("toolsPanel")
        tools_layout = QHBoxLayout(tools_panel)
        tools_layout.setContentsMargins(0, 0, 0, 0)
        tools_layout.setSpacing(0)

        # Brush size
        brush_widget = QWidget()
        brush_widget.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        brush_layout = QVBoxLayout(brush_widget)
        brush_layout.setContentsMargins(0, 0, 0, 0)
        brush_layout.setSpacing(4)

        brush_label = QLabel("Brush Size")
        brush_label.setObjectName("toolLabel")
        brush_layout.addWidget(brush_label)

        brush_row = QHBoxLayout()
        self.brush_slider = QSlider(Qt.Orientation.Horizontal)
        self.brush_slider.setRange(3, 200)
        self.brush_slider.setValue(45)
        self.brush_slider.setFixedWidth(200)
        self.brush_slider.valueChanged.connect(self._on_brush_slider_change)
        brush_row.addWidget(self.brush_slider)

        self.brush_spin = QSpinBox()
        self.brush_size_changed.connect(self._on_brush_spin_change)
        self.brush_spin.setRange(3, 200)
        self.brush_spin.setValue(45)
        self.brush_spin.setFixedWidth(48)
        self.brush_spin.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self.brush_spin.valueChanged.connect(self._on_brush_spin_change)
        brush_row.addWidget(self.brush_spin)
        brush_row.addStretch()

        brush_layout.addLayout(brush_row)
        tools_layout.addWidget(brush_widget)

        # Separator
        sep = QFrame()
        sep.setFixedWidth(2)
        sep.setStyleSheet("background-color: rgba(255,255,255,0.12);")
        tools_layout.addSpacing(40)
        tools_layout.addWidget(sep)
        tools_layout.addSpacing(40)

        # Zoom
        zoom_widget = QWidget()
        zoom_layout = QVBoxLayout(zoom_widget)
        zoom_layout.setContentsMargins(0, 0, 0, 0)
        zoom_layout.setSpacing(4)

        # Header row: label + percent
        zoom_header = QHBoxLayout()
        zoom_header.setSpacing(6)
        zoom_label = QLabel("Zoom")
        zoom_label.setObjectName("toolLabel")
        zoom_header.addWidget(zoom_label)

        self.zoom_percent_label = QLabel("100%")
        self.zoom_percent_label.setStyleSheet("color: #8B5CF6; font-size: 14px; font-weight: 600;")
        zoom_header.addWidget(self.zoom_percent_label)
        zoom_header.addStretch()
        zoom_layout.addLayout(zoom_header)

        zoom_row = QHBoxLayout()
        zoom_row.setSpacing(0)

        # Zoom buttons container with border
        zoom_container = QWidget()
        zoom_container.setObjectName("zoomContainer")
        zoom_container.setFixedSize(90, 36)
        zoom_container_layout = QHBoxLayout(zoom_container)
        zoom_container_layout.setContentsMargins(0, 0, 0, 0)
        zoom_container_layout.setSpacing(0)

        self.zoom_out_btn = QPushButton("−")
        self.zoom_out_btn.setObjectName("zoomButtonLeft")
        self.zoom_out_btn.setFixedSize(44, 36)
        self.zoom_out_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.zoom_out_btn.setToolTip("Zoom out")
        self.zoom_out_btn.clicked.connect(self._on_zoom_out)
        zoom_container_layout.addWidget(self.zoom_out_btn)

        # Vertical divider between buttons
        zoom_divider = QFrame()
        zoom_divider.setFixedWidth(1)
        zoom_divider.setFixedHeight(24)
        zoom_divider.setStyleSheet("background-color: rgba(255,255,255,0.12);")
        zoom_container_layout.addWidget(zoom_divider)

        self.zoom_in_btn = QPushButton("+")
        self.zoom_in_btn.setObjectName("zoomButtonRight")
        self.zoom_in_btn.setFixedSize(44, 36)
        self.zoom_in_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.zoom_in_btn.setToolTip("Zoom in")
        self.zoom_in_btn.clicked.connect(self._on_zoom_in)
        zoom_container_layout.addWidget(self.zoom_in_btn)

        zoom_row.addWidget(zoom_container)

        # Reset zoom button (cross) - appears only when zoomed
        self.zoom_reset_btn = QToolButton()
        self.zoom_reset_btn.setObjectName("iconButton")
        self.zoom_reset_btn.setFixedSize(36, 36)
        self.zoom_reset_btn.setIcon(create_icon_svg("x", "#9CA3AF", 18))
        self.zoom_reset_btn.setIconSize(QSize(18, 18))
        self.zoom_reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.zoom_reset_btn.setToolTip("Reset zoom (Fit to view)")
        self.zoom_reset_btn.clicked.connect(self._on_zoom_reset)
        self.zoom_reset_btn.setVisible(False)
        zoom_row.addWidget(self.zoom_reset_btn)
        zoom_row.addStretch()

        zoom_layout.addLayout(zoom_row)
        tools_layout.addWidget(zoom_widget)

        tools_layout.addStretch()

        # Clear mask button
        self.clear_btn = QPushButton("  Clear")
        self.clear_btn.setObjectName("clearButton")
        self.clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_btn.setIcon(create_icon_svg("x", "white", 18))
        self.clear_btn.setIconSize(QSize(18, 18))
        self.clear_btn.setFixedWidth(100)
        self.clear_btn.clicked.connect(self._on_clear_mask)
        tools_layout.addWidget(self.clear_btn)
        tools_layout.addSpacing(10)

        # Remove button
        self.remove_btn = QPushButton("  Remove")
        self.remove_btn.setObjectName("removeButton")
        self.remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.remove_btn.setIcon(create_icon_svg("trash", "white", 18))
        self.remove_btn.setIconSize(QSize(18, 18))
        self.remove_btn.setFixedWidth(200)
        self.remove_btn.clicked.connect(self._on_remove_click)
        tools_layout.addWidget(self.remove_btn)

        layout.addWidget(tools_panel)

    def _show_info_dialog(self):
        """Show info dialog with author credits and support info"""
        dialog = QDialog(self)
        dialog.setWindowTitle("About")
        dialog.setMinimumWidth(420)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #1E1E2E;
                border-radius: 16px;
            }
            QLabel {
                color: #FFFFFF;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QPushButton {
                background-color: #4F46E5;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 24px;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #5B54E8;
            }
        """)

        layout = QVBoxLayout(dialog)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # Title
        title = QLabel("Watermark Remover Portable")
        title_font = QFont("Segoe UI", 18, QFont.Weight.Bold)
        title.setFont(title_font)
        title.setStyleSheet("color: #8B5CF6;")
        layout.addWidget(title)

        # Authors section
        authors_title = QLabel("Authors")
        authors_font = QFont("Segoe UI", 14, QFont.Weight.Bold)
        authors_title.setFont(authors_font)
        authors_title.setStyleSheet("color: #FFFFFF; margin-top: 8px;")
        layout.addWidget(authors_title)

        # Author 1
        author1 = QLabel(
            '<b>NeiroVlad</b> — '
            '<a href="https://github.com/vlad-ir" style="color: #8B5CF6; text-decoration: none;">github.com/vlad-ir</a> — '
            'portable build author'
        )
        author1.setOpenExternalLinks(True)
        author1.setWordWrap(True)
        layout.addWidget(author1)

        # Author 2
        author2 = QLabel(
            '<b>oti.by</b> — '
            '<a href="https://t.me/vlad_vlk" style="color: #8B5CF6; text-decoration: none;">t.me/vlad_vlk</a> — '
            '<a href="https://oti.by" style="color: #8B5CF6; text-decoration: none;">oti.by</a> — '
            'neural networks and smart chatbots for business'
        )
        author2.setOpenExternalLinks(True)
        author2.setWordWrap(True)
        layout.addWidget(author2)

        # Author 3
        author3 = QLabel(
            '<b>AI in Business and Life</b> — '
            '<a href="https://t.me/neiro_com" style="color: #8B5CF6; text-decoration: none;">t.me/neiro_com</a> — '
            'prompts, examples, tips and more'
        )
        author3.setOpenExternalLinks(True)
        author3.setWordWrap(True)
        layout.addWidget(author3)

        # Separator line
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: rgba(255,255,255,0.12);")
        line.setFixedHeight(1)
        layout.addWidget(line)

        # Support section
        support_title = QLabel("Support the Author")
        support_title.setFont(authors_font)
        support_title.setStyleSheet("color: #FFFFFF;")
        layout.addWidget(support_title)

        support_text = QLabel(
            "If you found this project useful, please give it a ⭐ on GitHub!<br><br>"
            '<b>UnionPay Card:</b> <span style="color: #8B5CF6; font-family: monospace;">6229644000154242</span>'
        )
        support_text.setWordWrap(True)
        layout.addWidget(support_text)

        layout.addStretch()

        # OK button
        btn_ok = QPushButton("OK")
        btn_ok.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_ok.clicked.connect(dialog.accept)
        layout.addWidget(btn_ok, alignment=Qt.AlignmentFlag.AlignCenter)

        dialog.exec()

    def _check_model(self):
        """Check if big-lama.pt model file exists, show warning if not"""
        script_dir = Path(__file__).resolve().parent
        model_path = script_dir.parent / "models" / "big-lama.pt"
        if not model_path.exists():
            text = ("Expected model at:" + chr(10) + str(model_path) + chr(10) + chr(10)
                    + "Please download big-lama.pt and place it in the 'models' folder." + chr(10)
                    + "The app will run but inpainting will not work without the model.")
            msg = QMessageBox(self)
            msg.setWindowTitle("Model Not Found")
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setText("LaMa model not found!")
            msg.setInformativeText(text)
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg.exec()
            return False
        return True

    def _ensure_model_loaded(self):
        """Lazy-load model on first use (called when Remove is pressed)"""
        if self.model is not None:
            return True
        script_dir = Path(__file__).resolve().parent
        model_path = script_dir.parent / "models" / "big-lama.pt"
        if not model_path.exists():
            QMessageBox.warning(self, "No Model", "LaMa model not found. Please check the models folder.")
            return False
        try:
            self.model = load_model()
            print("[INFO] LaMa model loaded on", self.model["device"])
            return True
        except Exception as e:
            print("[WARN] Failed to load model:", e)
            QMessageBox.warning(self, "Model Load Error", str(e))
            return False

    def _load_model(self):
        """Load LaMa inpainting model"""
        try:
            self.model = load_model()
            print("[INFO] LaMa model loaded on", self.model["device"])
        except Exception as e:
            print("[WARN] Failed to load model:", e)
            QMessageBox.warning(self, "Model Load Error", str(e))

    def _apply_styles(self):
        self.setStyleSheet(DARK_STYLESHEET)

    # ===== ZOOM HANDLERS =====
    def _on_zoom_in(self):
        self.canvas.zoom_in()
        self._update_zoom_label()

    def _on_zoom_out(self):
        self.canvas.zoom_out()
        self._update_zoom_label()

    def _on_zoom_reset(self):
        self.canvas.reset_zoom()
        self._update_zoom_label()

    def _update_zoom_label(self):
        self.zoom_percent_label.setText(f"{self.canvas.zoom_percent:.0f}%")
        self.zoom_reset_btn.setVisible(not self.canvas.is_fit_to_view)

    # ===== BRUSH SIZE HANDLERS =====
    def _on_brush_slider_change(self, value):
        self.brush_spin.blockSignals(True)
        self.brush_spin.setValue(value)
        self.brush_spin.blockSignals(False)
        self.canvas.set_brush_size(value)

    def _on_brush_spin_change(self, value):
        self.brush_slider.blockSignals(True)
        self.brush_slider.setValue(value)
        self.brush_slider.blockSignals(False)
        self.brush_spin.blockSignals(True)
        self.brush_spin.setValue(value)
        self.brush_spin.blockSignals(False)
        self.canvas.set_brush_size(value)

    # ===== LOAD MEDIA =====
    def _on_load_click(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Media",
            self.last_directory,
            "Images/Videos (*.jpg *.jpeg *.png *.mp4 *.avi *.mov *.mkv)"
        )
        if not file_path:
            return

        self.last_directory = str(Path(file_path).parent)
        self.settings.setValue("last_directory", self.last_directory)

        ext = Path(file_path).suffix.lower()
        if ext in [".mp4", ".avi", ".mov", ".mkv"]:
            self._load_video(file_path)
        else:
            self._load_image(file_path)

    def _load_image(self, path):
        """Load image file"""
        try:
            self._last_image_path = path
            # Clear previous state
            self.canvas.clear_mask()
            self.is_video = False
            self.player_panel.setVisible(False)
            self.thumbnail_scroll.setVisible(False)

            # Load and save to assets
            pil = Image.open(path).convert("RGB")
            img_w, img_h = pil.size
            self.counter += 1

            save_path = self.assets_dir / f"img_{self.counter:04d}.png"
            pil.save(save_path, "PNG")

            # Display
            pixmap = QPixmap(str(save_path))
            self.canvas.load_image(pixmap)

            # Show image info
            file_size = Path(path).stat().st_size
            size_str = self._format_file_size(file_size)
            self.image_info_label.setText(f"{img_w} × {img_h} px  •  {size_str}")
            self.image_info_panel.setVisible(True)

        except Exception as e:
            QMessageBox.critical(self, "Error", "Failed to load image:" + chr(10) + str(path) + chr(10) + chr(10) + str(e))

    def _load_video(self, path):
        """Load video file"""
        try:
            self._last_video_path = path
            if self.cap:
                self.cap.release()

            self.cap = cv2.VideoCapture(path)
            if not self.cap.isOpened():
                QMessageBox.critical(self, "Error", f"Cannot open video: {path}")
                return

            self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.fps = self.cap.get(cv2.CAP_PROP_FPS)
            w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            self.current_frame = 0
            self.is_video = True
            self.canvas.frame_masks = {}
            self.frames_extracted = False
            self.extracted_count = 0

            self.video_info_label.setText(f"{w}×{h}×{self.fps:.0f}fps")
            self.image_info_panel.setVisible(False)

            # Clear old frames
            for f in self.assets_dir.glob("frame_*.jpg"):
                f.unlink()

            # Show loading dialog
            self.progress = QProgressDialog("Extracting video frames...", "Cancel", 0, self.total_frames, self)
            self.progress.setWindowTitle("Loading Video...")
            self.progress.setWindowModality(Qt.WindowModality.WindowModal)
            self.progress.setStyleSheet(DARK_STYLESHEET)
            self.progress.setMinimumDuration(0)
            self.progress.setMinimumWidth(320)
            self.progress.setMaximumWidth(320)
            self.progress.canceled.connect(self._cancel_extraction)

            # Start extraction thread
            self.extractor = FrameExtractor(path, str(self.assets_dir), self.total_frames)
            self.extractor.progress.connect(self._update_progress)
            self.extractor.finished_extract.connect(self._finish_extraction)
            self.extractor.start()

        except Exception as e:
            QMessageBox.critical(self, "Error", "Failed to load video:" + chr(10) + str(path) + chr(10) + chr(10) + str(e))


    def _update_progress(self, current, total):
        self.progress.setValue(current)
        self.progress.setLabelText(f"Extracting: {current}/{total} frames")

    def _cancel_extraction(self):
        if self.extractor:
            self.extractor.cancel()
            self.extractor.wait()
        self.progress.close()

    def _finish_extraction(self, count):
        self.progress.close()
        self.extracted_count = count
        self.frames_extracted = True

        self.timeline.setRange(0, max(0, count - 1))
        self.timeline.setValue(0)
        self.player_panel.setVisible(True)

        self.canvas.set_current_frame(0)
        self._show_frame(0)
        self._update_labels()
        self._generate_thumbnails()

    # ===== VIDEO PLAYBACK =====
    def _show_frame(self, idx):
        if not self.frames_extracted:
            return
        idx = max(0, min(idx, self.extracted_count - 1))

        frame_path = self.assets_dir / f"frame_{idx:06d}.jpg"
        if frame_path.exists():
            pixmap = QPixmap(str(frame_path))
            self.canvas.load_frame(pixmap, idx)
            self.current_frame = idx
            self.timeline.setValue(idx)
            self._update_labels()

    def _show_frame_fast(self, idx):
        """Show frame without updating labels (for slider drag)"""
        if not self.frames_extracted:
            return
        idx = max(0, min(idx, self.extracted_count - 1))

        frame_path = self.assets_dir / f"frame_{idx:06d}.jpg"
        if frame_path.exists():
            pixmap = QPixmap(str(frame_path))
            self.canvas.load_frame(pixmap, idx)
            self.current_frame = idx
            self._update_labels()

    def _update_labels(self):
        current_sec = self.current_frame / max(1, self.fps)
        total_sec = self.total_frames / max(1, self.fps)
        self.time_label.setText(f"{self._format_time(current_sec)} / {self._format_time(total_sec)}")
        self.frame_label.setText(f"Frame: {self.current_frame} / {self.total_frames}")

    def _format_time(self, seconds):
        seconds = int(seconds)
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        return f"{h:02d}:{m:02d}:{s:02d}"

    def _format_file_size(self, size_bytes):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"

    def _on_timeline_change(self, value):
        self._stop_playback()
        self._show_frame_fast(value)

    def _on_prev_frame(self):
        self._stop_playback()
        self._show_frame(self.current_frame - 1)

    def _on_next_frame(self):
        self._stop_playback()
        self._show_frame(self.current_frame + 1)

    def _on_play_click(self):
        if not self.is_video or not self.frames_extracted:
            return
        if self.is_playing:
            self._stop_playback()
        else:
            self._start_playback()

    def _on_remove_click(self):
        """Process image or video with inpainting"""
        try:
            print("[DEBUG] Step 1: Checking model...")
            if not self._ensure_model_loaded():
                print("[DEBUG] Model not loaded, returning")
                return
            print("[DEBUG] Step 2: Model OK, checking media type...")
            if self.is_video and self.frames_extracted:
                print("[DEBUG] Step 3: Processing video...")
                self._process_video()
            elif not self.is_video and hasattr(self, '_last_image_path'):
                print("[DEBUG] Step 3: Processing image...")
                self._process_image()
            else:
                print("[DEBUG] No media loaded")
                QMessageBox.information(self, "Nothing to Remove", "Please load media and draw a mask first.")
        except Exception as e:
            print("[ERROR] Remove failed:", e)
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", "Remove failed:" + chr(10) + str(e))

    def _process_image(self):
        """Process single image with inpainting"""
        input_path = Path(self._last_image_path)
        default_name = input_path.parent / (input_path.stem + "_inpainted.png")
        output_path, _ = QFileDialog.getSaveFileName(
            self, "Save Inpainted Image",
            str(Path(self.last_directory) / default_name.name),
            "Images (*.png *.jpg *.jpeg)"
        )
        if not output_path:
            return

        self.last_directory = str(Path(output_path).parent)
        self.settings.setValue("last_directory", self.last_directory)

        mask = self.canvas.get_mask()
        if mask is None or not np.any(mask > 0):
            QMessageBox.information(self, "No Mask", "Please draw a mask first.")
            return

        progress = QProgressDialog("Processing image...", None, 0, 0, self)
        progress.setWindowTitle("Inpainting Image")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setMinimumWidth(300)
        progress.setCancelButton(None)
        progress.show()
        QApplication.processEvents()

        try:
            # Читаем через PIL — поддержка UTF-8 путей (кириллица, пробелы)
            pil_img = Image.open(str(input_path)).convert("RGB")
            img_rgb = np.array(pil_img)
            result = inpaint_img_with_lama(img_rgb, mask, self.model)

            # Сохраняем через PIL — cv2.imwrite не умеет UTF-8 пути на Windows
            result_pil = Image.fromarray(result)
            result_pil.save(output_path)

            progress.close()
            QMessageBox.information(self, "Success", "Image saved to:" + chr(10) + output_path)
        except Exception as e:
            progress.close()
            QMessageBox.critical(self, "Error", "Inpainting failed:" + chr(10) + str(e))

    def _process_video(self):
        """Process video frame by frame with per-frame masks"""
        input_path = Path(self._last_video_path)
        default_name = input_path.parent / (input_path.stem + "_inpainted" + input_path.suffix)
        output_path, _ = QFileDialog.getSaveFileName(
            self, "Save Inpainted Video",
            str(Path(self.last_directory) / default_name.name),
            "Videos (*.mp4 *.avi *.mov *.mkv)"
        )
        if not output_path:
            return

        self.last_directory = str(Path(output_path).parent)
        self.settings.setValue("last_directory", self.last_directory)

        if not self.canvas.frame_masks:
            QMessageBox.information(self, "No Masks", "Please draw masks on at least one frame.")
            return

        progress = QProgressDialog("Processing video...", "Cancel", 0, self.extracted_count, self)
        progress.setWindowTitle("Inpainting Video")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setMinimumWidth(400)

        temp_dir = Path(tempfile.mkdtemp())
        try:
            for i in range(self.extracted_count):
                progress.setValue(i)
                progress.setLabelText("Processing frame " + str(i+1) + "/" + str(self.extracted_count) + "...")
                if progress.wasCanceled():
                    break
                frame_path = self.assets_dir / ("frame_%06d.jpg" % i)
                frame = cv2.imread(str(frame_path))
                if frame is None:
                    continue
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w = frame.shape[:2]
                mask = self.canvas._get_mask_for_frame(i, h, w)
                if np.any(mask > 0):
                    result = inpaint_img_with_lama(frame_rgb, mask, self.model)
                else:
                    result = frame_rgb
                out_path = temp_dir / ("frame_%06d.png" % i)
                cv2.imwrite(str(out_path), cv2.cvtColor(result, cv2.COLOR_RGB2BGR))
            progress.setValue(self.extracted_count)

            # Assemble video with original audio and parameters
            self._assemble_video(input_path, temp_dir, output_path)
            QMessageBox.information(self, "Success", "Video saved to:" + chr(10) + output_path)
        except Exception as e:
            QMessageBox.critical(self, "Error", "Video processing failed:" + chr(10) + str(e))
        finally:
            import shutil
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
            progress.close()

    def _assemble_video(self, original_path, temp_dir, output_path):
        """Assemble processed frames into video, preserving original audio and params"""
        # Find ffmpeg
        ffmpeg_cmd = None
        try:
            subprocess.run(['ffmpeg', '-version'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            ffmpeg_cmd = 'ffmpeg'
        except (subprocess.CalledProcessError, FileNotFoundError):
            script_dir = Path(__file__).parent
            for candidate in [
                script_dir / 'ffmpeg' / 'bin' / 'ffmpeg.exe',
                script_dir / 'ffmpeg.exe',
                script_dir.parent / 'ffmpeg' / 'bin' / 'ffmpeg.exe',
                script_dir.parent / 'ffmpeg.exe',
            ]:
                if candidate.exists():
                    ffmpeg_cmd = str(candidate)
                    break
        if ffmpeg_cmd is None:
            raise RuntimeError("ffmpeg not found. Please install ffmpeg.")

        fps = self.fps if self.fps else 30
        pattern = str(temp_dir / "frame_%06d.png")

        # Build ffmpeg command: re-encode video from frames, copy audio from original
        cmd = [
            ffmpeg_cmd, '-y',
            '-framerate', str(fps),
            '-i', pattern,
            '-i', str(original_path),
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-crf', '18',
            '-pix_fmt', 'yuv420p',
            '-c:a', 'copy',
            '-map', '0:v:0',
            '-map', '1:a:0?',
            '-shortest',
            output_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
        if result.returncode != 0:
            raise RuntimeError("ffmpeg failed: " + (result.stderr or ""))

    def _on_clear_mask(self):
        """Clear mask on current frame (subsequent frames will inherit empty mask)"""
        self.canvas.clear_mask()

    def _on_undo(self):
        """Undo last brush stroke"""
        self.canvas.undo()

    def _on_redo(self):
        """Redo last undone brush stroke"""
        self.canvas.redo()

    def _start_playback(self):
        self.is_playing = True
        self.play_btn.setIcon(create_icon_svg("pause", "white", 24))
        self.play_btn.setIconSize(QSize(24, 24))
        frame_ms = int(1000 / max(1, self.fps))
        self.play_timer.start(frame_ms)

    def _stop_playback(self):
        self.is_playing = False
        self.play_btn.setIcon(create_icon_svg("play", "white", 24))
        self.play_btn.setIconSize(QSize(24, 24))
        self.play_timer.stop()

    def _next_frame(self):
        next_idx = self.current_frame + 1
        if next_idx >= self.extracted_count:
            self._stop_playback()
            return
        self._show_frame(next_idx)

    # ===== THUMBNAILS =====
    def _generate_thumbnails(self):
        if not self.cap or self.total_frames == 0:
            return

        # Clear old thumbnails
        while self.thumbnail_layout.count() > 1:  # keep stretch
            item = self.thumbnail_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        step = max(1, self.total_frames // 20)
        thumb_w, thumb_h = 40, 53

        for i in range(0, self.total_frames, step):
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, i)
            ret, frame = self.cap.read()
            if not ret:
                continue

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = frame_rgb.shape
            bytes_per_line = ch * w
            qt_image = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(qt_image).scaled(thumb_w, thumb_h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)

            btn = QPushButton()
            btn.setObjectName("thumbButton")
            btn.setFixedSize(thumb_w, thumb_h)
            btn.setIcon(QIcon(pixmap))
            btn.setIconSize(QSize(thumb_w, thumb_h))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, idx=i: self._on_thumbnail_click(idx))

            self.thumbnail_layout.insertWidget(self.thumbnail_layout.count() - 1, btn)

        self.thumbnail_scroll.setVisible(True)

    def _on_thumbnail_click(self, frame_idx):
        self._stop_playback()
        self._show_frame(frame_idx)

    def eventFilter(self, obj, event):
        """Global event filter for keyboard navigation — works regardless of focus"""
        if event.type() == event.Type.KeyPress:
            if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                if event.key() == Qt.Key.Key_Z:
                    self._on_undo()
                    return True
            elif event.modifiers() == (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier):
                if event.key() == Qt.Key.Key_Z:
                    self._on_redo()
                    return True
            elif event.key() == Qt.Key.Key_Left:
                self._on_prev_frame()
                return True
            elif event.key() == Qt.Key.Key_Right:
                self._on_next_frame()
                return True
            elif event.key() == Qt.Key.Key_Space:
                if self.is_video and self.frames_extracted:
                    self._on_play_click()
                    return True
        return super().eventFilter(obj, event)

    def closeEvent(self, event):
        if self.extractor and self.extractor.isRunning():
            self.extractor.cancel()
            self.extractor.wait()
        if self.cap:
            self.cap.release()
        event.accept()


# =============================================================================
# MAIN ENTRY
# =============================================================================
def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Dark palette
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#1A1A1A"))
    palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Base, QColor("#2D2D2D"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#1A1A1A"))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#1A1A1A"))
    palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Button, QColor("#2D2D2D"))
    palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#8B5CF6"))
    palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.white)
    app.setPalette(palette)

    window = WatermarkRemoverWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()