from .base import NotConfiguredPlugin

class FacebookPlugin(NotConfiguredPlugin):
    def __init__(self) -> None:
        super().__init__("facebook")
