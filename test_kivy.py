from kivymd.app import MDApp
from kivymd.uix.label import MDLabel

class TestApp(MDApp):
    def build(self):
        return MDLabel(
            text="KivyMD is working!",
            halign="center"
        )

TestApp().run()