"""Setup Wizard for K-IRC."""

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Label, Static
from textual.reactive import reactive

from kirc.crypto import generate_key_pair, save_key_to_file
from kirc.db.models import UserProfile


class WizardScreen(Screen):
    """Wizard screen for initial setup."""

    CSS = """
    WizardScreen {
        align: center middle;
        background: $background;
    }

    #wizard-container {
        width: 60;
        height: auto;
        border: heavy $neon-cyan;
        padding: 1 2;
        background: $surface;
    }

    .wizard-title {
        text-style: bold;
        color: $neon-pink;
        text-align: center;
        margin-bottom: 1;
    }

    .wizard-step {
        margin: 1 0;
        color: $text-main;
    }

    Input {
        margin: 1 0;
        border: solid $neon-cyan;
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

    step = reactive(1)
    
    def __init__(self) -> None:
        super().__init__()
        self.username = ""
        self.display_name = ""

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(id="wizard-container"):
            yield Static("INITIALIZATION_SEQUENCE", classes="wizard-title")
            with Vertical(id="step-content"):
                yield Label("Welcome to K-IRC, Netrunner.", classes="wizard-step")
                yield Label("We need to establish your identity and uplink.", classes="wizard-step")
                yield Button("INITIATE_SETUP", id="start-btn", variant="primary")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "start-btn":
            self.step = 2
            self.update_step()
        elif event.button.id == "save-profile-btn":
            self.save_profile()
        elif event.button.id == "gen-keys-btn":
            self.generate_identity()
        elif event.button.id == "save-pg-btn":
            self.pg_uri = self.query_one("#pg-uri-input", Input).value.strip()
            self.step = 5
            self.update_step()
        elif event.button.id == "save-valkey-btn":
            self.valkey_uri = self.query_one("#valkey-uri-input", Input).value.strip()
            self.step = 6
            self.update_step()
        elif event.button.id == "save-kafka-btn":
            self.kafka_servers = self.query_one("#kafka-servers-input", Input).value.strip()
            self.kafka_user = self.query_one("#kafka-user-input", Input).value.strip()
            self.kafka_pass = self.query_one("#kafka-pass-input", Input).value.strip()
            self.step = 7
            self.update_step()
        elif event.button.id == "finish-btn":
            self.finish_setup()

    def update_step(self) -> None:
        content = self.query_one("#step-content", Vertical)
        content.remove_children()
        
        if self.step == 2:
            content.mount(
                Label("Step 1: Profile Configuration", classes="wizard-title"),
                Label("Choose your handle:", classes="wizard-step"),
                Input(placeholder="Username (e.g. alice)", id="username-input"),
                Input(placeholder="Display Name", id="display-name-input"),
                Button("SAVE_PROFILE", id="save-profile-btn")
            )
        elif self.step == 3:
            content.mount(
                Label("Step 2: Identity Generation", classes="wizard-title"),
                Label(f"Greetings, {self.display_name}.", classes="wizard-step"),
                Label("Generating 2048-bit RSA Key Pair...", classes="wizard-step"),
                Button("GENERATE_KEYS", id="gen-keys-btn")
            )
        elif self.step == 4:
            content.mount(
                Label("Step 3: PostgreSQL Configuration", classes="wizard-title"),
                Label("Enter Aiven PostgreSQL URI:", classes="wizard-step"),
                Input(placeholder="postgres://avnadmin:pass@host:port/defaultdb?sslmode=require", id="pg-uri-input"),
                Button("SAVE_POSTGRES", id="save-pg-btn")
            )
        elif self.step == 5:
            content.mount(
                Label("Step 4: Valkey Configuration", classes="wizard-title"),
                Label("Enter Aiven Valkey URI:", classes="wizard-step"),
                Input(placeholder="rediss://default:pass@host:port", id="valkey-uri-input"),
                Button("SAVE_VALKEY", id="save-valkey-btn")
            )
        elif self.step == 6:
            content.mount(
                Label("Step 5: Kafka Configuration", classes="wizard-title"),
                Label("Enter Aiven Kafka Bootstrap Servers:", classes="wizard-step"),
                Input(placeholder="host:port", id="kafka-servers-input"),
                Label("SASL Username:", classes="wizard-step"),
                Input(placeholder="avnadmin", value="avnadmin", id="kafka-user-input"),
                Label("SASL Password:", classes="wizard-step"),
                Input(placeholder="password", password=True, id="kafka-pass-input"),
                Button("SAVE_KAFKA", id="save-kafka-btn")
            )
        elif self.step == 7:
            content.mount(
                Label("Step 6: Uplink Confirmation", classes="wizard-title"),
                Label("Credentials Cached.", classes="wizard-step"),
                Label("Ready to establish secure communication link.", classes="wizard-step"),
                Button("ESTABLISH_LINK", id="finish-btn")
            )

    def save_profile(self) -> None:
        self.username = self.query_one("#username-input", Input).value.strip() or "guest"
        self.display_name = self.query_one("#display-name-input", Input).value.strip() or self.username
        
        self.step = 3
        self.update_step()

    async def generate_identity(self) -> None:
        # Generate keys
        private_pem, public_pem = generate_key_pair()
        
        # Save to files
        save_key_to_file(private_pem, self.app.settings.user_config.private_key_path)
        save_key_to_file(public_pem, self.app.settings.user_config.private_key_path + ".pub")
        
        # Save profile to DB
        # Note: We can't save to DB yet if PG is not configured
        # The original code assumed DB was already there.
        # We'll defer DB save until PG is configured or just notify.
        self.public_key_to_save = public_pem.decode()
        
        self.step = 4
        self.update_step()

    def finish_setup(self) -> None:
        """Save settings to .env and close wizard."""
        env_content = f"""# K-IRC Aiven Configuration
KIRC_USER_CONFIG__USERNAME={self.username}
KIRC_USER_CONFIG__DISPLAY_NAME={self.display_name}

KIRC_POSTGRES__URI={self.pg_uri}
KIRC_VALKEY__URI={self.valkey_uri}

KIRC_KAFKA__BOOTSTRAP_SERVERS={self.kafka_servers}
KIRC_KAFKA__SECURITY_PROTOCOL=SASL_SSL
KIRC_KAFKA__SASL_MECHANISM=SCRAM-SHA-256
KIRC_KAFKA__SASL_PLAIN_USERNAME={self.kafka_user}
KIRC_KAFKA__SASL_PLAIN_PASSWORD={self.kafka_pass}
KIRC_KAFKA__SSL_CAFILE=./certs/ca.pem
"""
        Path(".env").write_text(env_content)
        self.app.notify("Configuration saved to .env")
        # Now try to save profile if we have db_client
        # But db_client might not be initialized with new settings yet
        # For now, just exit. The user will restart.
        self.app.pop_screen()
