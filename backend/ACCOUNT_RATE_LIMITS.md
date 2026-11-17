# Account rate limits

Login requests are limited to 5 per username and client, 30 per username across
clients, and 60 per client across usernames in each five-minute window. Signup
requests are limited to 10 per client in the same window. The limits count all
requests, including successful logins and duplicate signup attempts. A rejected
request returns HTTP 429 with `Retry-After` and a generic message. Windows expire
automatically; old counters are removed as requests arrive.

Counters are stored in the application database, so backend workers must use the
same database file. The client address comes from ASGI's `request.client`, never
directly from a forwarded header. When running behind a reverse proxy, configure
Uvicorn's `--proxy-headers` and `--forwarded-allow-ips` with only the trusted
proxy addresses. Otherwise all traffic through the proxy shares its address and
one client can exhaust the proxy's limit for five minutes.
