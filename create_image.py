from PIL import Image, ImageDraw, ImageFont
import os

# Create a proper refrigeration cycle diagram
width, height = 1200, 600
img = Image.new('RGB', (width, height), color=(26, 115, 232))  # Blue

# Create drawing context
draw = ImageDraw.Draw(img)

# Add decorative elements
draw.rectangle([(50, 50), (1150, 550)], outline=(255, 255, 255), width=3)

# Add text
try:
    font_large = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", 48)
    font_small = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", 24)
except:
    font_large = ImageFont.load_default()
    font_small = ImageFont.load_default()

# Add title
draw.text((100, 80), "Industrial Refrigeration Systems", fill=(255, 255, 255), font=font_large)

# Draw refrigeration cycle components boxes
components = [
    ("Compressor", 100, 200, 200),
    ("Condenser", 360, 200, 200),
    ("Expansion\nValve", 620, 200, 200),
    ("Evaporator", 880, 200, 200)
]

for comp_name, x, y, width_box in components:
    # Draw white box
    draw.rectangle([x, y, x+width_box, y+120], fill=(255, 255, 255), outline=(0, 0, 0), width=2)
    # Draw text
    draw.text((x+15, y+40), comp_name, fill=(26, 115, 232), font=font_small)

# Draw flow arrows between components
arrow_y = 260
draw.line([(300, arrow_y), (360, arrow_y)], fill=(255, 215, 0), width=4)
draw.line([(560, arrow_y), (620, arrow_y)], fill=(255, 215, 0), width=4)
draw.line([(820, arrow_y), (880, arrow_y)], fill=(255, 215, 0), width=4)

# Add description
try:
    font_desc = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", 18)
except:
    font_desc = ImageFont.load_default()

desc_text = "Vapor Compression Cycle - Industrial Applications"
draw.text((150, 420), desc_text, fill=(255, 255, 255), font=font_desc)

# Save as GIF
output_path = "d:\\4030(college)\\Minor\\project\\refrigeration-backend\\static\\industrialSystems1-ezgif.com-resize.gif"
img.save(output_path, 'GIF', optimize=False)
file_size = os.path.getsize(output_path)
print(f"✓ GIF created successfully!")
print(f"  Path: {output_path}")
print(f"  Size: {file_size:,} bytes")
print(f"  Dimensions: {width}x{height} pixels")
