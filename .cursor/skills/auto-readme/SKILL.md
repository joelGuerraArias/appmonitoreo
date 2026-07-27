---
name: auto-readme
description: Automatically logs code changes into README.md whenever files are modified, functions are added, or code is updated.
---

# Auto README Logger

## Behavior

This skill runs automatically whenever code changes are detected in the project.

---

## Activation Message

When starting, say:

Auto README Logger activado. Detectando y registrando cambios automáticamente...

---

## When to use

Use this skill automatically when:
- Any file is modified
- New functions are added
- Code is updated
- New files are created
- The user edits or generates code

---

## Instructions

1. Detect recent code changes in the project context

2. Identify the type of change:

- FEAT → new function or feature
- MOD → modified function or logic
- FILE → new file created
- REFACTOR → internal improvement without changing behavior

3. If README.md does not exist:

Create it with:

# Proyecto

## 📌 Cambios automáticos

---

4. Generate a new log entry using this format:

- [YYYY-MM-DD HH:mm] TYPE: short title
  - Clear, natural human description of the change

---

5. Append the new entry to README.md

---

## Rules

- DO NOT delete previous logs
- DO NOT duplicate entries
- DO NOT write robotic or generic text
- Keep descriptions natural and concise
- Always append, never overwrite

---

## Examples

- [2026-03-30 16:10] FEAT: createUser()
  - Added user creation function with input validation

- [2026-03-30 16:15] MOD: login()
  - Improved authentication logic and error handling

- [2026-03-30 16:20] FILE: auth.py
  - New authentication module added