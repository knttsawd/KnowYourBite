import cv2
import time
import json
import re
from PIL import Image
from llama_cpp import Llama
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.boxlayout import MDBoxLayout
# import pytesseract
# pytesseract.pytesseract.tesseract_cmd = r'C:\Users\donal\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'

classifierLLM = Llama(model_path="models/Phi-3-mini-4k-instruct-q4.gguf")

with open("additives.json", "r", encoding="utf-8") as f:
    additives = json.load(f)


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
            # Case 1: value is a dict with an "en" field
            if isinstance(value, dict):
                en_value = value.get("en")
                if isinstance(en_value, str) and en_value.strip():
                    flat[key] = en_value.strip()

            # Case 2: value is a simple string or number
            elif isinstance(value, (str, int, float)):
                if str(value).strip():
                    flat[key] = value

            # Ignore anything else (lists, None, empty dicts, etc.)

        return flat
    # FIXED: Proper method signature
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
        # Split into sentences using punctuation
        sentences = re.split(r'(?<=[.!?]) +', text)

        # If the last sentence doesn't end with punctuation, drop it
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

        image = Image.open("test_photo.jpg")
        raw_text = "" # pytesseract.image_to_string(image)

        if not raw_text.strip():
            raw_text = "Salt, Water, Sugar, Natural Flavors, Citric Acid, Cryptoaxanthin"

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
                prompt = (
                    f"Provide a clear explanation of the food ingredient {ingredient} in simple language. Limit yourself to 3 paragraphs "
                    f"using only the information found here: {info}. "
                    "Describe what it is, why it is used in food, and any general health considerations. "
                    "Avoid special tokens or formatting symbols."
                )
                response = classifierLLM(prompt, max_tokens=600)
            else:
                prompt = (
                    f"Explain the food ingredient {ingredient} in clear, simple language. Limit yourself to 3 sentences. "
                    "Describe what it is, why it is used in food, and any general health considerations. "
                    "Avoid special tokens or formatting symbols."
                )

                response = classifierLLM(prompt, max_tokens=100)

            text = response["choices"][0]["text"].strip()
            text = self.clean_artifacts(text)
            text = self.remove_incomplete_sentence(text)
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
                text=ingredient,
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