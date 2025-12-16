"""Setup Wizard for K-IRC."""

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Label, Static
from textual.reactive import reactive

from kirc.crypto import generate_key_pair, save_key_to_file
from kirc.tui.widgets import ChatInput


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
        elif event.button.id == "gen-keys-btn":
            self.generate_identity()
        elif event.button.id == "finish-btn":
            self.app.pop_screen()

    def update_step(self) -> None:
        content = self.query_one("#step-content", Vertical)
        content.remove_children()
        
        if self.step == 2:
            content.mount(
                Label("Step 1: Identity Generation", classes="wizard-title"),
                Label("Generating 2048-bit RSA Key Pair...", classes="wizard-step"),
                Button("GENERATE_KEYS", id="gen-keys-btn")
            )
        elif self.step == 3:
            content.mount(
                Label("Step 2: Uplink Configuration", classes="wizard-title"),
                Label("Identity Established.", classes="wizard-step"),
                Label("Please configure your Aiven services in .env", classes="wizard-step"),
                Button("ESTABLISH_LINK", id="finish-btn")
            )

    def generate_identity(self) -> None:
        # Generate keys
        private_pem, public_pem = generate_key_pair()
        
        # Save to files (in a real app, we'd ask for location or use a default secure dir)
        save_key_to_file(private_pem, "id_rsa.pem")
        save_key_to_file(public_pem, "id_rsa.pub")
        
        self.step = 3
        self.update_step()
