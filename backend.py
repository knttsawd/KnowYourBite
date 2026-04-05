from fastapi import FastAPI, UploadFile, File, Body
from pydantic import BaseModel
from typing import Optional
from io import BytesIO
from PIL import Image
import pytesseract
import sys
import os


from llama_cpp import Llama

tesseract_path = "models/tesseract.exe"

if tesseract_path:
    pytesseract.pytesseract.tesseract_cmd = tesseract_path

if tesseract_path:
    pytesseract.pytesseract.tesseract_cmd = tesseract_path
elif sys.platform == "win32":
    # Common Windows locations
    for path in [
        r'C:\Program Files\Tesseract-OCR\tesseract.exe',
        r'C:\Users\{}\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'.format(os.getenv('USERNAME'))
    ]:
        if os.path.exists(path):
            pytesseract.pytesseract.tesseract_cmd = path
            break

app = FastAPI()

# Load Phi-3 (GGUF)
llm = Llama(
    model_path="models\\Phi-3-mini-4k-instruct-q4.gguf",
    n_ctx=512,
    n_threads=4
)
import re

def complete_sentences(text: str) -> str:
    sentences = re.split(r'(?<=[.!?])\s+', text)
    if len(sentences) == 1:
        return ""
    return " ".join(sentences[:-1])

class Phi3Request(BaseModel):
    prompt: str
    max_tokens: Optional[int] = 128

@app.post("/phi3")
def run_phi3(req: Phi3Request):
    result = llm(
        req.prompt,
        max_tokens=req.max_tokens,
        temperature=0.7
    )
    text = result["choices"][0]["text"].strip()
    text = text.split("\n")[0]
    return {"response": complete_sentences(text)}


@app.post("/ocr")
async def run_ocr(image_bytes: bytes = Body(...)):
    try:
        image = Image.open(BytesIO(image_bytes))
        image = image.convert("RGB")
    except Exception as e:
        return {"error": f"Invalid image: {e}"}

    try:
        text = pytesseract.image_to_string(
            image,
            config="--oem 1 --psm 4"
        )
        return {"text": text}
    except Exception as e:
        return {"error": f"OCR failed: {e}"}
