import pytesseract
from PIL import Image

pytesseract.pytesseract.tesseract_cmd = r'C:\Users\donal\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'

# Temporary - type ingredients manually for testing
raw_text = "Water, Sugar, Salt, Citric Acid, Natural Flavors"

# Parse into ingredients list
ingredients = [item.strip() for item in raw_text.split(",") if item.strip()]

print("Ingredients found:")
for i, ingredient in enumerate(ingredients, 1):
    print(f"{i}. {ingredient}")