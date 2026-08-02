---
title: "From documentation chaos to a searchable document server for small teams"
published: false
description: "A personal documentation mess — emails, Joplin, WhatsApp, dev.to posts — became Doclets: a full-stack AllSpeak app with content search, local-LLM queries, and per-topic access control."
tags: [allspeak, documentation, lowcode, programming]
---

A while back I wrote that I produce a lot of documentation but had no strategy
for organising it. Emails, web pages, Markdown notes in Joplin, WhatsApp
messages, dev.to posts of my own — it was a largely unsearchable mass of
information. Every fact I needed lived somewhere; none of it was findable.

Doclets started as an AllSpeak coding exercise. It became the tool that
brought order to that chaos — and, six months on, it has quietly turned into
something a small team could genuinely use.

## What Doclets is

Doclets is a central, searchable repository of Markdown documents ("doclets"),
organised into topics and years. You read and edit doclets in a browser on any
device; a small server process owns the documents and talks to the browser
over MQTT.

![Screenshot: the Doclets reader showing the topic list and query bar](screenshot-reader.png)

The two things that make it more than a notes folder are *finding* and
*sharing*.

## Finding things

Plain search is a simple substring match over every doclet's title and
content — nothing clever, but it works, and it already beat the alternative
(not being able to find things at all).

More recently I added a second way to search: a local language model. Tick
"LLM query" and you can ask questions like *"list the main topics covered by
the doclets in the Linux topic"* and get a short prose answer derived from the
collection's subjects, or *"find the doclets that include a proposed letter of
introduction"* and get the matching documents back. The model runs on your own
machine via Ollama — no cloud, no per-query cost — and every doclet is indexed
by a small embedding model, so searching doesn't mean reading the whole
database on each query.

![Screenshot: an LLM query returning a concise answer](screenshot-llm.png)

## Sharing with a small team

None of the tools that held my scattered notes offered the same ease of use —
and few could operate across the internet. Doclets is a central repository,
so the same collection is reachable from any browser, anywhere.

If you want to share that repository with colleagues, each topic can have an
owner and a visibility:

- **public** topics are readable by anyone with the link
- **private** topics are readable only by the owner and named readers
- creating/modifying is controlled by per-user grants, deleting by its own
  separate grant
- a simple activity log records who did what, and when

Identity is a token phrase — nothing to install, nothing to configure beyond
a small JSON file of permissions.

![Screenshot: the per-topic access control file](screenshot-acl.png)

## Why the construction matters

Doclets is also a good illustration of building a real application in
AllSpeak, and the way it is put together is one of the reasons it stayed
maintainable:

- **One language, full stack.** The browser client (`doclets.as`) and the
  server (`docletServer.as`) are both AllSpeak. One person can understand and
  change the entire system — UI, messaging, backend — without a conventional
  web framework or a second client language.
- **Declarative screens.** The UI is defined as Webson JSON, not hand-written
  DOM code — easy to read, easy for AI tools to generate.
- **MQTT instead of REST.** The browser and server talk over MQTT
  request/reply, which works naturally across the internet and on phones.
- **A clear plugin boundary.** The one genuinely heavy part — managing,
  searching and securing the document collection, plus the LLM integration —
  lives in a small Python plugin that exposes simple AllSpeak commands like
  `doclets query` and `doclets topics`. The scripting language stays readable;
  the native code stays isolated.
- **Features that arrive as additions, not rewrites.** Semantic LLM search and
  per-topic access control were bolted on over time without disturbing the
  original design — a sign the structure is doing its job.

Because AllSpeak separates language from logic, the same application could be
presented in French, Arabic or any other language via a language pack — a
property that also happens to be at the heart of why AllSpeak exists.

## Running it

The server is a single Python process (the `allspeak` runtime) plus an MQTT
broker; the client is static files on any web host. If you want the LLM
features, you add Ollama with a small model — again, all local.

![Screenshot: the doclets server console showing MQTT connect and an LLM query](screenshot-server.png)

Six months ago my documentation was a scattered mess. Today I can find any of
it in seconds, and I can share the collection with people who need it without
giving them the mess. If you have the same problem, Doclets is a good place to
start — and if you are curious about AllSpeak, it is a working example of what
the platform can do.

<!--
Editor notes:
- Replace the four screenshot placeholders with real images (dev.to: upload in
  the editor and use the generated URLs, or commit images and set cover_image).
- Keep the description under ~150 characters for previews.
- Tags: max 4, lowercase, no spaces (currently: allspeak, documentation,
  lowcode, programming).
- Optional front matter: canonical_url, cover_image, series.
-->
