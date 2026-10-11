from .base import NotConfiguredPlugin

class EmailPlugin(NotConfiguredPlugin):
    def __init__(self) -> None:
        super().__init__("email")
