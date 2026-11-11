import argparse
from datetime import date

from src.course_service import InfraiClient, LearnerDeadline, educator_report, run_delivery


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--recipient", required=True, help="email address for the deadline notice")
    args = parser.parse_args()

    deadline = LearnerDeadline(args.recipient, "Algebra", date.today())
    client = InfraiClient()
    balance = client.balance()
    print("account balance envelope received:", balance["ok"])
    client.configure_autorecharge(trigger_balance=5, recharge_amount=25)
    print(run_delivery(client, deadline, date.today()))
    print(educator_report([deadline], date.today()))


if __name__ == "__main__":
    main()
