# spending_tracker.p
import yaml
import hashlib
import sqlite3
import os
import importlib
import pandas as pd

from utils.importers import (
    CapitalOneImporter,
    AmexImporter,
    CitiImporter,
    BPCardImporter,
)
from utils.metrics import FinancialReportService
from utils.description_cleaner import DescriptionCleaner
from utils.category_manager import CategoryManager
from pathlib import Path
from datetime import datetime


PROJECT_ROOT = Path(__file__).parent
CONFIG_DIR = PROJECT_ROOT / "config"
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = Path(DATA_DIR / "spending_tracker.db")


def resolve_importer(importer_spec):
    if callable(importer_spec):
        return importer_spec

    if isinstance(importer_spec, str):
        # try dotted path first
        if "." in importer_spec:
            module_path, _, cls_name = importer_spec.rpartition(".")
            try:
                module = importlib.import_module(module_path)
                return getattr(module, cls_name)
            except (ImportError, AttributeError):
                pass
        # try data.importers module
        try:
            module = importlib.import_module("data.importers")
            return getattr(module, importer_spec)
        except (ImportError, AttributeError):
            pass
        # fallback to globals (e.g. imported at top)
        return globals().get(importer_spec)

    return None


def import_transactions():
    import_summary = []
    new_transactions = []
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(CONFIG_DIR / "categories.yaml", "r") as f:
        categories_config = yaml.safe_load(f)["categories"]

    category_manager = CategoryManager(str(DB_PATH), categories_config)

    # initialize description cleaner
    cleaner = DescriptionCleaner(CONFIG_DIR / "descriptions.yaml")

    with sqlite3.connect(str(DB_PATH)) as conn:
        cursor = conn.cursor()
        with open(CONFIG_DIR / "accounts.yaml", "r") as f:
            config = yaml.safe_load(f)
            for account in config.get("accounts", []):
                default_path = "/home/wandored/Projects/spending-tracker/data/"
                account_id = account.get("account_id")
                account_name = account.get("account_name")
                file_name = account.get("file")
                importer_spec = account.get("importer")

                importer_class = resolve_importer(importer_spec)
                if not importer_class:
                    print(
                        f"Importer '{importer_spec}' not found for account '{account_name}'"
                    )
                    continue

                data_file = os.path.join(default_path, file_name)
                try:
                    importer = importer_class(data_file)
                except Exception as e:
                    print(f"Failed to instantiate importer for '{account_name}': {e}")
                    continue

                import_fn = getattr(importer, "import_data", None)
                if not callable(import_fn):
                    print(
                        f"Importer for '{account_name}' does not provide callable 'import_data' method"
                    )
                    continue
                inserted = 0
                duplicates = 0
                transactions = import_fn()

                for transaction in transactions:
                    # ensure required keys exist; skip otherwise
                    if (
                        "transaction_date" not in transaction
                        or "description" not in transaction
                    ):
                        print(f"Skipping malformed transaction: {transaction}")
                        continue

                    # Save original bank description
                    transaction["raw_description"] = transaction["description"]

                    # clean descriptions
                    description = transaction["description"]
                    transaction["description"] = cleaner.clean(description)

                    # add category
                    transaction["category"] = category_manager.get_category(
                        transaction["description"]
                    )

                    # add account_id to transaction for reference
                    transaction["account_id"] = account_id

                    # Generate a unique hash for each transaction using its date, raw_description, type, and amount
                    transaction_str = f"{transaction['account_id']}_{transaction['transaction_date']}_{transaction.get('raw_description', '')}_{transaction.get('transaction_type', '')}_{transaction['amount']}"
                    transaction_hash = hashlib.sha256(
                        transaction_str.encode()
                    ).hexdigest()
                    transaction["imported_hash"] = transaction_hash

                    # write to data/spending_tracker.db
                    try:
                        cursor.execute(
                            """
                            INSERT OR IGNORE INTO transactions (
                                account_id,
                                transaction_date,
                                raw_description,
                                description,
                                transaction_type,
                                amount,
                                balance,
                                category,
                                imported_hash
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                            (
                                transaction["account_id"],
                                transaction["transaction_date"],
                                transaction["raw_description"],
                                transaction.get("description", ""),
                                transaction.get("transaction_type", ""),
                                transaction["amount"],
                                transaction["balance"],
                                transaction.get("category", "Misc"),
                                transaction["imported_hash"],
                            ),
                        )
                        if cursor.rowcount == 1:
                            inserted += 1

                            new_transactions.append(
                                {
                                    "Date": transaction["transaction_date"],
                                    "Account": account_name,
                                    "Type": transaction["transaction_type"].title(),
                                    "Description": transaction["description"],
                                    "Category": transaction["category"],
                                    "Amount": transaction["amount"],
                                }
                            )
                        else:
                            duplicates += 1
                        # Use the same connection to execute and commit
                    except Exception as e:
                        print(f"Failed to insert transaction: {e} - {transaction}")
                import_summary.append(
                    {
                        "Account": account_name,
                        "Imported": inserted,
                        "Duplicates": duplicates,
                        "Total Imported": inserted + duplicates,
                    }
                )
                conn.commit()

    return import_summary, new_transactions


def normalize_descriptions():
    cleaner = DescriptionCleaner("config/descriptions.yaml")

    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, description
            FROM transactions
        """)

        updated = 0

        for row in cursor.fetchall():
            old_description = row["description"]
            new_description = cleaner.clean(old_description)

            if old_description != new_description:
                cursor.execute(
                    """
                    UPDATE transactions
                    SET description = ?
                    WHERE id = ?
                    """,
                    (new_description, row["id"]),
                )

                updated += 1

        conn.commit()


