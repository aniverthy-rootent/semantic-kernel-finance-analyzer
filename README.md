# Personal Finance Analyzer

**Framework:** Semantic Kernel  
**Agents:** 6

Analyses a bank-statement CSV: categorises spending, finds subscriptions, compares to the 50/30/20 rule and writes an action plan. Agents call native plugins through function calling.

> **Status:** this project was written as complete, runnable code but has **not been executed end to end against live LLM APIs** yet. It needs your own API key; expect to fix small issues from provider or library version changes. Issues and PRs welcome.

## Agents

| # | Agent | Role |
|---|---|---|
| 1 | Ingest | loads the CSV and reports data quality |
| 2 | Categorizer | spend by category |
| 3 | Budget Analyst | monthly cash flow + 50/30/20 |
| 4 | Subscription Hunter | recurring charges, big expenses |
| 5 | Savings Advisor | ranked savings actions |
| 6 | Report Writer | final Markdown report |

## Run it

```bash
pip install -r requirements.txt
cp .env.example .env
python samples/make_sample.py
python main.py samples/transactions.csv --out finance_report.md
```

## How it works

Educational information, not financial advice. ChatCompletionAgents with kernel_function plugins sharing a Ledger.

## Configuration

See `.env.example`. Models are chosen with one `LLM_SPEC` variable so you can switch provider without touching code.

## License

MIT
