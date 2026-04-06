from kivy.config import Config
Config.set("graphics", "width", "300")
Config.set("graphics", "height", "600")
import io
import json
import logging
import re
import cv2

import requests
from PIL import Image as PILImage
from rapidfuzz import fuzz
from llama_cpp import Llama

from kivy.utils import platform
from kivy.core.camera import Camera
from kivy.clock import Clock
from kivy.uix.widget import Widget
from kivy.properties import NumericProperty
from kivy.graphics.texture import Texture
from kivy.uix.modalview import ModalView
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivy.uix.image import Image
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.spinner import MDSpinner
from kivymd.uix.dialog import MDDialog
from kivymd.uix.textfield import MDTextField


logging.basicConfig(filename="app.log", level=logging.INFO)
from kivy.graphics import Color, RoundedRectangle
from kivy.uix.boxlayout import BoxLayout


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

SERVER = "http://localhost:8000"
def call_phi3(prompt):
    payload = {
        "prompt": prompt,
        "max_tokens": 128
    }

    response = requests.post(f"{SERVER}/phi3", json=payload)
    data = response.json()

    return data["response"]

def send_frame_to_ocr(frame):
    image = PILImage.fromarray(frame)

    image = image.resize((image.width // 2, image.height // 2))

    buffer = io.BytesIO()
    image.save(buffer, format="JPEG")
    image_bytes = buffer.getvalue()

    response = requests.post(
        f"{SERVER}/ocr",
        data=image_bytes,
        headers={"Content-Type": "application/octet-stream"}
    )
    data = response.json()
    return data["text"]


with open("additives.json", "r", encoding="utf-8") as f:
    additives = json.load(f)

BASE_PROMPT = (
    "Use simple, educational language and keep the explanation to three sentences, avoiding special characters. "
    "Describe what the ingredient is, why it is used in food, and any general considerations "
    "that food-safety authorities highlight. Avoid medical advice."
)


class CameraModal(ModalView):
    def __init__(self, on_capture_callback, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (1, 1)
        self.auto_dismiss = False
        self.on_capture_callback = on_capture_callback

        # Layout
        self.layout = MDBoxLayout(orientation="vertical", spacing=10, padding=10)

        # Preview widget
        self.preview = Image(size_hint=(1, 1), allow_stretch=True, keep_ratio=True)
        self.layout.add_widget(self.preview)

        # Buttons
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

        self.is_android = platform == "android"

        self.init_opencv_camera()

    def init_opencv_camera(self):
        self.cap = cv2.VideoCapture(0)

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        self.current_frame = None

        Clock.schedule_interval(self.update_preview, 1/30)

    def update_preview(self, dt):
        if not self.cap.isOpened():
            return

        ret, frame = self.cap.read()
        if not ret:
            return

        self.current_frame = frame

        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        texture = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt='rgb')
        texture.blit_buffer(frame.tobytes(), colorfmt='rgb', bufferfmt='ubyte')

        self.preview.texture = texture

    def capture(self, *args):
        if self.current_frame is None:
            return

        rgb = cv2.cvtColor(self.current_frame, cv2.COLOR_BGR2RGB)

        img = PILImage.fromarray(rgb)

        buffer = io.BytesIO()
        img.save(buffer, format="JPEG")
        buffer.seek(0)

        self.on_capture_callback(buffer)

        self.dismiss()

    def on_dismiss(self):
        if hasattr(self, "cap") and self.cap.isOpened():
            self.cap.release()
class AutoResizeLabel(MDLabel):
    min_font_size = NumericProperty(10)
    max_font_size = NumericProperty(40)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.text_size = (None, None)  # keep text on one line
        Clock.schedule_once(self.adjust_font_size)

    def adjust_font_size(self, *args):
        font_size = self.max_font_size
        self.font_size = font_size

        while font_size > self.min_font_size:
            self.texture_update()
            if self.texture_size[0] <= self.width:
                break
            font_size -= 1
            self.font_size = font_size

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
            height="160dp",
            spacing=6,
            padding=[0, 10, 0, 10]
        )


        logo = AutoResizeLabel(
    text="KnowYourBite",
    halign="center",
    theme_text_color="Custom",
    text_color=(0.10, 0.65, 0.35, 1),
    size_hint_y=None,
    height="70dp",
    bold=True,
    max_font_size=54,
    min_font_size=24
)


        subtitle = MDLabel(
    text="Scan your label. Know what you eat.",
    halign="center",
    font_style="Subtitle2",
    theme_text_color="Custom",
    text_color=(0.25, 0.25, 0.25, 1),
    size_hint_y=None,
    height="28dp"
)

        disclaimer = MDLabel(
    text="For informational purposes only — not medical advice.",
    halign="center",
    font_style="Caption",
    theme_text_color="Custom",
    text_color=(0.45, 0.45, 0.45, 1),
    size_hint_y=None,
    height="22dp"
)


        title_layout.add_widget(logo)
        title_layout.add_widget(subtitle)
        title_layout.add_widget(disclaimer)

        # Scan button
        scan_btn = MDRaisedButton(
            text="Scan Ingredient Label",
            pos_hint={"center_x": 0.5},
            size_hint=(0.7, None),
            height="52dp",
            md_bg_color=(0.18, 0.8, 0.44, 1),
            on_release=self.scan
        )

        manual_btn = MDRaisedButton(
            text="Enter Ingredients Manually",
            pos_hint={"center_x": 0.5},
            size_hint=(0.7, None),
            height="52dp",
            md_bg_color=(0.18, 0.8, 0.44, 1),
            on_release=self.manual_input
        )

        history_btn = MDRaisedButton(
            text="View History",
            pos_hint={"center_x": 0.5},
            size_hint=(0.7, None),
            height="52dp",
            md_bg_color=(0.18, 0.8, 0.44, 1),
            on_release=self.show_history
        )

        clear_btn = MDRaisedButton(
            text="Clear Results",
            pos_hint={"center_x": 0.5},
            size_hint=(0.7, None),
            height="52dp",
            md_bg_color=(0.18, 0.8, 0.44, 1),
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

        SAFE_PHRASES = [
            "low risk",
            "low-risk",
            "not harmful",
            "no harm",
            "no concern",
            "not a concern",
            "generally safe",
            "safe to use",
            "do not avoid",
            "minimal risk",
            "low concern"
        ]

        if any(p in text for p in SAFE_PHRASES):
            return "Safe"

        if any(w in text for w in ["moderation", "limit", "carefully"]):
            return "Safe in Moderation"

        if "safe" in text:
            return "Safe"

        if any(w in text for w in ["risk", "harmful", "concern"]):
            return "Higher Concern"

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
            response = call_phi3(
                f"<|begin_of_text|><|start_header_id|>user<|end_header_id|>{prompt}"
                f"<|start_header_id|>assistant<|end_header_id|>"
            )
            return response
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
            raw_text = send_frame_to_ocr(frame)
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
                    f"Using only this information: {info}, explain the general safety of {ingredient} using the tiers Safe, Safe in Moderation, or Higher Concern. "
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
            text=f"{ingredient.capitalize()} - {tier}",
            halign="center",
            font_style="H6",
            size_hint_y=None,
            theme_text_color="Custom",
            text_color=(0, 0, 0, 1),
            bold=True,
            height="30dp"
        )

        # Spacer
        spacer = Widget(size_hint_y=None, height="12dp")

        definition = MDLabel(
            text=text,
            halign="left",
            font_style="Caption",
            theme_text_color="Custom",
            text_color=(0, 0, 0, 1),
            size_hint_y=None,
            text_size=(self.screen.width - 80, None),
            adaptive_height=True
        )

        card.add_widget(label)
        card.add_widget(spacer)
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
            content_cls=MDTextField(hint_text="Comma separated list"),
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