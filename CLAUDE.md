Read the following primer prompts:

https://easycoder.github.io/agent-primer-python.md
https://easycoder.github.io/agent-primer-js.md

The project is a central file storage system and reader for Markdown documents. Communication between the two is done with MQTT.

The server is docletServer.ecs. This is written in the Python dialect of EasyCoder.

The client is doclets.ecs. It's a web application written in the JS dialect of EasyCoder and uses Webson for all DOM rendering. It runs on any smartphone. The entry point is index.html, which contains a loader to start up the main script.

Tasks will be provided as the need arises.
