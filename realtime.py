# realtime.py
import cv2
import numpy as np
from seam_carving import SeamCarver
from Sketcher import Sketcher
import os, sys

MODE = 'remove'  # 'remove', 'protect'
img_path = sys.argv[1]

def nothing(x):
    pass

# Initialize images and mask
img = cv2.imread(img_path, cv2.IMREAD_COLOR)
if img is None:
    print("Error: Image not found or unable to read.")
    sys.exit(1)
img_masked = img.copy()
mask = np.zeros(img.shape[:2], np.uint8)

# Initialize Sketcher
sketcher = Sketcher('image', [img_masked, mask], lambda: ((255, 255, 255), 255))

# Create Trackbars
cv2.namedWindow('image')
cv2.createTrackbar('width', 'image', img.shape[1], img.shape[1]*2, nothing)
cv2.createTrackbar('height', 'image', img.shape[0], img.shape[0]*2, nothing)

# Callback function to visualize seams
def seam_callback(current_image, seam_idx):
    # Create a copy to draw the seam
    seam_image = current_image.astype(np.uint8).copy()
    for row, col in enumerate(seam_idx):
        cv2.circle(seam_image, (col, row), 1, (0, 0, 255), -1)  # Red color for seam
    # Show the seam on a separate window or overlay on the original image
    cv2.imshow('Seam', seam_image)
    cv2.waitKey(1)  # Small delay to allow GUI to update

while True:
    key = cv2.waitKey(1) & 0xFF

    if key == ord('q'):  # quit
        break
    if key == ord('r'):  # reset
        print('reset')
        img_masked[:] = img
        mask[:] = 0
        sketcher.show()
        cv2.destroyWindow('Seam')
    if key == 32:  # hit spacebar
        new_width = int(cv2.getTrackbarPos('width', 'image'))
        new_height = int(cv2.getTrackbarPos('height', 'image'))

        if np.sum(mask) > 0:  # object removal or protect mask
            if MODE == 'remove':
                carver = SeamCarver(img, 0, 0, object_mask=mask, seam_callback=seam_callback)
            elif MODE == 'protect':
                carver = SeamCarver(img, new_height, new_width, protect_mask=mask, seam_callback=seam_callback)
            else:
                carver = SeamCarver(img, new_height, new_width, seam_callback=seam_callback)
        else:
            carver = SeamCarver(img, new_height, new_width, seam_callback=seam_callback)

        # Display the resized image
        resized_img = cv2.resize(carver.out_image.astype(np.uint8), dsize=(new_width, new_height))
        cv2.imshow('resize', resized_img)
        cv2.imshow('input', carver.in_image.astype(np.uint8))
        cv2.imshow('output', carver.out_image.astype(np.uint8))
        print('Seam carving completed.')

# Cleanup
cv2.destroyAllWindows()
