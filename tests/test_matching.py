"""Unit tests for the Job Match logic. Run from the project root:

    python -m unittest discover tests
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from matching import match_job, parse_skills, rank_jobs, top_missing_skills  # noqa: E402


class ParseSkillsTests(unittest.TestCase):
    def test_splits_on_commas_semicolons_and_newlines(self):
        self.assertEqual(parse_skills("Python, SQL; Flask\nGit"), ["Python", "SQL", "Flask", "Git"])

    def test_removes_duplicates_case_insensitively_keeping_first(self):
        self.assertEqual(parse_skills("Python, python,  PYTHON"), ["Python"])

    def test_ignores_blanks_and_extra_spaces(self):
        self.assertEqual(parse_skills(" ,  Machine   Learning , ,"), ["Machine Learning"])

    def test_empty_input(self):
        self.assertEqual(parse_skills(""), [])
        self.assertEqual(parse_skills(None), [])


class MatchJobTests(unittest.TestCase):
    def test_spec_example_full_match(self):
        r = match_job(["Python", "SQL", "Flask"], ["Python", "SQL", "Flask"])
        self.assertEqual((r["percent"], r["matched_count"], r["total"]), (100, 3, 3))
        self.assertEqual(r["missing"], [])

    def test_spec_example_partial_match(self):
        r = match_job(["Python", "SQL", "Flask"], ["Python", "SQL", "Tableau"])
        self.assertEqual((r["percent"], r["matched_count"], r["total"]), (67, 2, 3))
        self.assertEqual(r["missing"], ["Tableau"])

    def test_case_and_whitespace_insensitive(self):
        r = match_job(["  python "], ["Python"])
        self.assertEqual(r["percent"], 100)

    def test_no_overlap(self):
        self.assertEqual(match_job(["Go"], ["Python", "SQL"])["percent"], 0)

    def test_half_rounds_up(self):
        # 1 of 8 = 12.5% -> 13 (Python's built-in round() would give 12)
        r = match_job(["a"], list("abcdefgh"))
        self.assertEqual(r["percent"], 13)

    def test_no_requirements_is_unscorable(self):
        self.assertIsNone(match_job(["Python"], []))
        self.assertIsNone(match_job(["Python"], None))


class RankJobsTests(unittest.TestCase):
    def setUp(self):
        self.jobs = [
            {"job_title": "Data Analyst", "requirements": ["Python", "SQL", "Tableau"]},
            {"job_title": "Software Developer", "requirements": ["Python", "SQL", "Flask"]},
            {"job_title": "Mystery Role", "requirements": []},
            {"job_title": "Embedded", "requirements": ["C", "RTOS"]},
        ]

    def test_ranks_best_first_and_separates_unscored(self):
        ranked, unscored = rank_jobs(self.jobs, ["Python", "SQL", "Flask"])
        self.assertEqual([j["job_title"] for j in ranked],
                         ["Software Developer", "Data Analyst", "Embedded"])
        self.assertEqual([j["match"]["percent"] for j in ranked], [100, 67, 0])
        self.assertEqual([j["job_title"] for j in unscored], ["Mystery Role"])

    def test_ties_break_by_matched_count_then_title(self):
        jobs = [
            {"job_title": "B", "requirements": ["x", "y"]},          # 50%, 1 matched
            {"job_title": "A", "requirements": ["x", "y"]},          # 50%, 1 matched
            {"job_title": "C", "requirements": ["x", "y", "z", "w"]}, # 25%
        ]
        ranked, _ = rank_jobs(jobs, ["x"])
        self.assertEqual([j["job_title"] for j in ranked], ["A", "B", "C"])

    def test_top_missing_skills(self):
        ranked, _ = rank_jobs(self.jobs, ["Python"])
        top = dict(top_missing_skills(ranked))
        self.assertEqual(top["SQL"], 2)
        self.assertEqual(top["Tableau"], 1)


if __name__ == "__main__":
    unittest.main()
