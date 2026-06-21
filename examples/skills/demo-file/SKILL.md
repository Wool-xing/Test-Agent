---
name: demo-file
version: 1.0.0
display_name: Demo File Check
description: Example skill — verify file existence, size, and content
permissions:
  network: none
  filesystem: read
  shell: none
  timeout: 10
tags: [file, demo, validation]
icon: "📄"
---

# Demo File Check

Verify that a file exists, has expected size, and optionally contains expected content.

```bash
tagent skill install examples/skills/demo-file
tagent "check if config.json exists and is not empty"
tagent "verify README.md contains the word 'Installation'"
```
