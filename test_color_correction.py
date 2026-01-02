#!/usr/bin/env python3
"""Test color correction functionality."""

import sys
import os
from PIL import Image, ImageDraw, ImageFont

def create_test_image(output_path):
    """Create a test image with red, green, and blue blocks."""
    # Create a 600x200 image
    img = Image.new('RGB', (600, 200), 'white')
    draw = ImageDraw.Draw(img)
    
    # Draw colored rectangles
    # Red block
    draw.rectangle([0, 0, 199, 199], fill=(255, 0, 0))
    draw.text((70, 90), "RED", fill=(255, 255, 255))
    
    # Green block
    draw.rectangle([200, 0, 399, 199], fill=(0, 255, 0))
    draw.text((260, 90), "GREEN", fill=(0, 0, 0))
    
    # Blue block
    draw.rectangle([400, 0, 599, 199], fill=(0, 0, 255))
    draw.text((460, 90), "BLUE", fill=(255, 255, 255))
    
    img.save(output_path)
    print(f"Created test image: {output_path}")
    return output_path

def apply_swap_rb(input_path, output_path):
    """Apply red-blue channel swap."""
    img = Image.open(input_path)
    r, g, b = img.split()
    corrected = Image.merge('RGB', (b, g, r))
    corrected.save(output_path)
    print(f"Applied swap_rb correction: {output_path}")
    return output_path

def main():
    """Test color correction."""
    print("Color Correction Test")
    print("=" * 50)
    
    # Create test directory
    test_dir = "/tmp/color_test"
    os.makedirs(test_dir, exist_ok=True)
    
    # Create original test image
    original = os.path.join(test_dir, "original.png")
    create_test_image(original)
    
    # Apply correction
    corrected = os.path.join(test_dir, "corrected.png")
    apply_swap_rb(original, corrected)
    
    print("\nTest complete!")
    print(f"Original image: {original}")
    print(f"Corrected image: {corrected}")
    print("\nTo view the images, transfer them to your local machine:")
    print(f"  scp user@pi:{original} .")
    print(f"  scp user@pi:{corrected} .")
    print("\nThe original should show RED, GREEN, BLUE in order.")
    print("The corrected should show BLUE, GREEN, RED in order (R and B swapped).")

if __name__ == '__main__':
    main()
