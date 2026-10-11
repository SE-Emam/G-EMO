from .base import NotConfiguredPlugin

class DrivePlugin(NotConfiguredPlugin):
    def __init__(self) -> None:
        super().__init__("drive")
