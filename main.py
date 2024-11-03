# main.py
import sys
import cv2
import numpy as np
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget,
    QPushButton, QHBoxLayout, QFileDialog, QSlider, QGroupBox, QMessageBox
)
from PyQt5.QtGui import QPixmap, QImage, QPainter, QColor, QPen
from PyQt5.QtCore import Qt, QPoint

from seam_carving import SeamCarver
from Sketcher import Sketcher  # Ensure this is compatible or refactor as needed

class ImageLabel(QLabel):
    def __init__(self):
        super().__init__()
        self.setAlignment(Qt.AlignCenter)
        self.setAcceptDrops(False)  # Drag-and-drop is handled by the main window
        self.pixmap = None
        self.drawing = False
        self.last_point = QPoint()
        self.mask = None  # Mask image as a NumPy array
        self.brush_size = 10
        self.brush_color = (255, 255, 255)  # White for protection/removal

    def set_image(self, img):
        """Set the image to display and initialize mask."""
        self.original_img = img.copy()
        self.display_img = img.copy()
        height, width, channel = img.shape
        bytes_per_line = 3 * width
        q_img = QImage(img.data, width, height, bytes_per_line, QImage.Format_RGB888).rgbSwapped()
        self.pixmap = QPixmap.fromImage(q_img)
        self.setPixmap(self.pixmap)
        # Initialize mask
        self.mask = np.zeros((height, width), dtype=np.uint8)

    def mousePressEvent(self, event):
        if self.pixmap is not None:
            if event.button() == Qt.LeftButton:
                self.drawing = True
                self.last_point = event.pos()

    def mouseMoveEvent(self, event):
        if self.drawing and self.pixmap is not None:
            painter = QPainter(self.pixmap)
            pen = QPen()
            pen.setWidth(self.brush_size)
            pen.setColor(QColor(*self.brush_color))
            pen.setCapStyle(Qt.RoundCap)
            painter.setPen(pen)
            painter.drawLine(self.last_point, event.pos())
            self.last_point = event.pos()
            self.setPixmap(self.pixmap)
            painter.end()

            # Update the mask
            x1, y1 = self.mapToImageCoordinates(self.last_point)
            x2, y2 = self.mapToImageCoordinates(event.pos())
            cv2.line(self.mask, (x1, y1), (x2, y2), 255, self.brush_size)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drawing = False

    def mapToImageCoordinates(self, point):
        """Map widget coordinates to image coordinates."""
        pixmap_width = self.pixmap.width()
        pixmap_height = self.pixmap.height()
        label_width = self.width()
        label_height = self.height()

        scale_x = self.original_img.shape[1] / pixmap_width
        scale_y = self.original_img.shape[0] / pixmap_height

        x = int(point.x() * scale_x)
        y = int(point.y() * scale_y)
        x = np.clip(x, 0, self.original_img.shape[1]-1)
        y = np.clip(y, 0, self.original_img.shape[0]-1)
        return x, y

    def reset(self):
        """Reset the image and mask."""
        if hasattr(self, 'original_img'):
            self.set_image(self.original_img)

class SeamCarvingApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Seam Carving Application")
        self.setGeometry(100, 100, 1200, 800)
        self.image_label = ImageLabel()

        # Initialize mask mode
        self.mode = 'remove'  # or 'protect'

        # Layouts
        main_layout = QHBoxLayout()
        image_layout = QVBoxLayout()
        control_layout = QVBoxLayout()

        # Image display
        image_layout.addWidget(self.image_label)

        # Controls
        # Mode selection
        mode_group = QGroupBox("Mode")
        mode_layout = QHBoxLayout()
        self.remove_button = QPushButton("Remove")
        self.remove_button.setCheckable(True)
        self.remove_button.setChecked(True)
        self.remove_button.clicked.connect(self.set_remove_mode)
        self.protect_button = QPushButton("Protect")
        self.protect_button.setCheckable(True)
        self.protect_button.clicked.connect(self.set_protect_mode)
        mode_layout.addWidget(self.remove_button)
        mode_layout.addWidget(self.protect_button)
        mode_group.setLayout(mode_layout)
        control_layout.addWidget(mode_group)

        # Brush size slider
        brush_group = QGroupBox("Brush Size")
        brush_layout = QHBoxLayout()
        self.brush_slider = QSlider(Qt.Horizontal)
        self.brush_slider.setMinimum(1)
        self.brush_slider.setMaximum(50)
        self.brush_slider.setValue(10)
        self.brush_slider.valueChanged.connect(self.change_brush_size)
        brush_layout.addWidget(self.brush_slider)
        brush_group.setLayout(brush_layout)
        control_layout.addWidget(brush_group)

        # Width slider
        width_group = QGroupBox("Width")
        width_layout = QHBoxLayout()
        self.width_slider = QSlider(Qt.Horizontal)
        self.width_slider.setMinimum(1)
        self.width_slider.setMaximum(2000)  # Adjust as needed
        self.width_slider.setValue(0)  # 0 will indicate no change
        width_layout.addWidget(self.width_slider)
        width_group.setLayout(width_layout)
        control_layout.addWidget(width_group)

        # Height slider
        height_group = QGroupBox("Height")
        height_layout = QHBoxLayout()
        self.height_slider = QSlider(Qt.Horizontal)
        self.height_slider.setMinimum(1)
        self.height_slider.setMaximum(2000)  # Adjust as needed
        self.height_slider.setValue(0)  # 0 will indicate no change
        height_layout.addWidget(self.height_slider)
        height_group.setLayout(height_layout)
        control_layout.addWidget(height_group)

        # Buttons
        self.load_button = QPushButton("Load Image")
        self.load_button.clicked.connect(self.load_image)
        self.save_button = QPushButton("Save Result")
        self.save_button.clicked.connect(self.save_result)
        self.process_button = QPushButton("Start Seam Carving")
        self.process_button.clicked.connect(self.start_seam_carving)
        control_layout.addWidget(self.load_button)
        control_layout.addWidget(self.process_button)
        control_layout.addWidget(self.save_button)

        # Spacer
        control_layout.addStretch()

        main_layout.addLayout(image_layout, 3)
        main_layout.addLayout(control_layout, 1)

        # Central widget
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

    def set_remove_mode(self):
        if self.remove_button.isChecked():
            self.mode = 'remove'
            self.protect_button.setChecked(False)
            self.image_label.brush_color = (255, 255, 255)  # White for removal
        else:
            self.mode = None

    def set_protect_mode(self):
        if self.protect_button.isChecked():
            self.mode = 'protect'
            self.remove_button.setChecked(False)
            self.image_label.brush_color = (0, 0, 255)  # Red for protection
        else:
            self.mode = None

    def change_brush_size(self, value):
        self.image_label.brush_size = value

    def load_image(self):
        """Load an image using file dialog."""
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Image", "",
                                                   "Image Files (*.png *.jpg *.jpeg *.bmp);;All Files (*)",
                                                   options=options)
        if file_path:
            img = cv2.imread(file_path, cv2.IMREAD_COLOR)
            if img is None:
                QMessageBox.critical(self, "Error", "Failed to load image.")
                return
            self.image_label.set_image(img)
            # Reset mask
            self.image_label.mask = np.zeros(img.shape[:2], dtype=np.uint8)
            # Set initial slider positions
            self.width_slider.setValue(0)
            self.height_slider.setValue(0)

    def save_result(self):
        """Save the resulting image."""
        if hasattr(self, 'result_image'):
            options = QFileDialog.Options()
            file_path, _ = QFileDialog.getSaveFileName(self, "Save Image", "",
                                                       "PNG Files (*.png);;JPEG Files (*.jpg *.jpeg);;All Files (*)",
                                                       options=options)
            if file_path:
                cv2.imwrite(file_path, self.result_image)
                QMessageBox.information(self, "Saved", f"Image saved to {file_path}.")
        else:
            QMessageBox.warning(self, "Warning", "No result image to save.")

    def start_seam_carving(self):
        """Initiate the seam carving process."""
        if not hasattr(self.image_label, 'original_img'):
            QMessageBox.warning(self, "Warning", "No image loaded.")
            return

        img = self.image_label.original_img.copy()
        mask = self.image_label.mask.copy()

        # Get desired dimensions
        new_width = self.width_slider.value()
        new_height = self.height_slider.value()
        if new_width == 0:
            new_width = img.shape[1]
        if new_height == 0:
            new_height = img.shape[0]

        # Depending on mode, set masks appropriately
        if self.mode == 'remove':
            object_mask = mask
            protect_mask = []
        elif self.mode == 'protect':
            object_mask = []
            protect_mask = mask
        else:
            object_mask = []
            protect_mask = []

        # Define a callback function to update the image with seams
        def seam_callback(current_image, seam_idx):
            # Draw the seam on the image
            seam_image = current_image.astype(np.uint8).copy()
            for row, col in enumerate(seam_idx):
                cv2.circle(seam_image, (col, row), 1, (0, 0, 255), -1)  # Red color for seam
            # Convert to QImage and display
            height, width, channel = seam_image.shape
            bytes_per_line = 3 * width
            q_img = QImage(seam_image.data, width, height, bytes_per_line, QImage.Format_RGB888).rgbSwapped()
            pixmap = QPixmap.fromImage(q_img)
            self.image_label.setPixmap(pixmap)
            QApplication.processEvents()  # Update the GUI

        # Instantiate SeamCarver
        try:
            carver = SeamCarver(
                in_image=img,
                out_height=new_height,
                out_width=new_width,
                protect_mask=protect_mask,
                object_mask=object_mask,
                seam_callback=seam_callback
            )
            # After processing, retrieve the result
            self.result_image = carver.out_image.astype(np.uint8)
            # Display the result
            height, width, channel = self.result_image.shape
            bytes_per_line = 3 * width
            q_img = QImage(self.result_image.data, width, height, bytes_per_line, QImage.Format_RGB888).rgbSwapped()
            pixmap = QPixmap.fromImage(q_img)
            self.image_label.setPixmap(pixmap)
            QMessageBox.information(self, "Success", "Seam carving completed.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred during seam carving:\n{str(e)}")

def main():
    app = QApplication(sys.argv)
    window = SeamCarvingApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
