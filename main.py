import cv2
import time
import pytesseract
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

pytesseract.pytesseract.tesseract_cmd = r'C:\Users\donal\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'
classifierLLM = Llama(model_path=("models\Phi-3-mini-4k-instruct-q4.gguf"))
class KnowYourBiteApp(MDApp):
    def build(self):
        self.theme_cls.primary_palette = "Green"

        self.screen = MDScreen()

        # Main layout
        layout = MDBoxLayout(orientation="vertical", padding=20, spacing=20)

        # Title
        title = MDLabel(
            text="KnowYourBite",
            halign="center",
            font_style="H4",
            size_hint_y=None,
            height="60dp"
        )

        # Scan button
        btn = MDRaisedButton(
            text="Scan Ingredient Label",
            pos_hint={"center_x": 0.5},
            size_hint_y=None,
            height="50dp",
            on_release=self.scan
        )

        # Scrollable card grid
        self.scroll = MDScrollView()
        self.grid = MDGridLayout(
            cols=2,
            spacing=20,
            padding=20,size_hint=(1, None),
adaptive_height=True,

        )
        self.grid.bind(minimum_height=self.grid.setter("height"))
        self.scroll.add_widget(self.grid)

        layout.add_widget(title)
        layout.add_widget(btn)
        layout.add_widget(self.scroll)

        self.screen.add_widget(layout)
        return self.screen

    def scan(self, instance):
        # Step 1 - Take photo
        cam = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        time.sleep(2)
        ret, frame = cam.read()
        cv2.imwrite("test_photo.jpg", frame)
        cam.release()

        # Step 2 - Read text
        image = Image.open("test_photo.jpg")
        raw_text = pytesseract.image_to_string(image)

        # Step 3 - Parse ingredients
        if not raw_text.strip():
            raw_text = "Water, Sugar, Salt, Citric Acid, Natural Flavors"

        ingredients = [item.strip() for item in raw_text.split(",") if item.strip()]

        # Step 4 - Show cards
        self.grid.clear_widgets()
        for ingredient in ingredients:
            response = classifierLLM(f"Explain the food ingredient {ingredient} in clear, simple language. Describe what it is, why it is used in food, and any health benefits or concerns. Do not include any special tokens, role markers, or formatting symbols.", max_tokens=50)
            text=response["choices"][0]["text"]
            text=text.split("<|assistant|>")
            card = MDCard(
                orientation="vertical",
                padding=16,
                radius=[20],
                elevation=4,
                size_hint=(1, None),
                adaptive_height=True
            )

            label = MDLabel(
                text=ingredient,
                halign="center",
                size_hint_y=None,
                adaptive_height=True
            )

            definition = MDLabel(
                text=text[-1],
                halign="center",
                size_hint_y=None,
                adaptive_height=True
            )

            card.add_widget(label)
            card.add_widget(definition)
            self.grid.add_widget(card)

KnowYourBiteApp().run()