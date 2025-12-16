#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE kirc_alice;
    CREATE DATABASE kirc_bob;
    GRANT ALL PRIVILEGES ON DATABASE kirc_alice TO admin;
    GRANT ALL PRIVILEGES ON DATABASE kirc_bob TO admin;
EOSQL
