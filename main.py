import cv2
import json
import re
import logging
from PIL import Image
from llama_cpp import Llama
from kivy.clock import Clock
from kivy.graphics.texture import Texture
from kivy.uix.modalview import ModalView

from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.spinner import MDSpinner
from kivymd.uix.dialog import MDDialog
from kivymd.uix.textfield import MDTextField

from rapidfuzz import fuzz
import pytesseract

logging.basicConfig(filename="app.log", level=logging.INFO)
from kivy.graphics import Color, RoundedRectangle
from kivy.uix.boxlayout import BoxLayout

import cv2
import time
import os
import sys
import shutil
import pytesseract
from PIL import Image

import shutil
import sys

# Automatically find Tesseract on any device
tesseract_path = shutil.which("tesseract")

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

BADGE_COLORS = {
    "safe": (0.18, 0.8, 0.44, 1),
    "warning": (1, 0.76, 0.03, 1),
    "danger": (0.91, 0.3, 0.24, 1),
}

CARD_COLORS = [
    (0.98, 0.36, 0.36, 1),
    (0.36, 0.78, 0.98, 1),
    (0.56, 0.93, 0.56, 1),
    (0.98, 0.78, 0.36, 1),
    (0.78, 0.56, 0.98, 1),
    (0.98, 0.56, 0.78, 1),
]

classifierLLM = Llama(
    model_path="models/Phi-3-mini-4k-instruct-q4.gguf",
    n_threads=4,
    n_ctx=512
)

with open("additives.json", "r", encoding="utf-8") as f:
    additives = json.load(f)

BASE_PROMPT = (
    "Use simple, educational language and keep the explanation to three sentences. "
    "Describe what the ingredient is, why it is used in food, and any general considerations "
    "that food-safety authorities highlight. Avoid medical advice."
)
class CameraModal(ModalView):
    def __init__(self, on_capture_callback, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (1, 1)  
        self.auto_dismiss = False
        self.on_capture_callback = on_capture_callback

        self.layout = MDBoxLayout(orientation="vertical", spacing=10, padding=10)

        from kivy.uix.image import Image
        self.preview = Image(size_hint=(1, 1), allow_stretch=True, keep_ratio=True)
        self.layout.add_widget(self.preview)

        btn_layout = MDBoxLayout(size_hint_y=None, height="70dp", spacing=20, padding=10)

        capture_btn = MDRaisedButton(
            text="Capture",
            md_bg_color=(0, 0.6, 0, 1),
            on_release=self.capture
        )
        cancel_btn = MDFlatButton(
            text="Cancel",
            on_release=lambda x: self.dismiss()
        )

        btn_layout.add_widget(capture_btn)
        btn_layout.add_widget(cancel_btn)

        self.layout.add_widget(btn_layout)
        self.add_widget(self.layout)

        self.cam = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        Clock.schedule_interval(self.update_preview, 1/30)

    def update_preview(self, dt):
        ret, frame = self.cam.read()
        if not ret:
            return

        frame = cv2.flip(frame, 0)
        buf = frame.tobytes()
        texture = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt='bgr')
        texture.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')

        self.preview.texture = texture

    def capture(self, instance):
        ret, frame = self.cam.read()
        if ret:
            self.on_capture_callback(frame)
        self.dismiss()

    def on_dismiss(self):
        if hasattr(self, "cam"):
            self.cam.release()

    
