import cv2
import time
import json
import re
from PIL import Image
from bs4 import BeautifulSoup
from llama_cpp import Llama
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.boxlayout import MDBoxLayout
import pytesseract
import requests
#pytesseract.pytesseract.tesseract_cmd = r'C:\Users\donal\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'

classifierLLM = Llama(model_path="models/Phi-3-mini-4k-instruct-q4.gguf")

with open("additives.json", "r", encoding="utf-8") as f:
    additives = json.load(f)

def cas_from_enumber(e_number):
    ins = re.sub(r"^[eE]\s*", "", e_number).strip()

    query = f"""
    SELECT ?cas WHERE {{
      ?item wdt:P1013 "{ins}" .   # INS number property
      ?item wdt:P231 ?cas .       # CAS number property
    }}
    """

    url = "https://query.wikidata.org/sparql"
    headers = {"Accept": "application/sparql-results+json"}

    r = requests.get(url, params={"query": query}, headers=headers)

    if r.status_code != 200:
        return None

    data = r.json()

    results = data.get("results", {}).get("bindings", [])
    if not results:
        return None

    return results[0]["cas"]["value"]

def search_jecfa(e_num):
    url = "https://www.fao.org/food/food-safety-quality/scientific-advice/jecfa/jecfa-additives/en/c/"
    cas = cas_from_enumber(e_num)
    params = {"search": cas}
    r = requests.get(url, params=params)

    if r.status_code != 200:
        return None

    soup = BeautifulSoup(r.text, "html.parser")

    tables = soup.find_all("table")
    if not tables:
        return None

    results = []

    for table in tables:
        rows = table.find_all("tr")
        if not rows:
            continue

        header = [h.get_text(strip=True).lower() for h in rows[0].find_all("th")]

        if ("name" in header and "adi" in header) or len(header) >= 3:
            for row in rows[1:]:
                cols = [c.get_text(strip=True) for c in row.find_all("td")]
                if len(cols) >= 3:
                    results.append({
                        "name": cols[0],
                        "ins_number": cols[1] if len(cols) > 1 else None,
                        "adi": cols[2] if len(cols) > 2 else None,
                        "notes": cols[3] if len(cols) > 3 else None
                    })

    return results


