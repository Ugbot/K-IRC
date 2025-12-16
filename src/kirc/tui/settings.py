"""Settings Screen for K-IRC."""

from pathlib import Path
from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Label, Static

from kirc.config import load_settings


class SettingsScreen(Screen):
    """Screen to view and verify current configuration."""

    CSS = """
    SettingsScreen {
        align: center middle;
        background: $background;
    }

    #settings-container {
        width: 70;
        height: auto;
        border: heavy $neon-cyan;
        padding: 1 2;
        background: $surface;
    }

    .settings-title {
        text-style: bold;
        color: $neon-pink;
        text-align: center;
        margin-bottom: 1;
    }

    .setting-row {
        height: auto;
        margin: 1 0;
    }

    .setting-label {
        width: 20;
        color: $neon-cyan;
        text-style: bold;
    }

    .setting-value {
        width: 1fr;
        color: $text-main;
    }
    
    .status-ok {
        color: $neon-green;
    }
    
    .status-error {
        color: $neon-red;
    }

    Button {
        width: 100%;
        margin-top: 1;
        background: $custom-panel;
        color: $neon-cyan;
        border: heavy $neon-cyan;
    }
    
    Button:hover {
        background: $neon-cyan;
        color: $background;
    }
    """

    def compose(self) -> ComposeResult:
        settings = load_settings()
        
        # Check certs
        ca_exists = Path(settings.kafka.ssl_cafile).exists()
        cert_exists = Path(settings.kafka.ssl_certfile).exists()
        key_exists = Path(settings.kafka.ssl_keyfile).exists()
        
        yield Header()
        with Container(id="settings-container"):
            yield Label("SYSTEM_CONFIGURATION", classes="settings-title")
            
            with Vertical():
                # User Info
                with Horizontal(classes="setting-row"):
                    yield Label("USERNAME:", classes="setting-label")
                    yield Label(settings.user_config.username, classes="setting-value")

                # Kafka Config
                with Horizontal(classes="setting-row"):
                    yield Label("BOOTSTRAP:", classes="setting-label")
                    yield Label(settings.kafka.bootstrap_servers, classes="setting-value")

                # Cert Status
                with Horizontal(classes="setting-row"):
                    yield Label("CA CERT:", classes="setting-label")
                    status = "FOUND" if ca_exists else "MISSING"
                    style = "status-ok" if ca_exists else "status-error"
                    yield Label(status, classes=f"setting-value {style}")

                with Horizontal(classes="setting-row"):
                    yield Label("CLIENT CERT:", classes="setting-label")
                    status = "FOUND" if cert_exists else "MISSING"
                    style = "status-ok" if cert_exists else "status-error"
                    yield Label(status, classes=f"setting-value {style}")

                with Horizontal(classes="setting-row"):
                    yield Label("CLIENT KEY:", classes="setting-label")
                    status = "FOUND" if key_exists else "MISSING"
                    style = "status-ok" if key_exists else "status-error"
                    yield Label(status, classes=f"setting-value {style}")

            yield Button("RETURN_TO_CONSOLE", id="back-btn", variant="error")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back-btn":
            self.app.pop_screen()
