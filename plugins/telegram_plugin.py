from .base import NotConfiguredPlugin

class TelegramPlugin(NotConfiguredPlugin):
    def __init__(self) -> None:
        super().__init__("telegram")