def add_account_balance(account_id, balance, balance_date=None):
    if balance_date is None:
        balance_date = datetime.now().strftime("%Y-%m-%d")

    description = "Balance Snapshot"

    transaction_str = f"{account_id}_{balance_date}_{description}_{balance}"

    imported_hash = hashlib.sha256(transaction_str.encode()).hexdigest()

    with sqlite3.connect(str(DB_PATH)) as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR IGNORE INTO transactions (
                account_id,
                transaction_date,
                description,
                transaction_type,
                amount,
                balance,
                category,
                imported_hash
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                account_id,
                balance_date,
                description,
                "balance",
                0,
                balance,
                "Balance",
                imported_hash,
            ),
        )

        conn.commit()

        return cursor.rowcount == 1


def report_metrics(summary_df, transactions_df):
    report_service = FinancialReportService("data/spending_tracker.db")
    report = report_service.get_report_data()
    # print(report["summary"])
    #
    # for row in report["account_balances"]:
    #     print(row)
    #
    # for row in report["monthly_trend"]:
    #     print(row)
    # for row in report["top_descriptions"]:
    #     print(row)
    # for row in report["top_categories"]:
    #     print(row)
    print()
    if not transactions_df.empty:
        transactions_df["Amount"] = transactions_df["Amount"].map("${:,.2f}".format)
        transactions_df = transactions_df.sort_values(
            ["Date", "Account"],
            ascending=[False, True],
        )
        transactions_df.reset_index(drop=True, inplace=True)

    print(summary_df)
    print()
    print(transactions_df)

    return report


if __name__ == "__main__":
    import_summary, new_transactions = import_transactions()

    with open(CONFIG_DIR / "categories.yaml", "r") as f:
        categories_config = yaml.safe_load(f)["categories"]
        category_manager = CategoryManager(str(DB_PATH), categories_config)
        category_manager.sync_database()

    normalize_descriptions()

    summary_df = pd.DataFrame(import_summary)
    transactions_df = pd.DataFrame(new_transactions)

    report = report_metrics(summary_df, transactions_df)
