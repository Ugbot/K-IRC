"""Credential Exchange Screens for K-IRC."""

import base64
import json
from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Label, Static, TextArea
from textual.reactive import reactive

from kirc.crypto import encrypt_message, decrypt_message, load_key_from_file


class ShowIdentityScreen(Screen):
    """Screen to display own identity (Public Key)."""

    CSS = """
    ShowIdentityScreen {
        align: center middle;
        background: $background;
    }

    #identity-container {
        width: 80;
        height: auto;
        border: heavy $neon-pink;
        padding: 1 2;
        background: $surface;
    }

    .title {
        text-style: bold;
        color: $neon-pink;
        text-align: center;
        margin-bottom: 1;
    }

    .label {
        color: $neon-cyan;
        margin-top: 1;
    }

    TextArea {
        height: 10;
        background: $custom-panel;
        color: $text-main;
        border: solid $text-dim;
    }

    Button {
        width: 100%;
        margin-top: 1;
        background: $custom-panel;
        color: $neon-pink;
        border: heavy $neon-pink;
    }
    
    Button:hover {
        background: $neon-pink;
        color: $background;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="identity-container"):
            yield Label("MY_DIGITAL_IDENTITY", classes="title")
            
            yield Label("PUBLIC_KEY (SHARE_THIS)", classes="label")
            yield TextArea(id="pub-key-display", read_only=True)
            
            yield Button("RETURN_TO_CONSOLE", id="back-btn")
        yield Footer()

    def on_mount(self) -> None:
        try:
            with open("id_rsa.pub", "r") as f:
                pub_key = f.read()
                self.query_one("#pub-key-display", TextArea).text = pub_key
        except Exception as e:
            self.query_one("#pub-key-display", TextArea).text = f"ERROR: Could not load public key: {e}"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back-btn":
            self.app.pop_screen()


class InviteGenScreen(Screen):
    """Screen to generate an invite (Encrypted Bundle) for a peer."""

    CSS = """
    InviteGenScreen {
        align: center middle;
        background: $background;
    }

    #invite-container {
        width: 80;
        height: auto;
        border: heavy $neon-cyan;
        padding: 1 2;
        background: $surface;
    }

    .title {
        text-style: bold;
        color: $neon-pink;
        text-align: center;
        margin-bottom: 1;
    }

    .label {
        color: $neon-cyan;
        margin-top: 1;
    }

    TextArea {
        height: 10;
        background: $custom-panel;
        color: $text-main;
        border: solid $text-dim;
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
        yield Header()
        with Container(id="invite-container"):
            yield Label("GENERATE_NEURAL_LINK_INVITE", classes="title")
            
            yield Label("1. INPUT_PEER_PUBLIC_KEY", classes="label")
            yield TextArea(id="pub-key-input", language="text")
            
            yield Button("ENCRYPT_PAYLOAD", id="encrypt-btn")
            
            yield Label("2. TRANSMIT_THIS_BUNDLE", classes="label")
            yield TextArea(id="bundle-output", read_only=True)
            
            yield Button("RETURN_TO_CONSOLE", id="back-btn", variant="error")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back-btn":
            self.app.pop_screen()
        elif event.button.id == "encrypt-btn":
            self.generate_bundle()

    def generate_bundle(self) -> None:
        pub_key_str = self.query_one("#pub-key-input", TextArea).text
        if not pub_key_str:
            self.app.notify("Error: Peer Public Key required", severity="error")
            return

        try:
            # Fetch actual credentials and identity
            settings = self.app.settings
            
            # We need our own public key to send to them
            my_public_key = None
            try:
                # Assuming public key is stored in settings or loaded from file
                # For now, let's try to load it from the default location if not in settings
                # In a real app, this should be in memory
                with open("id_rsa.pub", "r") as f:
                    my_public_key = f.read()
            except Exception:
                pass

            payload = {
                "sender": {
                    "username": settings.user_config.username,
                    "display_name": settings.user_config.display_name,
                    "public_key": my_public_key,
                    "kafka_bootstrap_servers": settings.kafka.bootstrap_servers
                },
                "services": {
                    "kafka": {
                        "bootstrap_servers": settings.kafka.bootstrap_servers,
                        "topics": [settings.kafka.topic_data_in, settings.kafka.topic_data_out]
                    },
                    "valkey": {
                        "uri": settings.valkey.uri
                    }
                }
            }
            payload_bytes = json.dumps(payload).encode("utf-8")
            
            # Encrypt
            encrypted = encrypt_message(pub_key_str.encode("utf-8"), payload_bytes)
            bundle = base64.b64encode(encrypted).decode("utf-8")
            
            self.query_one("#bundle-output", TextArea).text = bundle
            self.app.notify("Invite bundle generated successfully")
        except Exception as e:
            self.query_one("#bundle-output", TextArea).text = f"ERROR: {str(e)}"


class InviteAcceptScreen(Screen):
    """Screen to accept an invite (Decrypt Bundle)."""

    CSS = """
    InviteAcceptScreen {
        align: center middle;
        background: $background;
    }
    
    #accept-container {
        width: 80;
        height: auto;
        border: heavy $neon-green;
        padding: 1 2;
        background: $surface;
    }
    
    .title {
        text-style: bold;
        color: $neon-green;
        text-align: center;
        margin-bottom: 1;
    }
    
    .label {
        color: $neon-cyan;
        margin-top: 1;
    }
    
    TextArea {
        height: 10;
        background: $custom-panel;
        color: $text-main;
        border: solid $text-dim;
    }
    
    Button {
        width: 100%;
        margin-top: 1;
        background: $custom-panel;
        color: $neon-green;
        border: heavy $neon-green;
    }
    
    Button:hover {
        background: $neon-green;
        color: $background;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="accept-container"):
            yield Label("ACCEPT_NEURAL_LINK_INVITE", classes="title")
            
            yield Label("INPUT_ENCRYPTED_BUNDLE", classes="label")
            yield TextArea(id="bundle-input")
            
            yield Button("DECRYPT_AND_ADD_CONTACT", id="decrypt-btn")
            yield Button("RETURN_TO_CONSOLE", id="back-btn", variant="error")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back-btn":
            self.app.pop_screen()
        elif event.button.id == "decrypt-btn":
            self.process_bundle()

    async def process_bundle(self) -> None:
        bundle_str = self.query_one("#bundle-input", TextArea).text
        if not bundle_str:
            return

        try:
            # Load my private key
            if not self.app.private_key:
                self.app.notify("Error: No private key loaded", severity="error")
                return
            
            # Decode and Decrypt
            encrypted_bytes = base64.b64decode(bundle_str)
            decrypted_bytes = decrypt_message(self.app.private_key, encrypted_bytes)
            
            payload = json.loads(decrypted_bytes.decode("utf-8"))
            
            sender_info = payload.get("sender", {})
            username = sender_info.get("username")
            public_key = sender_info.get("public_key")
            bootstrap_servers = sender_info.get("kafka_bootstrap_servers")
            
            if username and public_key:
                # Save Contact to DB
                from kirc.db.models import Contact
                from uuid import uuid4
                from datetime import datetime, timezone
                
                contact = Contact(
                    id=uuid4(),
                    username=username,
                    display_name=sender_info.get("display_name", username),
                    kafka_bootstrap_servers=bootstrap_servers or "unknown",
                    public_key=public_key,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
                
                await self.app.db_client.save_contact(contact)
                self.app.notify(f"SUCCESS: Added contact {username}")
                self.app.pop_screen()
            else:
                 self.app.notify("Invalid bundle: Missing sender info", severity="error")
            
        except Exception as e:
            self.app.notify(f"DECRYPTION FAILED: {str(e)}", severity="error")
