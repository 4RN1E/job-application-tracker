"""Job Match logic: compare the skills you have with the skills a job asks for.

Kept free of Flask and database code so it can be unit tested on its own
(see tests/test_matching.py).

Scoring rule (matches the project spec's example):
    match % = (job requirements you have) / (total job requirements) * 100
"""
import re
from collections import Counter


def normalize(skill):
    """Lower-case and collapse whitespace so 'Python ' == 'python'."""
    return " ".join(str(skill).strip().lower().split())


def parse_skills(text):
    """Split free text like 'Python, SQL; Flask' into a clean list.

    Accepts commas, semicolons and new lines as separators. Duplicates are
    removed (case-insensitively); the first spelling the user typed is kept.
    """
    if not text:
        return []
    seen = set()
    skills = []
    for part in re.split(r"[,;\n]", text):
        skill = " ".join(part.split())
        key = normalize(skill)
        if key and key not in seen:
            seen.add(key)
            skills.append(skill)
    return skills


def match_job(user_skills, requirements):
    """Score one job. Returns None if the job lists no requirements."""
    if not requirements:
        return None
    have = {normalize(s) for s in user_skills}
    matched = [r for r in requirements if normalize(r) in have]
    missing = [r for r in requirements if normalize(r) not in have]
    total = len(requirements)
    # int(x + 0.5) rounds half up (Python's round() rounds 12.5 down to 12)
    percent = int(100 * len(matched) / total + 0.5)
    return {
        "matched": matched,
        "missing": missing,
        "matched_count": len(matched),
        "total": total,
        "percent": percent,
    }


def rank_jobs(jobs, user_skills):
    """Return (ranked, unscored).

    jobs        -- list of dicts, each with a 'requirements' list
    ranked      -- jobs that list requirements, each with a 'match' dict,
                   best match first (ties: more matched skills, then title)
    unscored    -- jobs with no requirements listed (can't be scored)
    """
    ranked, unscored = [], []
    for job in jobs:
        result = match_job(user_skills, job.get("requirements") or [])
        if result is None:
            unscored.append(job)
        else:
            ranked.append({**job, "match": result})
    ranked.sort(
        key=lambda j: (
            -j["match"]["percent"],
            -j["match"]["matched_count"],
            j["job_title"].lower(),
        )
    )
    return ranked, unscored


def top_missing_skills(ranked, limit=5):
    """Skills you lack that appear most often across the ranked jobs."""
    counts = Counter()
    display = {}
    for job in ranked:
        for skill in job["match"]["missing"]:
            key = normalize(skill)
            counts[key] += 1
            display.setdefault(key, skill)
    return [(display[k], n) for k, n in counts.most_common(limit)]
