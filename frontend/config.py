import os


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


def grade_label(grade: str) -> str:
    number = int(grade.removeprefix("Class "))
    suffix = "th" if 10 < number % 100 < 14 else {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix} Grade"