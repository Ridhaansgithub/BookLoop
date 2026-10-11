import os
import re


API_URL = (
    os.getenv("BOOKLOOP_API_URL")
    or os.getenv("API_URL")
    or "https://bookloop-api-kade.onrender.com"
).rstrip("/")

GRADE_OPTIONS = [
    "Class 1",
    "Class 2",
    "Class 3",
    "Class 4",
    "Class 5",
    "Class 6",
    "Class 7",
    "Class 8",
    "Class 9",
    "Class 10",
    "Class 11",
    "Class 12",
]

CATEGORY_OPTIONS = ["SAT Prep", "ACT Prep", "AP Books", "College Textbooks"]


def book_category(book: dict) -> str:
    searchable_text = " ".join(
        str(book.get(field, "")) for field in ("title", "author", "target_class")
    )
    if re.search(r"\bSAT\b|scholastic (?:aptitude|assessment) test", searchable_text, re.IGNORECASE):
        return "SAT Prep"
    if re.search(r"\bACT\b|american college testing", searchable_text, re.IGNORECASE):
        return "ACT Prep"
    if re.search(r"\bAP\b|advanced placement", searchable_text, re.IGNORECASE):
        return "AP Books"
    return "College Textbooks"


def grade_label(grade: str) -> str:
    number = int(grade.removeprefix("Class "))
    suffix = "th" if 10 < number % 100 < 14 else {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix} Grade"