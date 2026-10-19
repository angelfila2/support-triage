import csv
import os


def save_result(file_path, result):
    file_exists = os.path.exists(file_path)

    with open(file_path, "a", newline="", encoding="utf-8") as file:
        fieldnames = [
            "ticket_id",
            "subject",
            "category",
            "urgency",
            "confidence",
            "is_suspicious",
            "decision",
            "reason",
            "response",
            "retrieved_sources",
            "expected_category"
        ]

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        if not file_exists:
            writer.writeheader()

        writer.writerow(result)