# Voice Agent Booking Prototype

Minimal, single‑file prototype demonstrates simple usage and free‑form interactions with a voice AI agent for booking appointments at various dental clinics.

The code is structured to be easily used as a reference for a more complete solution.

Watch the [video](https://youtu.be/QJi7tqnG7oc) example.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Environment](#environment)
- [Installation](#installation)
- [Usage](#usage)

## Prerequisites

- Docker \>= v27.5.1
- Docker Compose \>= v2.38.2
- Python 3.10+

## Environment

To run this project you will need to provide your own .env file containing OpenAI API key, as well as following variables:
```bash
OPENAI_API_KEY=<YourOpenAIAPIKey>
TRANSIENT_DATA_DIR=/vab_db/
JSON_DB_FILE=bookings.json
```

## Installation

### Clone and Build

Clone the repo build the docker images

```bash
git clone https://github.com/your-org/your-project.git
cd your-project
docker-compose build
```
### Run

Start the stack in detached mode:

```bash
docker compose up -d

```

Then navigate to:

```bash
http://localhost:3000

```

### Logs

To find the container logs:

```bash
docker compose logs vab_app

```
### Stop

When you’re done, stop and remove containers, networks, and volumes:

```bash
docker compose down
```
## Usage

Watch the [video](https://youtu.be/QJi7tqnG7oc) for an example.

Go to http://localhost:3000 in your browser to open the Gradio web UI.

Once generated, you’ll find `booking.db` and all session records in the mounted `db/` directory at the root of this repository.

