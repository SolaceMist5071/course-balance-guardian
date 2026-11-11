from datetime import date

from src.course_service import LearnerDeadline, educator_report, should_notify


def test_deadline_decision_drives_educator_report():
    today = date(2026, 10, 25)
    deadlines = [
        LearnerDeadline("a@example.com", "Algebra", date(2026, 10, 25)),
        LearnerDeadline("b@example.com", "Biology", date(2026, 10, 30)),
    ]

    assert should_notify(deadlines[0], today)
    assert not should_notify(deadlines[1], today)
    assert educator_report(deadlines, today) == {"learners": 2, "due": 1, "upcoming": 1}
