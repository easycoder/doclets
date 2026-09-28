# Fenced to its own broker account — one restart left for you

The Doclets page no longer hands out the broker's master account. It uses a `doclets` account now, fenced by ACL to exactly what Doclets needs:

- `a8:41:f4:d3:19:dd` — the service topic
- `doclets/reply/#` — the reader reply namespace

That second line is why the client changed. The reply topics used to be `Doclets-<random>`, and **an ACL cannot express a name prefix**: MQTT wildcards match whole levels, so `Doclets-+` is not valid (mosquitto rejects the whole file for it) and `Doclets-123456` needs the reply topics to live under a namespace instead. Hence `doclets/reply/<random>`, and hence the redeploy.

## Done

- **Broker**: the `doclets` account, and an ACL limiting it to those two topics. Validated on a scratch broker on a spare port before it went near the live one — worth doing, because a reload that fails to parse the ACL leaves the broker running with **no ACL at all**. I found that out the hard way, briefly, this afternoon.
- **The ACL also fixes something my first version broke**: `#` does not cover `$SYS` topics, so `rbr` lost the right to publish its bridge state (`$SYS/broker/connection/<id>/state`). It now has an explicit `$SYS/#` grant.
- **Client**: the reply topic renamed, doc blocks refreshed (`asdoc-check` 0/0), and `doclets.allspeak` redeployed — readers pick it up on reload, the same cache-buster that always applied.
- **Credentials**: `doclets.eclecity.net.txt` on the host switched to the new account (old file backed up beside it).
- **Verified**: the new account talks to the live service over wss/443 and receives its reply; and it is refused in the chat namespace.

## One thing left, and only you can do it

The service reads its credentials from the endpoint at startup, so it is still using the old account in memory until it restarts:

    sudo systemctl restart doclets

Until then everything works — it is just that the service process still holds the master credentials rather than the fenced ones. The publicly exposed half (the page) is already switched.

## Still outstanding from the audit

The master password is committed to the public `easycoder/rbr` repository, in five files of its current tree. Rotating it is the only real remedy — removing the files does not unpublish them — and it needs the RBR gateways updated at the same time, which is why it wants a deliberate pass rather than an afterthought.

## After that restart, reload any open Doclets pages

A page loaded before today's deploy is still asking for replies on the old `Doclets-<random>` topic, which the service (on the fenced account) can no longer publish to. Reloading the page picks up the new client — the script is fetched with a cache-buster, so a plain refresh is enough. Nothing breaks in between: while the service is still on the old account, replies to old names still work.
