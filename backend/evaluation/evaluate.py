import pandas as pd


# -------------------------
# 1. Load triage results
# -------------------------

from backend.config import TRIAGE_RESULTS_FILE

def main():
    if not TRIAGE_RESULTS_FILE.exists():
        print(f"Error: Results file not found at {TRIAGE_RESULTS_FILE}")
        print("Please run `python -m backend.evaluation.main` first to generate triage results.")
        raise SystemExit(1)

    results = pd.read_csv(TRIAGE_RESULTS_FILE)

    print("Support Ticket Triage Evaluation")
    print("--------------------------------")

    print(f"Total tickets: {len(results)}")


    # -------------------------
    # 2. Check each prediction
    # -------------------------

    results["correct"] = (
        results["category"]
        == results["expected_category"]
    )


    # -------------------------
    # 3. Calculate accuracy
    # -------------------------

    correct_count = results["correct"].sum()

    total_count = len(results)

    accuracy = (
        correct_count / total_count
    ) * 100


    # -------------------------
    # 4. Display results
    # -------------------------

    print(f"Correct classifications: {correct_count}")
    print(
        f"Incorrect classifications: "
        f"{total_count - correct_count}"
    )

    print(f"Classification accuracy: {accuracy:.2f}%")

if __name__ == "__main__":
    main()
