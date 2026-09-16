"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  CipherVault — Image Handler                                               ║
║  Image processing, preview generation, and encryption/decryption wrapper   ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO


def generate_thumbnail(image_path: str, max_size: tuple = (400, 400)) -> Image.Image:
    """
    Generate a thumbnail preview of an image for UI display.
    
    Uses PIL's LANCZOS resampling for high-quality downscaling.
    Maintains aspect ratio within max_size bounds.
    
    Args:
        image_path: Path to the image file
        max_size: Maximum (width, height) for the thumbnail
    
    Returns:
        PIL Image object suitable for display
    """
    try:
        img = Image.open(image_path)
        img.thumbnail(max_size, Image.LANCZOS)
        return img
    except Exception as e:
        raise ValueError(f"Cannot generate preview: {str(e)}")


def get_image_info(image_path: str) -> dict:
    """
    Extract metadata about an image file.
    
    Returns:
        dict with format, mode, dimensions, pixel count, file size
    """
    try:
        img = Image.open(image_path)
        file_size = os.path.getsize(image_path)
        
        return {
            'format': img.format or 'Unknown',
            'mode': img.mode,
            'width': img.size[0],
            'height': img.size[1],
            'pixels': img.size[0] * img.size[1],
            'size_bytes': file_size,
            'size_kb': f"{file_size / 1024:.1f}",
            'size_mb': f"{file_size / (1024 * 1024):.2f}",
            'filename': os.path.basename(image_path),
        }
    except Exception as e:
        raise ValueError(f"Cannot read image info: {str(e)}")


def create_placeholder_image(
    width: int = 400,
    height: int = 300,
    text: str = "No Image Selected",
    bg_color: str = "#1a1a2e",
    text_color: str = "#64748b",
) -> Image.Image:
    """
    Create a placeholder image for empty preview areas.
    
    Uses PIL ImageDraw for text rendering on a solid background.
    """
    img = Image.new('RGB', (width, height), color=bg_color)
    draw = ImageDraw.Draw(img)
    
    # Try to use a clean font, fallback to default
    try:
        font = ImageFont.truetype("segoeui.ttf", 16)
    except (OSError, IOError):
        try:
            font = ImageFont.truetype("arial.ttf", 16)
        except (OSError, IOError):
            font = ImageFont.load_default()

    # Center the text
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (width - text_width) // 2
    y = (height - text_height) // 2
    
    draw.text((x, y), text, fill=text_color, font=font)
    
    return img


def is_valid_image(file_path: str) -> bool:
    """Check if a file is a valid, openable image."""
    try:
        with Image.open(file_path) as img:
            img.verify()
        return True
    except Exception:
        return False


SUPPORTED_FORMATS = {
    '.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.tif', '.webp'
}


def get_supported_extensions() -> str:
    """Get file dialog filter string for supported image formats."""
    return " ".join(f"*{ext}" for ext in sorted(SUPPORTED_FORMATS))
