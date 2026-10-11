"""Minimal EMO setup/status screen. This is not a chat interface."""
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.utils import get_color_from_hex

class EmoSetupApp(App):
    title = "EMO"

    def build(self):
        root = BoxLayout(orientation="vertical", padding=24, spacing=16)
        root.add_widget(Label(
            text="[b]EMO[/b]\nGemini companion setup",
            markup=True, font_size="28sp", color=get_color_from_hex("#0846ED"),
            size_hint_y=None, height="100dp"
        ))
        root.add_widget(Label(
            text="EMO does not provide a separate chat. Enable the Accessibility service in Android Settings only after the native service is installed. Commands are processed only when explicitly prefixed with “يا EMO”.",
            halign="left", valign="middle", color=get_color_from_hex("#303846")
        ))
        self.status = Label(
            text="Native Accessibility integration: NOT INSTALLED",
            color=get_color_from_hex("#B45309"), size_hint_y=None, height="60dp"
        )
        root.add_widget(self.status)
        button = Button(
            text="Check integration status", size_hint_y=None, height="52dp",
            background_normal="", background_color=get_color_from_hex("#0846ED")
        )
        button.bind(on_press=self.check_status)
        root.add_widget(button)
        root.add_widget(Label(
            text="Privacy: G-EMO must not read unrelated apps or store message history. Sensitive actions require confirmation.",
            halign="left", valign="bottom", color=get_color_from_hex("#606875")
        ))
        return root

    def check_status(self, *_):
        # A native bridge must replace this placeholder before production release.
        self.status.text = "BLOCKED: native Accessibility bridge is not implemented"

if __name__ == "__main__":
    EmoSetupApp().run()
