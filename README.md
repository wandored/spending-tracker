# Spending Tracker

## Overview

Spending Tracker is a personal finance application written in Python that imports transactions from multiple financial institutions into a single SQLite database. Once imported, the data is normalized, categorized, and summarized for reporting through a web dashboard.

The project was designed to solve a common problem: every bank exports transaction data in a different format. Spending Tracker converts those exports into a single, consistent schema that can be queried and analyzed.

## Features

* Import transactions from multiple financial institutions
* Normalize transaction descriptions
* Automatically categorize transactions using configurable YAML rules
* Prevent duplicate imports using transaction hashes
* Maintain a local SQLite database
* Generate financial summary metrics
* Display reports through a local web dashboard
* Produce an import audit showing newly imported transactions

## Current Supported Banks

* CapitalOne
* American Express
* Citi

Additional importers can be added by implementing a new importer class.

---

## Project Structure

```text
spending-tracker/
├── config/
│   ├── accounts.yaml          # Account definitions
│   ├── categories.yaml        # Category matching rules
│   └── descriptions.yaml      # Description normalization rules
│
├── data/
│   ├── spending_tracker.db
│   ├── importers.py
│   └── metrics.py
│
├── utils/
│   ├── category_manager.py
│   └── description_cleaner.py
│
├── web/
│   ├── app.py
│   ├── templates/
│   └── static/
│
└── spending_tracker.py
```

---

## Database

The application stores all transactions in a local SQLite database.

### Accounts

Stores information about each financial account.

| Column       | Description                     |
| ------------ | ------------------------------- |
| id           | Primary key                     |
| account_name | Friendly account name           |
| account_type | checking, savings, credit, etc. |
| institution  | Financial institution           |

### Transactions

Stores every imported transaction.

| Column           | Description                            |
| ---------------- | -------------------------------------- |
| account_id       | Account reference                      |
| transaction_date | Transaction date                       |
| description      | Normalized description                 |
| transaction_type | credit or debit                        |
| amount           | Positive transaction amount            |
| balance          | Running account balance (if available) |
| category         | User assigned category                 |
| imported_hash    | Duplicate detection hash               |

---

## Configuration

### accounts.yaml

Defines the accounts to import.

Example:

```yaml
accounts:
  - account_id: 1
    account_name: Capital One Checking
    importer: CapitalOneImporter
    file: CapitalOne_Checking.csv
```

---

### categories.yaml

Contains automatic category assignment rules.

Example:

```yaml
categories:
  default: Misc

  rules:

    Transfer:
      - Emergency Savings
      - Household Acct

    Debts:
      - Rocket Mortgage
      - Ally
```

---

### descriptions.yaml

Normalizes vendor descriptions before categorization.

Example:

```yaml
cleanup:

  prefixes:
    - withdrawal from
    - electronic payment to

  normalize:

    Rocket Mortgage:
      - rocket mortgage
      - nsm dbamr
```

This allows multiple vendor names to be grouped together in reports.

---

## Import Process

Each import follows the same workflow:

1. Read CSV export
2. Parse institution-specific format
3. Normalize transaction description
4. Assign category
5. Generate transaction hash
6. Insert new transactions into SQLite
7. Skip duplicate transactions
8. Display import audit

---

## Duplicate Detection

Duplicate imports are prevented using a SHA-256 hash generated from:

* Transaction date
* Description
* Transaction type
* Amount

Repeated imports safely ignore previously imported transactions.

---

## Reporting

Current metrics include:

* Current Cash Balance
* Monthly Average Income
* Monthly Average Expenses
* Current Month Net Income
* Current Quarter Net Income
* Current Year Net Income
* Last 12 Months Net Income
* Top Spending Categories
* Top Spending Vendors

Transfers are excluded from spending calculations.

---

## Web Dashboard

The web dashboard displays:

* Account balances
* Financial summary
* Monthly income vs. expenses
* Top spending vendors
* Top spending categories

The dashboard is intended for day-to-day review while the command-line importer serves as the audit process.

---

## Running

Import transactions:

```bash
python -m spending_tracker
```

Start the dashboard:

```bash
python web/app.py
```

---

## Future Enhancements

* Investment account support
* Loan tracking
* Merchant normalization improvements
* Budget tracking
* Net worth reporting
* Monthly financial snapshots
* Cash flow forecasting
* CSV/Excel report exports

---

## License

This project is intended for personal use.
