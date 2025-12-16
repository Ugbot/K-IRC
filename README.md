# K-IRC: Kafka Relay Chat

A Python-based TUI chat and social media tool built on the Actor Model pattern, using Apache Kafka as the message backbone and WebRTC for real-time communication.

## Concept

K-IRC treats each user as an **actor** with their own infrastructure:

```
┌─────────────────────────────────────────────────────────────────┐
│                        YOUR K-IRC ACTOR                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌─────────────┐         ┌─────────────────────────────────┐   │
│   │             │         │         KAFKA (Mailbox)         │   │
│   │   K-IRC     │◄───────►│  ┌─────────┐    ┌─────────┐     │   │
│   │   TUI App   │         │  │ data-in │    │ data-out│     │   │
│   │             │         │  └─────────┘    └─────────┘     │   │
│   └─────────────┘         │  ┌─────────┐    ┌─────────┐     │   │
│         │                 │  │ rpc-in  │    │ rpc-out │     │   │
│         │                 │  └─────────┘    └─────────┘     │   │
│         │                 └─────────────────────────────────┘   │
│         │                                                       │
│         │                 ┌─────────────────────────────────┐   │
│         ├────────────────►│     PostgreSQL (Config Store)   │   │
│         │                 │  - User profiles                │   │
│         │                 │  - Settings                     │   │
│         │                 │  - Contact list                 │   │
│         │                 └─────────────────────────────────┘   │
│         │                                                       │
│         │                 ┌─────────────────────────────────┐   │
│         └────────────────►│     Valkey (Pub/Sub + Cache)    │   │
│                           │  - Presence notifications       │   │
│                           │  - Typing indicators            │   │
│                           │  - Session cache                │   │
│                           └─────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

Each user:
- Forks this repo
- Sets up their own free Aiven Kafka + PostgreSQL + Valkey
- Runs their own K-IRC instance
- Communicates with other actors via Kafka topics

## Actor Model via Kafka

Kafka serves as the actor's **mailbox**:

| Topic | Purpose |
|-------|---------|
| `data-in` | Inbox - incoming messages from other actors |
| `data-out` | Outbox - messages you send to others |
| `rpc-in` | Incoming RPC requests (presence, typing, etc.) |
| `rpc-out` | Outgoing RPC responses |

## User Profiles

- **Public Profile**: Shared endpoint info with strict quotas for discovery
- **Private Profile**: Local configuration and preferences

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- Terraform 1.0+
- Free [Aiven](https://aiven.io) account

## Quick Start

### 1. Fork and Clone

```bash
git clone https://github.com/YOUR_USERNAME/K-IRC.git
cd K-IRC
```

### 2. Create Aiven Account

1. Sign up at [console.aiven.io](https://console.aiven.io)
2. Create a new project (or use default)
3. Generate an API token: Profile → Tokens → Generate Token

### 3. Set Up Kafka (Console - Required)

The Kafka free tier must be created via the Aiven Console (no Terraform support yet):

1. Go to [console.aiven.io](https://console.aiven.io)
2. Click **Create Service** → **Apache Kafka**
3. Select **Free** plan
4. Choose available region (limited options on free tier)
5. Name it `kirc-kafka` (or your preference)
6. Click **Create Service**

Once created, add the 4 required topics:

1. Go to your Kafka service → **Topics**
2. Create each topic with **2 partitions**:
   - `data-in`
   - `data-out`
   - `rpc-in`
   - `rpc-out`

Download credentials:
1. Go to **Overview** → **Connection information**
2. Download the CA certificate (`ca.pem`)
3. Note the Service URI, username, and password

### 4. Set Up PostgreSQL + Valkey (Terraform)

```bash
cd terraform

# Copy example vars and edit with your values
cp terraform.tfvars.example terraform.tfvars

# Edit terraform.tfvars with your Aiven API token and project name
# Get token from: https://console.aiven.io/profile/tokens

# Initialize and apply
terraform init
terraform plan
terraform apply
```

### 5. Get Connection Details

After Terraform completes:

```bash
# View PostgreSQL connection info
terraform output pg_host
terraform output pg_port
terraform output pg_database

# View Valkey connection info
terraform output valkey_host
terraform output valkey_port

# View sensitive values
terraform output -raw pg_service_uri
terraform output -raw pg_password
terraform output -raw pg_ca_cert > pg_ca.pem

terraform output -raw valkey_service_uri
terraform output -raw valkey_password
```

### 6. Configure K-IRC

```bash
cd ..
cp .env.example .env
# Edit .env with your Kafka and PostgreSQL connection details
```

### 7. Run K-IRC

```bash
# Install uv if you haven't already
# curl -LsSf https://astral.sh/uv/install.sh | sh

# Sync dependencies
uv sync

