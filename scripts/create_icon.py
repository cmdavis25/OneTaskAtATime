"""
Create a simple placeholder icon for OneTaskAtATime application.

This script generates a minimal icon file using PIL/Pillow with a green background
and white "1" character, representing the app's focus on one task at a time.
"""

from PIL import Image, ImageDraw, ImageFont
import os


def create_icon():
    """Generate application icon with multiple resolutions."""
    # Create 256x256 base image
    img = Image.new('RGBA', (256, 256), (76, 175, 80, 255))  # Green background
    draw = ImageDraw.Draw(img)

    try:
        # Try to load Arial font for better appearance
        font = ImageFont.truetype("arial.ttf", 150)
    except OSError:
        # Fallback to default font if Arial not available
        print("Warning: Arial font not found, using default font")
        font = ImageFont.load_default()

    # Draw white "1" in center
    # Calculate text position for centering
    bbox = draw.textbbox((0, 0), "1", font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (256 - text_width) // 2
    y = (256 - text_height) // 2 - 10  # Slight adjustment for visual centering

    draw.text((x, y), "1", fill='white', font=font)

    # Save as .ico with multiple sizes
    output_path = os.path.abspath(os.path.join(
        os.path.dirname(__file__), '..', 'resources', 'icon.ico'
    ))

    # Create resources directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Save with multiple icon sizes
    img.save(output_path, format='ICO', sizes=[(16, 16), (32, 32), (48, 48), (256, 256)])

    print(f"✓ Icon created successfully: {output_path}")
    print(f"  Sizes: 16x16, 32x32, 48x48, 256x256")


if __name__ == '__main__':
    create_icon()
