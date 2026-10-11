"""Lifecycle contract. Native Android service wiring remains platform-specific."""
from dataclasses import dataclass

@dataclass
class BackgroundServiceState:
    enabled: bool = False
    status: str = "STOPPED"

class BackgroundService:
    def __init__(self) -> None:
        self.state = BackgroundServiceState()

    def start(self) -> BackgroundServiceState:
        self.state.enabled = True
        self.state.status = "NATIVE_ANDROID_INTEGRATION_REQUIRED"
        return self.state

    def stop(self) -> BackgroundServiceState:
        self.state.enabled = False
        self.state.status = "STOPPED"
        return self.state
