        for i, ingredient in enumerate(ingredients):
            color = CARD_COLORS[i % len(CARD_COLORS)]

            card = MDCard(
                size_hint=(None, None),
                size=("200dp", "180dp"),
                radius=[24],
                elevation=6,
                padding=16,
                md_bg_color=color
            )

            card_layout = MDBoxLayout(orientation="vertical", spacing=8)

            name_label = MDLabel(
                text=ingredient,
                halign="center",
                font_style="H6",
                theme_text_color="Custom",
                text_color=(1, 1, 1, 1),
                bold=True
            )

            info_label = MDLabel(
                text="AI info coming soon",
                halign="center",
                font_style="Caption",
                theme_text_color="Custom",
                text_color=(1, 1, 1, 0.8)
            )

            badge = MDLabel(
                text=" Safe",
                halign="center",
                font_style="Caption",
                theme_text_color="Custom",
                text_color=(1, 1, 1, 1),
                bold=True
            )

            card_layout.add_widget(name_label)
            card_layout.add_widget(info_label)
            card_layout.add_widget(badge)
            card.add_widget(card_layout)
            self.grid.add_widget(card)