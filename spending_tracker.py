# spending_tracker.py

import yaml
import hashlib
import sqlite3
import os
import importlib
import matplotlib.pyplot as plt
import pandas as pd

from data.importers import CapitalOneImporter
from data.metrics import FinancialReportService
from datetime import datetime
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


DB_PATH = Path("data/spending_tracker.db")


def categorize_transaction(transaction):
    # use config/categories.yaml to categorize transactions based on description or use default
    transaction["category"] = "Misc"
    return transaction


def resolve_importer(importer_spec):
    # importer_spec may be:
    # - a callable class object
    # - a string with class name in data.importers (e.g. "CapitalOneImporter")
    # - a dotted path "data.importers.CapitalOneImporter"
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
    # create a SQLite database connection
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(str(DB_PATH)) as conn:
        cursor = conn.cursor()
        with open("config/accounts.yaml", "r") as f:
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
                transactions = import_fn()

                for transaction in transactions:
                    # ensure required keys exist; skip otherwise
                    if (
                        "transaction_date" not in transaction
                        or "description" not in transaction
                    ):
                        print(f"Skipping malformed transaction: {transaction}")
                        continue

                    # convert date to YYYY-MM-DD format
                    try:
                        transaction["transaction_date"] = datetime.strptime(
                            transaction["transaction_date"], "%m/%d/%y"
                        ).strftime("%Y-%m-%d")
                    except ValueError:
                        print(
                            f"Error parsing date '{transaction['transaction_date']}' for transaction: {transaction}"
                        )
                        continue

                    # add category
                    transaction = categorize_transaction(transaction)

                    # add account_id and account_name to transaction for reference
                    transaction["account_id"] = account_id

                    # Generate a unique hash for each transaction using its date, description, type, and amount
                    transaction_str = f"{transaction['transaction_date']}_{transaction.get('description', '')}_{transaction.get('transaction_type', '')}_{transaction['amount']}"
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
                                description,
                                transaction_type,
                                amount,
                                balance,
                                category,
                                imported_hash
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                            (
                                transaction["account_id"],
                                transaction["transaction_date"],
                                transaction.get("description", ""),
                                transaction.get("transaction_type", ""),
                                transaction["amount"],
                                transaction["balance"],
                                transaction.get("category", "Misc"),
                                transaction["imported_hash"],
                            ),
                        )
                        # Use the same connection to execute and commit
                    except Exception as e:
                        print(f"Failed to insert transaction: {e} - {transaction}")
                conn.commit()


def report_metrics():
    report_service = FinancialReportService("data/spending_tracker.db")

    report = report_service.get_report_data()

    print(report["summary"])

    for row in report["account_balances"]:
        print(row)

    for row in report["monthly_trend"]:
        print(row)

    for row in report["top_descriptions"]:
        print(row)

    for row in report["top_categories"]:
        print(row)

    return report


def create_monthly_trend_chart(monthly_trend, output_file):

    df = pd.DataFrame(monthly_trend)
    df = df.sort_values("month")
    df["rolling_avg"] = df["net"].rolling(window=12, min_periods=1).mean()

    plt.figure(figsize=(10, 3))

    plt.bar(
        df["month"],
        df["net"],
    )

    plt.plot(
        df["month"],
        df["rolling_avg"],
        linewidth=2,
    )

    plt.title("Monthly Net Income")
    plt.ylabel("Net Income")
    plt.xticks(rotation=45)

    plt.tight_layout()
    plt.savefig(output_file)
    plt.close()


def draw_metric_box(
    canvas,
    x,
    y,
    width,
    height,
    title,
    value,
):

    canvas.rect(
        x,
        y,
        width,
        height,
    )

    canvas.setFont(
        "Helvetica-Bold",
        10,
    )

    canvas.drawString(
        x + 5,
        y + height - 15,
        title,
    )

    canvas.setFont(
        "Helvetica",
        14,
    )

    canvas.drawString(
        x + 5,
        y + 15,
        value,
    )


def create_pdf(report, pdf_file):

    c = canvas.Canvas(
        pdf_file,
        pagesize=letter,
    )

    page_width, page_height = letter

    #
    # Chart
    #

    c.drawImage(
        "monthly_trend.png",
        40,
        page_height - 280,
        width=530,
        height=200,
    )

    #
    # Metric Boxes
    #

    summary = report["summary"]

    metrics = [
        ("Balance", summary.total_balance),
        ("Avg Income", summary.avg_monthly_income),
        ("Avg Expense", summary.avg_monthly_expense),
        ("Month Net", summary.month_net),
        ("Quarter Net", summary.quarter_net),
        ("Year Net", summary.year_net),
        ("TTM Net", summary.trailing_12_month_net),
    ]

    x = 40
    y = page_height - 420

    for i, (title, value) in enumerate(metrics):
        draw_metric_box(
            c,
            x,
            y,
            120,
            50,
            title,
            f"${value:,.2f}",
        )

        x += 130

        if (i + 1) % 4 == 0:
            x = 40
            y -= 60

    #
    # Top Descriptions
    #

    desc_x = 40
    desc_y = 180

    c.setFont(
        "Helvetica-Bold",
        12,
    )

    c.drawString(
        desc_x,
        desc_y + 120,
        "Top Descriptions",
    )

    c.setFont(
        "Helvetica",
        10,
    )

    for i, row in enumerate(report["top_descriptions"]):
        c.drawString(
            desc_x,
            desc_y + 100 - (i * 12),
            f"{row['description'][:25]:25} ${row['total']:,.0f}",
        )

    #
    # Top Categories
    #

    cat_x = 320

    c.setFont(
        "Helvetica-Bold",
        12,
    )

    c.drawString(
        cat_x,
        desc_y + 120,
        "Top Categories",
    )

    c.setFont(
        "Helvetica",
        10,
    )

    for i, row in enumerate(report["top_categories"]):
        c.drawString(
            cat_x,
            desc_y + 100 - (i * 12),
            f"{row['category'][:25]:25} ${row['total']:,.0f}",
        )

    c.save()


if __name__ == "__main__":
    import_transactions()
    report = report_metrics()
    create_monthly_trend_chart(report["monthly_trend"], "monthly_trend.png")
    create_pdf(report, "financial_report.pdf")
