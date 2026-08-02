---
title: "AI writes the code, humans review it — review is the coming skill"
published: false
description: "AI writes the code; humans review it. Recognition is easier than creation when the language is close to human language."
tags: [ai, coding, allspeak, lowcode]
---

Most articles on dev.to are about coding. This one is not. It is about the entire process of producing software in a world where AI does the coding and humans do the reviewing. That reversal is the whole point, and it has consequences for which skills matter.

## Recognition is easier than writing

There is no imperative for you to learn to write AllSpeak — you will never be asked to. Your job is to recognise code presented in the language. Recognition is a far simpler task than writing, and it becomes more and more effective the closer the language approaches that of human languages.

When you read a book on an unfamiliar subject, you consult a dictionary for the terms you don't know. Here the dictionary is an AI agent: an unfamiliar construct in the code is just a question away. "What is this block doing?" — and the agent explains it in plain language. Recognition, assisted by the dictionary, is enough to review what was written.

## Why programmers resist

This is hard for most programmers to comprehend, so used are they to regarding code as something they own themselves. "Reading the code" has always been unpopular, and mostly for good reason. That has the potential to change dramatically if AI writes code in a more accessible language.

I deliberately avoid the word "programmer" here, because in this scenario programmers, as such, effectively cease to exist. The people who remain are engineers — and the skill they need is judgment, not syntax.

## Review is the coming skill

It is widely accepted that there are fewer and fewer opportunities to gain coding expertise. Review is the coming skill, and if toolchains remain as they are now, there will be few who possess it effectively.

The only alternative to accepting — and embracing — the need for more accessible forms of language is to abdicate the entire process of software generation. That is a dangerous path, and one humans must avoid if they are to retain relevance in the world of tomorrow.

## AllSpeak is a first step, not a destination

AllSpeak is not a final destination; it is a first step towards a new paradigm, one that must gradually become familiar to engineers. The closer the language comes to a human language, the more effective recognition becomes, and the less the code feels like someone else's possession.

## The illustration: Doclets

The rest of this article is about Doclets, a working example of the pattern. Doclets was neither hand-coded nor vibe-coded: it was produced through exactly the process described above — AI writes, human reviews, block by block. It is an example of a pattern — maybe the only pattern that acknowledges the gap between coding and review and points the way to bridging it.

Doclets is a central, searchable repository of Markdown documents ("doclets"), organised into topics and years, read and edited in a browser on any device. A small server process owns the documents and talks to the browser over MQTT.

![Screenshot: the Doclets reader showing the topic list and query bar](screenshot-reader.png)

Plain search is a substring match over every doclet's title and content. A second way to search uses a local language model: tick "LLM query" and ask questions like *"list the main topics covered by the doclets in the Linux topic"* — a short prose answer comes back, derived from the collection itself, running entirely on your own machine.

![Screenshot: an LLM query returning a concise answer in the Doclets reader](screenshot-llm.png)

For small teams, each topic has an owner and a visibility: public topics are readable by anyone, private topics only by the owner and named readers, with separate grants for creating, modifying and deleting, and a simple activity log of who did what and when.

The construction is deliberately unremarkable — one language for the whole stack (the browser client and the server are both AllSpeak), screens defined declaratively, MQTT for request/reply, and the one heavy component (searching, securing, and the LLM integration) consigned to a plugin with a small vocabulary of its own.

This is a general picture, not a specification — the details live in the repository.

## Ask your agent

If you want the detail, point your AI agent at the [Doclets repository](https://github.com/easycoder/doclets) and ask for a synopsis, a full technical breakdown, or anything in between. Every section of the code carries a doc block explaining *why* it exists, so the agent — and you — can read it block by block. Recognition, assisted by the dictionary, all the way down.

Code was never the product; the product is what the code does. If AI writes the code and we review it well, software production becomes a skill of judgment rather than of syntax. That is a change worth embracing.

<!--
Editor notes:
- Replace the two screenshot placeholders with real images (dev.to: upload in the editor and use the generated URLs).
- Keep the description under ~150 characters for previews.
- Tags: max 4, lowercase, no spaces (currently: ai, coding, allspeak, lowcode).
- Optional front matter: canonical_url, cover_image, series.
- Central message: AI writes / human reviews; doclets is the peripheral illustration; end with the "ask your agent" invitation.
-->
