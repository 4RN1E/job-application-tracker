# AI Usage Documentation

> **Draft started during the build. Fill in every `TODO` with your own experience before submitting.**
> The grader wants to see *your* prompts, *your* changes, and *your* lessons. Keep this honest and specific: what you tried, what broke, what you changed.

## Tools Used

- **Claude** (Anthropic): generated the initial project base (schema, Flask app, templates, Job Match logic, README) from the course project specification, and is being used for guidance on finer details as the project develops.

## Key Prompts

1. Attached the project specification (.docx) and asked: *"Generate the base for this project and help me through the finer details as we go."*
2. Help me change the password for mysql on this device. (I was using my pc for this assignment. I usually use my laptop)

## What Worked Well

- Claude produced a complete working base in one pass: schema with foreign keys and JSON columns, CRUD routes for all four tables, a dashboard, and the Job Match page.
- Job Match logic was kept in its own module (`matching.py`) with unit tests that reproduce the spec's own example (100% for 3/3, 67% for 2/3 with "Tableau" missing).
- AI is extremely powerful and was able to complete the functionality of the application in one pass.

## What I Changed

- Change #1: I decided to make it more my style so I edited the style.css to match the branding of my clothing brand. 
- Change #2: There was no Accepted/hired button so I added it to the application.
- Change #3: Added Royal Caribbean Group as an employer, added the name of the role and other info, set it to offer.

## Bugs / Errors I Hit and How I Fixed Them

- I had errors when changing the password for MySQL and I had Claude assist me. It helped me do it by running powershell as admin and running a few commands.

## How I Verified the AI's Work

- Unit tests for the matching algorithm (`python -m unittest discover tests`).
- Once I ran the application, I proceeded to test it thouroughly by creating, evaluating, updating, and deleting     data from the application. 

## Lessons Learned

- When handing a full project spec to AI, it has everything it needs to successfully create what you want. 

## Understanding Check (for my own prep)

Before submitting, I should be able to explain, without the AI's help:
- [ ] How a request flows: browser → Flask route → SQL → template
- [ ] Why queries use `%s` placeholders instead of string formatting
- [ ] What `ON DELETE CASCADE` does and why I chose it
- [ ] How a JSON column is written and read back in Python
- [ ] How the match percentage is calculated and how ties are broken
