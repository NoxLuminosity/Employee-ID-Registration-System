"""
Shared Utility Functions
========================
Common helpers used across multiple modules.
Consolidated here to avoid code duplication.
"""


def parse_lark_name(full_name: str) -> dict:
    """
    Parse a full name into first name, middle initial, and last name.

    Handles various name formats:
    - "John Doe" -> first: John, last: Doe
    - "John M. Doe" -> first: John, middle: M, last: Doe
    - "John Michael Doe" -> first: John, middle: M, last: Doe
    - "John" -> first: John
    """
    if not full_name:
        return {"first_name": "", "middle_initial": "", "last_name": ""}

    parts = full_name.strip().split()

    if len(parts) == 1:
        return {
            "first_name": parts[0],
            "middle_initial": "",
            "last_name": "",
        }
    elif len(parts) == 2:
        return {
            "first_name": parts[0],
            "middle_initial": "",
            "last_name": parts[1],
        }
    else:
        # First, middle(s), and last name
        middle = parts[1]
        middle_initial = middle.replace(".", "")[0].upper() if middle else ""
        return {
            "first_name": parts[0],
            "middle_initial": middle_initial,
            "last_name": parts[-1],
        }
