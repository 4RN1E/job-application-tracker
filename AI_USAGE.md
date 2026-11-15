# AI Usage Documentation

> **Draft started during the build. Fill in every `TODO` with your own experience before submitting.**
> The grader wants to see *your* prompts, *your* changes, and *your* lessons. Keep this honest and specific: what you tried, what broke, what you changed.

## Tools Used

- **Claude** (Anthropic): generated the initial project base (schema, Flask app, templates, Job Match logic, README) from the course project specification, and is being used for guidance on finer details as the project develops.
- TODO: list any other tools (ChatGPT, Gemini, GitHub Copilot, ...) and what you used each for.

## Key Prompts

1. Attached the project specification (.docx) and asked: *"Generate the base for this project and help me through the finer details as we go."*
2. TODO: add each important prompt you use from here on (debugging, validation, UI changes, matching tweaks). Copy the exact wording.
3. TODO
4. TODO

## What Worked Well

- Claude produced a complete working base in one pass: schema with foreign keys and JSON columns, CRUD routes for all four tables, a dashboard, and the Job Match page.
- Job Match logic was kept in its own module (`matching.py`) with unit tests that reproduce the spec's own example (100% for 3/3, 67% for 2/3 with "Tableau" missing).
- TODO: what else saved you time or taught you something?

## What I Changed

> Record every edit you make to AI-generated code. Examples of what graders like to see: renamed things to fit your style, fixed a bug, tightened validation, redesigned a page, changed a query.

- TODO: change #1 (file, what, why)
- TODO: change #2
- TODO: change #3

## Bugs / Errors I Hit and How I Fixed Them

- TODO: error message → what caused it → how you fixed it (and which tool, if any, helped)

## How I Verified the AI's Work

- Unit tests for the matching algorithm (`python -m unittest discover tests`).
- TODO: describe how *you* tested the app yourself (adding, editing, deleting records; bad input; the Job Match page; running `schema.sql` on a clean database).

## Lessons Learned

- TODO: e.g. what the AI got right or wrong, what you now understand about Flask / SQL / JSON columns that you didn't before, and what you'd do differently when prompting next time.

## Understanding Check (for my own prep)

Before submitting, I should be able to explain, without the AI's help:
- [ ] How a request flows: browser → Flask route → SQL → template
- [ ] Why queries use `%s` placeholders instead of string formatting
- [ ] What `ON DELETE CASCADE` does and why I chose it
- [ ] How a JSON column is written and read back in Python
- [ ] How the match percentage is calculated and how ties are broken
