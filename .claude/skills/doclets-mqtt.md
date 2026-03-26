---
name: doclets-mqtt
description: MQTT credentials and connectivity setup for the doclets project (production vs localhost)
---

## MQTT Credentials

**Production:** The client fetches credentials from `https://doclets.eclecity.net/credentials.php`, which returns a JSON object with four fields: `broker`, `username`, `password`, `mac`.

**Localhost:** CORS blocks the credentials request. On first load the client prompts for all four values and stores them in `localStorage` under:
- `dev-broker`
- `dev-username`
- `dev-password`
- `dev-mac`

To reset them, remove those four keys from `localStorage`.
