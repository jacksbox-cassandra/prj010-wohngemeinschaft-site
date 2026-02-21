#!/usr/bin/env python3
from PIL import Image, ImageDraw, ImageFont
import os

def create_placeholder(text, save_path, width=400, height=300):
    """Create a placeholder image with text"""
    # Create image with light gray background
    img = Image.new('RGB', (width, height), (240, 240, 240))
    draw = ImageDraw.Draw(img)
    
    # Try to use a simple font, fallback to default
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 20)
    except:
        font = ImageFont.load_default()
    
    # Calculate text size and position for centering
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (width - text_width) // 2
    y = (height - text_height) // 2
    
    # Draw text in dark gray
    draw.text((x, y), text, fill=(100, 100, 100), font=font)
    
    # Save as JPEG
    img.save(save_path, 'JPEG', quality=85)
    print(f"✓ Created placeholder: {save_path}")

def main():
    photos_dir = '/Users/jacksbot/projects/PRJ010-wohngemeinschaft/docs/assets/leipzig/photos'
    
    # Failed candidates that need placeholders
    failed_candidates = ['LE001', 'LE002', 'LE003', 'LE004', 'LE005', 'LE007', 'LE008']
    
    for candidate_id in failed_candidates:
        placeholder_path = os.path.join(photos_dir, f"{candidate_id}.jpg")
        if not os.path.exists(placeholder_path):
            create_placeholder(f"Image not\navailable\n({candidate_id})", placeholder_path)

if __name__ == "__main__":
    main()