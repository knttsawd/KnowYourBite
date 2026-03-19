import cv2
import time
import pytesseract
from PIL import Image

pytesseract.pytesseract.tesseract_cmd = r'C:\Users\donal\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'

# Step 1 - Take photo
print("Taking photo in 3 seconds... hold your ingredient label steady!")
time.sleep(3)
cam = cv2.VideoCapture(0, cv2.CAP_DSHOW)
time.sleep(2)
ret, frame = cam.read()
cv2.imwrite("test_photo.jpg", frame)
cam.release()
print("Photo taken!")

# Step 2 - Read text
image = Image.open("test_photo.jpg")
raw_text = pytesseract.image_to_string(image)
print("Raw text:", raw_text)

# Step 3 - Parse ingredients
# If camera couldn't read, use manual input for now
if not raw_text.strip():
    raw_text = input("Camera couldn't read. Type ingredients manually: ")

ingredients = [item.strip() for item in raw_text.split(",") if item.strip()]
print("Ingredients found:", ingredients)

# Step 4 - Generate cards
cards_html = ""
for ingredient in ingredients:
    cards_html += f"""
        <div class="card">
            <h2>{ingredient}</h2>
            <p>AI info will go here</p>
            <span class="badge safe">✅ Safe</span>
        </div>
    """

# Step 5 - Save as HTML file
with open("results.html", "w", encoding="utf-8") as f:
    f.write(f"""
<!DOCTYPE html>
<html>
<head>
    <title>KnowYourBite</title>
    <style>
        body {{ font-family: Arial; background: #f0f7f2; padding: 40px; }}
        h1 {{ text-align: center; color: #1e6b3c; }}
        .cards-container {{ display: flex; flex-wrap: wrap; gap: 24px; justify-content: center; margin-top: 30px; }}
        .card {{ background: white; border-radius: 20px; padding: 28px; width: 220px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); text-align: center; border-top: 5px solid #2c7a4b; }}
        .card h2 {{ color: #1e6b3c; margin-bottom: 12px; }}
        .card p {{ color: #777; font-size: 13px; }}
        .badge {{ padding: 6px 16px; border-radius: 20px; font-size: 12px; font-weight: bold; }}
        .safe {{ background: #e6f4ec; color: #2c7a4b; }}
    </style>
</head>
<body>
    <h1> KnowYourBite</h1>
    <div class="cards-container">
        {cards_html}
    </div>
</body>
</html>
    """)

print("Done! Open results.html to see your cards!")