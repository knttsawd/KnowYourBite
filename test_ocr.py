import pytesseract
from PIL import Image

# Tell Python where Tesseract is installed
pytesseract.pytesseract.tesseract_cmd = r'C:\Users\donal\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'

# Read text from the photo
image = Image.open("test_photo.jpg")
text = pytesseract.image_to_string(image)

print("Text found:")
print(text)