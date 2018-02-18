from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
import Adafruit_SSD1306


class Display:
    RST = 24
    def __init__(self):
        disp = Adafruit_SSD1306.SSD1306_128_32(rst=self.RST)
        disp.begin()
        disp.clear()
        disp.display()
        width = disp.width
        height = disp.height
        image = Image.new('1', (width, height))
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, 0, width, height), outline=0, fill=0)
        # Draw some shapes.
        # First define some constants to allow easy resizing of shapes.
        padding = 2
        shape_width = 20
        top = padding
        bottom = height-padding
        # Move left to right keeping track of the current x position for drawing shapes.
        x = padding
        # Draw an ellipse.
        draw.ellipse((x, top , x+shape_width, bottom), outline=255, fill=0)
        x += shape_width+padding
        # Draw a rectangle.
        draw.rectangle((x, top, x+shape_width, bottom), outline=255, fill=0)
        x += shape_width+padding
        # Draw a triangle.
        draw.polygon([(x, bottom), (x+shape_width/2, top), (x+shape_width, bottom)], outline=255, fill=0)
        x += shape_width+padding
        # Draw an X.
        draw.line((x, bottom, x+shape_width, top), fill=255)
        draw.line((x, top, x+shape_width, bottom), fill=255)
        x += shape_width+padding
        # Load default font.
        font = ImageFont.load_default()
        # Write two lines of text.
        draw.text((x, top),    'Hello',  font=font, fill=255)
        draw.text((x, top+20), 'World!', font=font, fill=255)
        # Display image.
        disp.image(image)
        disp.display()