class KnowYourBiteApp(MDApp):
    def build(self):
        self.cache = {}
        self.history = []
        self.dialog = None
        self.theme_cls.primary_palette = "Green"
        self.theme_cls.theme_style = "Light"

        self.screen = MDScreen(md_bg_color=(0.9, 0.98, 0.93, 1))

        # Main layout
        main_layout = MDBoxLayout(
            orientation="vertical",
            padding=[20, 30, 20, 20],
            spacing=16
        )

        # Logo + Title
        title_layout = MDBoxLayout(
            orientation="vertical",
            size_hint_y=None,
            height="120dp",
            spacing=4
        )

        logo = MDLabel(
    text=" KnowYourBite ",
    halign="center",
    font_style="H2",
    theme_text_color="Custom",
    text_color=(0.18, 0.8, 0.44, 1),
    size_hint_y=None,
    height="80dp",
    bold=True
)

        title = MDLabel(
            text="KnowYourBite",
            halign="center",
            font_style="H4",
            size_hint_y=None,
            height="60dp"
        )

        subtitle = MDLabel(
            text="Scan your label. Know what you eat.",
            halign="center",
            font_style="Caption",
            theme_text_color="Custom",
            text_color=(0.5, 0.5, 0.5, 1),
            size_hint_y=None,
            height="30dp"
        )

        title_layout.add_widget(logo)
        title_layout.add_widget(title)
        title_layout.add_widget(subtitle)

        # Scan button
        btn = MDRaisedButton(
            text="📷  Scan Ingredient Label",
            pos_hint={"center_x": 0.5},
            size_hint=(0.7, None),
            height="52dp",
            md_bg_color=(0.18, 0.8, 0.44, 1),
            on_release=self.scan
        )

        manual_btn = MDRaisedButton(
            text="Enter Ingredients Manually",
            pos_hint={"center_x": 0.5},
            size_hint_y=None,
            height="50dp",
            on_release=self.manual_input
        )

        history_btn = MDRaisedButton(
            text="View History",
            pos_hint={"center_x": 0.5},
            size_hint_y=None,
            height="50dp",
            on_release=self.show_history
        )

        clear_btn = MDRaisedButton(
            text="Clear Results",
            pos_hint={"center_x": 0.5},
            size_hint_y=None,
            height="50dp",
            on_release=lambda x: self.grid.clear_widgets()
        )

        self.spinner = MDSpinner(size_hint=(None, None), size=("46dp", "46dp"), pos_hint={"center_x": 0.5})
        self.spinner.active = False

        self.scroll = MDScrollView()
        self.grid = MDGridLayout(
            cols=1,
            spacing=16,
            padding=[10, 10, 10, 10],
            size_hint=(1, None),
            adaptive_height=True
        )
        self.grid.bind(minimum_height=self.grid.setter("height"))
        self.scroll.add_widget(self.grid)

        main_layout.add_widget(title_layout)
        main_layout.add_widget(scan_btn)
        main_layout.add_widget(manual_btn)
        main_layout.add_widget(history_btn)
        main_layout.add_widget(clear_btn)
        main_layout.add_widget(self.spinner)
        main_layout.add_widget(self.scroll)

        self.screen.add_widget(main_layout)
        return self.screen

    def clean_text(self, text):
        text = text.replace("\n", " ")
        text = re.sub(r"[^a-zA-Z0-9, ]", "", text)
        return text.strip()

    def normalize_ingredient(self, ing):
        corrections = {
            "citrlc": "citric",
            "sodlum": "sodium",
            "natual": "natural",
            "flav0rs": "flavors",
            "nitratee": "nitrate",
        }
        ing = ing.lower()
        for wrong, right in corrections.items():
            ing = ing.replace(wrong, right)
        return ing.strip()

    def match_additive(self, ingredient, additives):
        ingredient = ingredient.lower()
        for key, item in additives.items():
            name_field = item.get("name")

            if isinstance(name_field, dict):
                for lang_name in name_field.values():
                    if isinstance(lang_name, str):
                        if fuzz.partial_ratio(ingredient, lang_name.lower()) > 80:
                            return item

            elif isinstance(name_field, str):
                if fuzz.partial_ratio(ingredient, name_field.lower()) > 80:
                    return item

        return None

    def extract_tier(self, text):
        text = text.lower()
        if any(w in text for w in ["moderation", "limit", "carefully"]):
            return "Safe in Moderation"
        if any(w in text for w in ["avoid", "risk", "harmful", "concern"]):
            return "Higher Concern"
        if any(w in text for w in ["safe", "generally safe", "low concern"]):
            return "Safe"
        return "Unknown"

    def tier_color(self, tier):
        if tier == "Safe":
            return (0.8, 1, 0.8, 1)
        if tier == "Safe in Moderation":
            return (1, 1, 0.8, 1)
        if tier == "Higher Concern":
            return (1, 0.8, 0.8, 1)
        return (0.9, 0.9, 0.9, 1)

    def safe_llm_call(self, prompt):
        try:
            response = classifierLLM(
                f"<|begin_of_text|><|start_header_id|>user<|end_header_id|>{prompt}"
                f"<|start_header_id|>assistant<|end_header_id|>",
                max_tokens=150
            )
            return response["choices"][0]["text"].strip()
        except Exception as e:
            logging.error(f"LLM error: {e}")
            return f"Error generating explanation: {e}"

    def scan(self, instance):
        modal = CameraModal(on_capture_callback=self.process_captured_frame)
        modal.open()

    def process_captured_frame(self, frame):
        self.spinner.active = True
        Clock.schedule_once(lambda dt: self._process_frame_async(frame), 0)

    def _process_frame_async(self, frame):
        self.grid.clear_widgets()

        try:
            cv2.imwrite("test_photo.jpg", frame)

            image = Image.open("test_photo.jpg")
            image = image.resize((image.width // 2, image.height // 2))

            raw_text = pytesseract.image_to_string(image, config="--oem 1 --psm 6")
            raw_text = self.clean_text(raw_text)

            if not raw_text:
                raw_text = "Salt, Water, Sugar, Citric Acid"

        except Exception as e:
            self.add_error_card(f"Camera or OCR error: {e}")
            self.spinner.active = False
            return

        ingredients = [i.strip() for i in raw_text.split(",") if i.strip()]

        for ing in ingredients:
            ing = self.normalize_ingredient(ing)
            self.process_ingredient(ing)

        self.spinner.active = False

    def process_ingredient(self, ingredient):
        if ingredient in self.cache:
            explanation = self.cache[ingredient]
        else:
            additive_info = self.match_additive(ingredient, additives)

            if additive_info:
                info = {k: v for k, v in additive_info.items()
                        if k in ["additives_classes", "vegan", "vegetarian", "organic_eu"]}

                prompt = (
                    f"Using only this information: {info}, explain the general safety of {ingredient}. "
                    f"{BASE_PROMPT}"
                )
            else:
                prompt = (
                    f"Explain the general safety of {ingredient} using the tiers Safe, "
                    f"Safe in Moderation, or Higher Concern. {BASE_PROMPT}"
                )

            explanation = self.safe_llm_call(prompt)
            explanation = explanation.split("\n")[0]
            self.cache[ingredient] = explanation

        tier = self.extract_tier(explanation)
        self.history.append((ingredient, tier, explanation))
        self.add_card(ingredient, tier, explanation)

    def add_card(self, ingredient, tier, text):
        card = MDCard(
            orientation="vertical",
            padding=20,
            radius=[25],
            elevation=6,
            size_hint=(1, None),
            md_bg_color=self.tier_color(tier),
            adaptive_height=True
        )

        
        label = MDLabel(
            text=f"{Ingredient.capitalize()} - {tier}",
            halign="center",
            font_style="H6",
            size_hint_y=None,
            theme_text_color="Custom",
            text_color=(1, 1, 1, 1),
                bold=True,
            height="30dp"
        )


        definition = MDLabel(
            text=text,
            halign="left",
            font_style="Caption",
                theme_text_color="Custom",
                text_color=(1, 1, 1, 0.8),

            size_hint_y=None,
            text_size=(self.screen.width - 80, None),
            adaptive_height=True
        )

        card.add_widget(label)
        card.add_widget(definition)
        self.grid.add_widget(card)

    def add_error_card(self, message):
        card = MDCard(
            orientation="vertical",
            padding=16,
            radius=[24],
            elevation=6,
            size_hint=(1, None),
            md_bg_color=(1, 0.9, 0.9, 1),
            adaptive_height=True,
            size=("200dp", "180dp")
        )

         

        label = MDLabel(
            text="Error",
            halign="left",
            font_style="H6",
            size_hint_y=None,
            height="30dp"
        )

        definition = MDLabel(
            text=message,
            halign="left",
            theme_text_color="Secondary",
            adaptive_height=True
        )

        retry_btn = MDFlatButton(
            text="Try Again",
            on_release=self.scan
        )

        card.add_widget(label)
        card.add_widget(definition)
        card.add_widget(retry_btn)
        self.grid.add_widget(card)

    def manual_input(self, instance):
        self.dialog = MDDialog(
            title="Enter Ingredients",
            type="custom",
            content_cls=MDTextField(hint_text="Please return a list of ingredient names separated by commas"),
            buttons=[
                MDRaisedButton(text="Submit", on_release=self.process_manual)
            ]
        )
        self.dialog.open()

    def process_manual(self, instance):
        text = self.dialog.content_cls.text
        self.dialog.dismiss()

        ingredients = [i.strip() for i in text.split(",") if i.strip()]
        self.grid.clear_widgets()

        for ing in ingredients:
            ing = self.normalize_ingredient(ing)
            self.process_ingredient(ing)

    def show_history(self, instance):
        self.grid.clear_widgets()
        for ingredient, tier, explanation in self.history:
            self.add_card(ingredient, tier, explanation)


KnowYourBiteApp().run()