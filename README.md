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
# Install dependencies
pip install -r requirements.txt

# Run the TUI
python -m kirc
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
├── terraform/           # Infrastructure as Code
│   ├── main.tf          # Aiven provider config
│   ├── variables.tf     # Input variables
│   ├── postgresql.tf    # PostgreSQL free tier
│   ├── valkey.tf        # Valkey free tier
│   ├── outputs.tf       # Connection outputs
│   └── terraform.tfvars.example
├── kirc/                # Python application (TBD)
│   ├── __main__.py
│   ├── tui/             # Terminal UI
│   ├── kafka/           # Kafka producer/consumer
│   ├── db/              # PostgreSQL models
│   ├── cache/           # Valkey/Redis client
│   └── webrtc/          # WebRTC signaling
├── .env.example
├── requirements.txt
└── README.md
```

## Development Roadmap

- [x] Infrastructure setup (Terraform + Console guide)
- [ ] Kafka producer/consumer client
- [ ] PostgreSQL schema and models
- [ ] TUI framework (Textual/Rich)
- [ ] User profile management
- [ ] Message sending/receiving
- [ ] WebRTC signaling via Kafka
- [ ] Presence and typing indicators
- [ ] Contact discovery

## License

MIT
