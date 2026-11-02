"""Native Semantic Kernel plugins over a bank-statement CSV (date, description, amount; spend < 0)."""
from __future__ import annotations

import csv
import json
import re
import statistics
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Annotated

from semantic_kernel.functions import kernel_function

CATEGORY_RULES = {
    "Housing": ["rent", "mortgage", "landlord"],
    "Utilities": ["electric", "water", "gas bill", "internet", "broadband", "mobile", "phone"],
    "Groceries": ["supermarket", "grocer", "whole foods", "tesco", "aldi", "lidl", "market"],
    "Dining": ["restaurant", "cafe", "coffee", "starbucks", "pizza", "uber eats", "doordash", "deliveroo"],
    "Transport": ["uber", "lyft", "metro", "train", "fuel", "petrol", "parking", "transit"],
    "Subscriptions": ["netflix", "spotify", "prime", "icloud", "youtube", "gym", "adobe", "subscription"],
    "Shopping": ["amazon", "zara", "ikea", "apple store", "target"],
    "Health": ["pharmacy", "doctor", "dental", "clinic"],
    "Income": ["salary", "payroll", "freelance", "dividend"],
    "Savings": ["savings", "investment", "brokerage", "pension"],
}
NEEDS = {"Housing", "Utilities", "Groceries", "Transport", "Health"}
WANTS = {"Dining", "Subscriptions", "Shopping"}


def _merchant(desc: str) -> str:
    return re.sub(r"[^a-z ]", "", desc.lower()).strip()[:28]


def categorize(desc: str) -> str:
    low = desc.lower()
    for cat, words in CATEGORY_RULES.items():
        if any(w in low for w in words):
            return cat
    return "Other"


class Ledger:
    """Shared state: loaded once by the ingest agent, read by every other plugin."""

    def __init__(self) -> None:
        self.rows: list[dict] = []

    def load(self, path: str) -> None:
        self.rows = []
        with Path(path).open(newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                d = datetime.strptime(r["date"].strip(), "%Y-%m-%d").date()
                amt = float(r["amount"])
                self.rows.append({"date": d, "description": r["description"].strip(), "amount": amt,
                                  "category": categorize(r["description"])})

    def require(self) -> None:
        if not self.rows:
            raise ValueError("No ledger loaded. Call load_statement first.")


class LedgerPlugin:
    def __init__(self, ledger: Ledger) -> None:
        self.ledger = ledger

    @kernel_function(name="load_statement", description="Load a bank statement CSV and return a data-quality summary.")
    def load_statement(self, path: Annotated[str, "Path to the CSV file"]) -> str:
        self.ledger.load(path)
        rows = self.ledger.rows
        income = sum(r["amount"] for r in rows if r["amount"] > 0)
        spend = -sum(r["amount"] for r in rows if r["amount"] < 0)
        dupes = len(rows) - len({(r["date"], r["description"], r["amount"]) for r in rows})
        return json.dumps({"transactions": len(rows), "from": str(min(r["date"] for r in rows)),
                           "to": str(max(r["date"] for r in rows)), "total_income": round(income, 2),
                           "total_spend": round(spend, 2), "possible_duplicates": dupes,
                           "uncategorized": sum(1 for r in rows if r["category"] == "Other")})


class CategoryPlugin:
    def __init__(self, ledger: Ledger) -> None:
        self.ledger = ledger

    @kernel_function(name="spend_by_category", description="Total spend per category plus the biggest uncategorized merchants.")
    def spend_by_category(self) -> str:
        self.ledger.require()
        totals: dict[str, float] = defaultdict(float)
        other: dict[str, float] = defaultdict(float)
        for r in self.ledger.rows:
            if r["amount"] < 0:
                totals[r["category"]] += -r["amount"]
                if r["category"] == "Other":
                    other[_merchant(r["description"])] += -r["amount"]
        return json.dumps({"by_category": {k: round(v, 2) for k, v in sorted(totals.items(), key=lambda x: -x[1])},
                           "top_uncategorized": sorted(((k, round(v, 2)) for k, v in other.items()),
                                                       key=lambda x: -x[1])[:8]})


class AnalyticsPlugin:
    def __init__(self, ledger: Ledger) -> None:
        self.ledger = ledger

    @kernel_function(name="monthly_cashflow", description="Income, spend and net per calendar month.")
    def monthly_cashflow(self) -> str:
        self.ledger.require()
        months: dict[str, dict[str, float]] = defaultdict(lambda: {"income": 0.0, "spend": 0.0})
        for r in self.ledger.rows:
            key = r["date"].strftime("%Y-%m")
            months[key]["income" if r["amount"] > 0 else "spend"] += abs(r["amount"])
        out = {m: {"income": round(v["income"], 2), "spend": round(v["spend"], 2),
                   "net": round(v["income"] - v["spend"], 2)} for m, v in sorted(months.items())}
        return json.dumps(out)

    @kernel_function(name="recurring_charges", description="Detect subscriptions / recurring monthly charges.")
    def recurring_charges(self) -> str:
        self.ledger.require()
        groups: dict[str, list[dict]] = defaultdict(list)
        for r in self.ledger.rows:
            if r["amount"] < 0:
                groups[_merchant(r["description"])].append(r)
        found = []
        for merchant, items in groups.items():
            if len(items) < 3:
                continue
            items.sort(key=lambda x: x["date"])
            gaps = [(b["date"] - a["date"]).days for a, b in zip(items, items[1:])]
            amounts = [abs(i["amount"]) for i in items]
            if 25 <= statistics.median(gaps) <= 35 and statistics.pstdev(amounts) <= 0.15 * statistics.mean(amounts):
                found.append({"merchant": merchant, "times": len(items), "monthly": round(statistics.mean(amounts), 2),
                              "yearly": round(12 * statistics.mean(amounts), 2),
                              "last_charge": str(items[-1]["date"])})
        return json.dumps(sorted(found, key=lambda x: -x["yearly"]))

    @kernel_function(name="largest_expenses", description="The N largest single expenses.")
    def largest_expenses(self, n: Annotated[int, "How many to return"] = 8) -> str:
        self.ledger.require()
        spends = sorted((r for r in self.ledger.rows if r["amount"] < 0), key=lambda r: r["amount"])[:n]
        return json.dumps([{"date": str(r["date"]), "description": r["description"], "amount": r["amount"]} for r in spends])


class BudgetPlugin:
    def __init__(self, ledger: Ledger) -> None:
        self.ledger = ledger

    @kernel_function(name="rule_50_30_20", description="Compare needs/wants/savings to the 50/30/20 budgeting rule.")
    def rule_50_30_20(self) -> str:
        self.ledger.require()
        income = sum(r["amount"] for r in self.ledger.rows if r["amount"] > 0) or 1.0
        needs = sum(-r["amount"] for r in self.ledger.rows if r["amount"] < 0 and r["category"] in NEEDS)
        wants = sum(-r["amount"] for r in self.ledger.rows if r["amount"] < 0 and (r["category"] in WANTS or r["category"] == "Other"))
        saved = sum(-r["amount"] for r in self.ledger.rows if r["category"] == "Savings" and r["amount"] < 0)
        net_left = income - needs - wants - saved
        pct = lambda x: round(100 * x / income, 1)  # noqa: E731
        return json.dumps({"income": round(income, 2), "needs_pct": pct(needs), "wants_pct": pct(wants),
                           "savings_pct": pct(saved), "unallocated_pct": pct(net_left),
                           "targets": {"needs": 50, "wants": 30, "savings": 20}})
