# Test Environment Setup Instructions

This setup creates a local simulation of the K-IRC network with:
- 2 Kafka Brokers (localhost:9092, localhost:9093)
- 2 Redis Instances (localhost:6379, localhost:6380)
- 1 PostgreSQL Instance (localhost:5432) with separate DBs for Alice and Bob.

## 1. Start Infrastructure
```bash
docker-compose -f docker-compose.test.yml up -d
```

## 2. Run Alice
Open a new terminal:
```bash
# Load Alice's env and run
export $(cat .env.alice | xargs)
uv run kirc
```

## 3. Run Bob
Open another terminal:
```bash
# Load Bob's env and run
export $(cat .env.bob | xargs)
uv run kirc
```

## 4. Connect and Chat
1. In both terminals, press `c` to connect.
2. Alice (or Bob) will claim leadership of `#NET_RUNNERS`.
3. Use the Invite flow (if implemented) or manually add each other as contacts in the DB to exchange keys.
   - Since the Invite flow relies on copy-pasting tokens, you can do that between the two windows.
4. Once connected as contacts, the Leader can press `r` to rotate keys and distribute them.
5. Chat!
