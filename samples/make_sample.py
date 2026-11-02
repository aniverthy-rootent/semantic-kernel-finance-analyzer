"""Create samples/transactions.csv: six months of realistic transactions."""
import csv
import random
from datetime import date, timedelta
from pathlib import Path

random.seed(11)
rows = []
for m in range(6):
    first = date(2025, 1 + m, 1)
    rows.append((first, "ACME Corp Payroll salary", 3600.00))
    rows.append((first + timedelta(days=1), "City Landlord rent", -1250.00))
    rows.append((first + timedelta(days=4), "Electric Co electric bill", -round(random.uniform(55, 90), 2)))
    rows.append((first + timedelta(days=5), "FastNet broadband internet", -39.99))
    rows.append((first + timedelta(days=6), "Netflix subscription", -15.49))
    rows.append((first + timedelta(days=6), "Spotify subscription", -10.99))
    rows.append((first + timedelta(days=9), "FitLife Gym membership", -34.00))
    rows.append((first + timedelta(days=9), "Adobe Creative subscription", -22.99))
    rows.append((first + timedelta(days=12), "Brokerage investment transfer", -200.00))
    for _ in range(random.randint(6, 9)):
        rows.append((first + timedelta(days=random.randint(0, 27)),
                     random.choice(["Whole Foods market", "Aldi supermarket", "Lidl supermarket"]),
                     -round(random.uniform(18, 95), 2)))
    for _ in range(random.randint(4, 8)):
        rows.append((first + timedelta(days=random.randint(0, 27)),
                     random.choice(["Starbucks coffee", "Pizza Palace restaurant", "Uber Eats", "Corner cafe"]),
                     -round(random.uniform(6, 48), 2)))
    for _ in range(random.randint(2, 4)):
        rows.append((first + timedelta(days=random.randint(0, 27)),
                     random.choice(["Amazon purchase", "Zara", "IKEA", "Apple Store"]),
                     -round(random.uniform(15, 220), 2)))
    rows.append((first + timedelta(days=random.randint(0, 27)), "Metro transit pass", -round(random.uniform(20, 60), 2)))
    rows.append((first + timedelta(days=random.randint(15, 27)), "Mystery Merchant 4471", -round(random.uniform(8, 60), 2)))
rows.append((date(2025, 4, 18), "Dental clinic", -310.00))
rows.sort()
with Path(__file__).with_name("transactions.csv").open("w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["date", "description", "amount"])
    w.writerows((d.isoformat(), desc, f"{amt:.2f}") for d, desc, amt in rows)
print(f"wrote {len(rows)} transactions")
