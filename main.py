"""Personal Finance Analyzer - six Semantic Kernel agents analyse a bank-statement CSV.

    python samples/make_sample.py                 # creates samples/transactions.csv
    python main.py samples/transactions.csv --out finance_report.md

CSV columns: date (YYYY-MM-DD), description, amount (negative = money spent).
"""
import argparse
import asyncio
from pathlib import Path

from dotenv import load_dotenv

from finance.agents import build_team


async def run(csv_path: Path, out: Path) -> None:
    agents = build_team()
    context = ""
    last = ""
    for agent in agents:
        message = (f"CSV path: {csv_path.resolve()}\n\nFindings from the previous agents:\n{context or '(none yet)'}\n\n"
                   "Do your part now.")
        response = await agent.get_response(messages=message)
        last = str(response.message.content)
        print(f"\n===== {agent.name} =====\n{last}")
        context += f"\n--- {agent.name} ---\n{last}\n"
    out.write_text(last, encoding="utf-8")
    print(f"\nReport written to {out}")


def main() -> None:
    load_dotenv()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", type=Path)
    ap.add_argument("--out", type=Path, default=Path("finance_report.md"))
    args = ap.parse_args()
    asyncio.run(run(args.csv, args.out))


if __name__ == "__main__":
    main()