class KnowYourBiteApp(MDApp):

    def build(self):
        self.theme_cls.primary_palette = "Green"

        self.screen = MDScreen()

        layout = MDBoxLayout(orientation="vertical", padding=20, spacing=20)

        title = MDLabel(
            text="KnowYourBite",
            halign="center",
            font_style="H4",
            size_hint_y=None,
            height="60dp"
        )

        btn = MDRaisedButton(
            text="Scan Ingredient Label",
            pos_hint={"center_x": 0.5},
            size_hint_y=None,
            height="50dp",
            on_release=self.scan
        )

        self.scroll = MDScrollView()
        self.grid = MDGridLayout(
            cols=1,
            spacing=20,
            padding=20,
            size_hint=(1, None),
            adaptive_height=True
        )
        self.grid.bind(minimum_height=self.grid.setter("height"))
        self.scroll.add_widget(self.grid)

        layout.add_widget(title)
        layout.add_widget(btn)
        layout.add_widget(self.scroll)

        self.screen.add_widget(layout)
        return self.screen
    def flatten_info(self, info):
        flat = {}

        for key, value in info.items():
            if isinstance(value, dict):
                en_value = value.get("en")
                if isinstance(en_value, str) and en_value.strip():
                    flat[key] = en_value.strip()

            elif isinstance(value, (str, int, float)):
                if str(value).strip():
                    flat[key] = value

        return flat
    def extract_tier(self, response_text):
        text = response_text.lower()
        moderation_keywords = [
            "moderation", "moderate", "limit", "limited amounts",
            "not too much", "small amounts", "consume carefully"
        ]
        if any(word in text for word in moderation_keywords):
            return "Safe in Moderation"
        concern_keywords = [
            "concern", "risk", "avoid", "harmful", "safety concerns",
            "higher risk", "potential issues", "watch out", "problematic"
        ]
        if any(word in text for word in concern_keywords):
            return "Higher Concern"
        safe_keywords = [
            "safe", "generally safe", "low concern", "not a major concern",
            "considered safe", "minimal concern"
        ]
        if any(word in text for word in safe_keywords):
            return "Safe"
        return None


    def match_additive(self, ingredient, additives):
        ingredient = ingredient.lower()

        for key, item in additives.items():
            name_field = item.get("name")

            if isinstance(name_field, dict):
                en = name_field.get("en", "")
                if isinstance(en, str) and ingredient in en.lower():
                    return item

                for lang_name in name_field.values():
                    if isinstance(lang_name, str) and ingredient in lang_name.lower():
                        return item

            elif isinstance(name_field, str):
                if ingredient in name_field.lower():
                    return item

        return None
    def clean_artifacts(self, text):
        bad_tokens = [
            "<|assistant|>", "<|user|>", "<|system|>",
            "<s>", "</s>", "###", "```", "****"
        ]

        for token in bad_tokens:
            text = text.replace(token, "")

        return text.strip()
    def remove_incomplete_sentence(self, text):
        sentences = re.split(r'(?<=[.!?]) +', text)

        if sentences and not sentences[-1].strip().endswith(('.', '!', '?')):
            sentences = sentences[:-1]

        return " ".join(sentences).strip()

    def scan(self, instance):
        global additives

        cam = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        time.sleep(2)
        ret, frame = cam.read()
        cv2.imwrite("test_photo.jpg", frame)
        cam.release()

        #image = Image.open("test_photo.jpg")
        raw_text = "" #pytesseract.image_to_string(image)

        if not raw_text.strip():
            raw_text = "Salt, Water, Sugar, Natural Flavors, Citric Acid, Cryptoaxanthin, Sodium Nitrate"

        ingredients = [item.strip() for item in raw_text.split(",") if item.strip()]

        self.grid.clear_widgets()

        for ingredient in ingredients:
            active_ingredient_info = self.match_additive(" " + ingredient, additives)
            if active_ingredient_info:
                ALLOWED_KEYS = [
                    "additives_classes",
                    "vegan",
                    "vegetarian",
                    "organic_eu"
                ]
                info = self.flatten_info(active_ingredient_info)
                info = {key: value for key, value in info.items() if key in ALLOWED_KEYS}
                print(info)
                if info:
                    prompt = (
    f"Using only the information found here: {info}, explain the general safety of {ingredient} "
    "by placing it into one of three broad tiers: Safe, Safe in Moderation, or Higher Concern. "
    "Use simple, educational language and keep the explanation to three sentences. "
    "Describe what the ingredient is, why it is used in food, and any general considerations "
    "that food-safety authorities highlight. Avoid medical advice."
)
                else:
                    prompt = (
    f"Explain the general safety of {ingredient} using three broad tiers: "
    "Safe, Safe in Moderation, or Higher Concern. "
    "Use simple, educational language and keep the explanation to three sentences. "
    "Describe what the ingredient is, why it is used in food, and any general considerations "
    "that food-safety authorities highlight. Avoid medical advice."
)

                response = classifierLLM(f"<|begin_of_text|><|start_header_id|>user<|end_header_id|>{prompt}<|start_header_id|>assistant<|end_header_id|>", max_tokens=600)
            else:
                prompt = (
    f"Explain the general safety of {ingredient} using three broad tiers: "
    "Safe, Safe in Moderation, or Higher Concern. "
    "Use simple, educational language and keep the explanation to three sentences. "
    "Describe what the ingredient is, why it is used in food, and any general considerations "
    "that major food-safety authorities highlight. Avoid medical advice."
)
                response = classifierLLM(f"<|begin_of_text|><|start_header_id|>user<|end_header_id|>{prompt}<|start_header_id|>assistant<|end_header_id|>", max_tokens=100)
            text = response["choices"][0]["text"].strip()
            text = self.clean_artifacts(text)
            text = self.remove_incomplete_sentence(text)
            text = text.split("\n")[0]
            card = MDCard(
                orientation="vertical",
                padding=20,
                radius=[25],
                elevation=6,
                size_hint=(1, None),
                md_bg_color=(0.98, 0.98, 0.98, 1),
                adaptive_height=True
            )

            label = MDLabel(
                text=f"{ingredient} - {self.extract_tier(text)}",
                halign="left",
                font_style="H6",
                size_hint_y=None,
                height="30dp"
            )

            definition = MDLabel(
                text=text,
                halign="left",
                theme_text_color="Secondary",
                size_hint_y=None,
                text_size=(self.screen.width - 80, None),
                adaptive_height=True
            )

            card.add_widget(label)
            card.add_widget(definition)
            self.grid.add_widget(card)


KnowYourBiteApp().run()