# Run the TUI
uv run kirc
```

## Free Tier Limitations

### Kafka Free Tier
- Max **5 topics** (we use 4)
- **2 partitions** per topic
- **125 KiB/s** ingress + **125 KiB/s** egress
- Auto-shutdown after **24 hours** of inactivity
- One free Kafka per organization
- No Kafka Connect or MirrorMaker

### PostgreSQL Free Tier
- **1 GB** storage
- 1 CPU, 1 GB RAM
- Max **20 connections**
- No connection pooling
- One free PG per organization

### Valkey Free Tier
- **512 MB** memory (maxmemory set to 50%)
- 1 CPU, 1 GB RAM
- Redis-compatible commands
- Pub/Sub support
- One free Valkey per organization

**Note:** Free tier services cannot choose cloud provider or region - Aiven assigns automatically.

## Project Structure

```
K-IRC/
├── terraform/              # Infrastructure as Code
│   ├── main.tf             # Aiven provider config
│   ├── variables.tf        # Input variables
│   ├── postgresql.tf       # PostgreSQL free tier
│   ├── valkey.tf           # Valkey free tier
│   ├── outputs.tf          # Connection outputs
│   └── terraform.tfvars.example
├── src/kirc/               # Python application
│   ├── __init__.py
│   ├── __main__.py         # Entry point
│   ├── app.py              # Main Textual App
│   ├── config.py           # Settings management
│   ├── kirc.tcss           # TUI stylesheet
│   ├── tui/                # TUI components
│   ├── kafka/              # Kafka producer/consumer
│   ├── db/                 # PostgreSQL models
│   └── cache/              # Valkey/Redis client
├── tests/                  # Test suite
├── .env.example
├── pyproject.toml          # Project configuration
└── README.md
```

## Architecture & Data Flow

K-IRC uses a hybrid P2P/Client-Server model where nodes (users) communicate via a shared Kafka cluster and Redis instance, but manage their own identity and encryption keys locally.

### 1. Identity & Discovery (The "Handshake")
Before two users can chat securely, they must exchange credentials and public keys.
1.  **Out-of-Band**: Alice shares her **Public Key** with Bob (e.g., via email/DM).
2.  **Invite Generation**: Bob uses Alice's Public Key to encrypt a bundle containing his **Identity** (Username, Public Key) and **Service Config** (Kafka/Redis endpoints).
3.  **Acceptance**: Alice receives the encrypted bundle, decrypts it with her Private Key, and adds Bob to her local **Contacts Database**.
4.  **Mutual Link**: Alice repeats the process for Bob, ensuring both have each other's Public Keys.

### 2. Channel Leadership (Redis Signaling)
Channels are ephemeral and leader-moderated.
1.  **Claiming Leadership**: When Alice joins `#NET_RUNNERS`, she checks Redis for a leader. If none exists, she registers herself as **Leader** (`channel:NET_RUNNERS:leader`).
2.  **Membership**: Users joining the channel add themselves to the Redis Set `channel:NET_RUNNERS:members`.
3.  **Events**: The Leader publishes events (Join/Leave/Kick) to `channel:NET_RUNNERS:events` so all connected clients can update their UI.

### 3. Secure Messaging (Kafka + Symmetric Encryption)
Messages are encrypted with a symmetric key (Fernet) specific to the channel and key version.
1.  **Key Generation**: The Leader generates a random Symmetric Key and a unique `KeyID`.
2.  **Distribution (RPC)**: The Leader iterates through the **Channel Members** list. For each member (e.g., Bob), the Leader:
    *   Encrypts the Symmetric Key with Bob's **Public Key**.
    *   Sends it via Kafka to `rpc-in-bob` with type `channel_key_update`.
3.  **Encryption**: When Alice sends a message:
    *   She encrypts the content with the current Symmetric Key.
    *   She attaches the `KeyID` to the message payload.
    *   She sends the message to the Leader's Inbox (`inbox-alice` -> Leader).
4.  **Relay**: The Leader receives the message, verifies it, and **re-broadcasts** it to the channel's output topic (`out-alice`).
5.  **Decryption**: Bob receives the message from `out-alice`, looks up the key by `KeyID`, and decrypts the content.

### 4. Key Rotation (The "Kick")
To remove a user (e.g., Eve) from the channel:
1.  The Leader generates a **New Symmetric Key** and `NewKeyID`.
2.  The Leader distributes this new key via RPC to all members **except Eve**.
3.  The Leader signals "Rotation" via Redis.
4.  Future messages are encrypted with the New Key. Eve, lacking this key, receives only encrypted gibberish.

### 5. Redis (Valkey) Data Structure
Redis is used as a shared state cache and control plane.

**Keys:**
- `channel:{name}:leader` (String): Username of the current leader. TTL 30s (heartbeat).
- `channel:{name}:members` (Set): Set of usernames currently in the channel.
- `channel:{name}:status` (Hash): Metadata about the channel (topic, mode, etc).
- `rotation:{name}` (Pub/Sub): Signal channel for key rotation events.
- `channel:{name}:events` (Pub/Sub): Event stream for Join/Leave/Kick notifications.

### 6. PostgreSQL Schema
Each user maintains their own local PostgreSQL database for persistence.

**Tables:**
- `contacts`: Stores known peers (Username, Public Key, Kafka Bootstrap Servers).
- `messages`: Stores chat history (Sender, Content, Timestamp, Channel, KeyID).
- `credentials`: Stores encrypted service credentials for other nodes.

## Development Roadmap

- [x] Infrastructure setup (Terraform + Console guide)
- [x] TUI framework (Textual)
- [x] Kafka producer/consumer client (aiokafka)
- [x] PostgreSQL schema and models (asyncpg)
- [x] Valkey pub/sub client (redis-py async)
- [x] User profile management
- [x] Message sending/receiving
- [x] Secure Channel Leadership & Key Rotation
- [x] P2P Invite System
- [ ] WebRTC signaling via Kafka
- [ ] File Transfer

## License

MIT
