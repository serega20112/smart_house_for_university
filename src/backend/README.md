# Smart Home Backend

Backend of a multi-user smart home platform.

One process and one interface serve every account: users authorize, the backend
resolves who they are from the session token, and every query is scoped to that
account. The stored data (devices, automation, scenarios, preferences, dashboard
layout, paired boards) is what makes each user see their own projection of the
same application.

## Layers

```text
presentation   HTTP, WebSocket, Telegram, static interface
infrastructure SQLAlchemy, board transport, tokens, notification channels
application    use cases, ports, engines
domain         entities, value objects, policies
```

`lint-imports` enforces the direction: the domain knows nothing about the layers
above it.

## Running

```bash
pip install -e ".[dev]"
uvicorn smart_home_backend.main:app --reload
```

The database, the board WebSocket port and the authorization secret are read from
the environment; every value has a default, see `.env`.

## Board pairing

A board dials in to the backend as a WebSocket client and announces itself with
the pairing key created in the web interface. The backend resolves that key into
an account and from then on every frame of that socket updates the state of that
account only, so one server can serve any number of homes.

## Checks

```bash
ruff check src tests
pytest
lint-imports
```
