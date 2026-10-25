from dataclasses import dataclass
import sqlite3


@dataclass
class FinancialSummary:
    current_week_expense: float
    current_monthly_expense: float
    current_year_expense: float
    last_12_month_expense: float
    avg_monthly_income: float
    avg_monthly_expense: float
    month_net: float
    quarter_net: float
    year_net: float
    trailing_12_month_net: float


class FinancialReportService:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def _query(self, conn, sql: str):
        conn.row_factory = sqlite3.Row
        return [dict(row) for row in conn.execute(sql)]

    def _scalar(self, conn, sql: str):
        result = conn.execute(sql).fetchone()[0]
        return round(result or 0, 2)

    def get_report_data(self):

        with sqlite3.connect(self.db_path) as conn:
            # -------------------------
            # Summary Metrics
            # -------------------------

            summary = FinancialSummary(
                current_week_expense=self._scalar(
                    conn,
                    """
                    SELECT COALESCE(SUM(amount), 0)
                    FROM transactions
                    WHERE transaction_type = 'debit'
                      AND category <> 'Transfer'
                      AND transaction_date >= date('now', '-6 days', 'weekday 1')
                      AND transaction_date < date('now', '+1 day', 'weekday 1')
                    """,
                ),
                current_monthly_expense=self._scalar(
                    conn,
                    """
                    SELECT COALESCE(SUM(amount), 0)
                    FROM transactions
                    WHERE transaction_type = 'debit'
                      AND category <> 'Transfer'
                      AND strftime('%Y-%m', transaction_date) = strftime('%Y-%m', 'now')
                    """,
                ),
                current_year_expense=self._scalar(
                    conn,
                    """
                    SELECT COALESCE(SUM(amount), 0)
                    FROM transactions
                    WHERE transaction_type = 'debit'
                      AND category <> 'Transfer'
                      AND strftime('%Y', transaction_date) = strftime('%Y', 'now')
                    """,
                ),
                last_12_month_expense=self._scalar(
                    conn,
                    """
                    SELECT COALESCE(SUM(amount), 0)
                    FROM transactions
                    WHERE transaction_type = 'debit'
                      AND category <> 'Transfer'
                      AND transaction_date >= date('now', '-12 months')
                    """,
                ),
                avg_monthly_income=self._scalar(
                    conn,
                    """
                    WITH monthly_income AS (
                        SELECT
                            strftime('%Y-%m', transaction_date) AS month,
                            SUM(amount) AS income
                        FROM transactions
                        WHERE transaction_type = 'credit'
                          AND category <> 'Transfer'
                        GROUP BY month
                    )
                    SELECT AVG(income)
                    FROM monthly_income
                    """,
                ),
                avg_monthly_expense=self._scalar(
                    conn,
                    """
                    WITH monthly_expense AS (
                        SELECT
                            strftime('%Y-%m', transaction_date) AS month,
                            SUM(amount) AS expense
                        FROM transactions
                        WHERE transaction_type = 'debit'
                          AND category <> 'Transfer'
                        GROUP BY month
                    )
                    SELECT AVG(expense)
                    FROM monthly_expense
                    """,
                ),
                month_net=self._scalar(
                    conn,
                    """
                    SELECT SUM(
                        CASE
                            WHEN transaction_type='credit'
                            THEN amount
                            ELSE -amount
                        END
                    )
                    FROM transactions
                    WHERE category <> 'Transfer'
                      AND strftime('%Y-%m', transaction_date)
                          = strftime('%Y-%m', 'now')
                    """,
                ),
                quarter_net=self._scalar(
                    conn,
                    """
                    WITH current_quarter AS (
                        SELECT
                            CAST(strftime('%Y', 'now') AS INTEGER) AS yr,
                            ((CAST(strftime('%m', 'now') AS INTEGER)-1)/3) AS qtr
                    )
                    SELECT SUM(
                        CASE
                            WHEN t.transaction_type='credit'
                            THEN t.amount
                            ELSE -t.amount
                        END
                    )
                    FROM transactions t
                    CROSS JOIN current_quarter cq
                    WHERE category <> 'Transfer'
                      AND CAST(strftime('%Y', t.transaction_date) AS INTEGER)=cq.yr
                      AND ((CAST(strftime('%m', t.transaction_date) AS INTEGER)-1)/3)=cq.qtr
                    """,
                ),
                year_net=self._scalar(
                    conn,
                    """
                    SELECT SUM(
                        CASE
                            WHEN transaction_type='credit'
                            THEN amount
                            ELSE -amount
                        END
                    )
                    FROM transactions
                    WHERE category <> 'Transfer'
                      AND strftime('%Y', transaction_date)
                          = strftime('%Y', 'now')
                    """,
                ),
                trailing_12_month_net=self._scalar(
                    conn,
                    """
                    SELECT SUM(
                        CASE
                            WHEN transaction_type='credit'
                            THEN amount
                            ELSE -amount
                        END
                    )
                    FROM transactions
                    WHERE category <> 'Transfer'
                      AND transaction_date >= date('now', '-12 months')
                    """,
                ),
            )

            # -------------------------
            # Monthly Trend Chart
            # -------------------------

            monthly_trend = self._query(
                conn,
                """
                WITH monthly_totals AS (
                    SELECT
                        strftime('%Y-%m', transaction_date) AS month,
                        SUM(
                            CASE
                                WHEN transaction_type='credit'
                                THEN amount
                                ELSE 0
                            END
                        ) AS income,
                        SUM(
                            CASE
                                WHEN transaction_type='debit'
                                THEN amount
                                ELSE 0
                            END
                        ) AS expense
                    FROM transactions
                    WHERE category <> 'Transfer'
                    GROUP BY month
                    ORDER BY month DESC
                    LIMIT 12
                )
                SELECT
                    month,
                    ROUND(income, 2) AS income,
                    ROUND(expense, 2) AS expense,
                    ROUND(income - expense, 2) AS net
                FROM monthly_totals
                ORDER BY month
                """,
            )

            # -------------------------
            # Account Balances
            # -------------------------

            account_balances = self._query(
                conn,
                """
                WITH latest_balance AS (
                    SELECT
                        a.account_name,
                        t.balance,
                        t.transaction_date,
                        ROW_NUMBER() OVER (
                            PARTITION BY t.account_id
                            ORDER BY t.transaction_date DESC, t.id DESC
                        ) AS rn
                    FROM transactions t
                    JOIN accounts a
                        ON a.id = t.account_id
                    WHERE t.balance IS NOT NULL
                )
                SELECT
                    account_name,
                    balance,
                    transaction_date
                FROM latest_balance
                WHERE rn = 1
                ORDER BY account_name
                """,
            )

            # -------------------------
            # Top Descriptions
            # -------------------------

            top_descriptions = self._query(
                conn,
                """
                SELECT
                    description,
                    ROUND(SUM(amount), 2) AS total,
                    COUNT(*) AS count,
                    ROUND(SUM(amount)/COUNT(*), 2) AS transaction_average
                FROM transactions
                WHERE transaction_type='debit'
                  AND category <> 'Transfer'
                AND transaction_date >= date('now', '-12 months')
                GROUP BY description
                ORDER BY total DESC
                LIMIT 10
                """,
            )

            # -------------------------
            # Top Categories
            # -------------------------

            top_categories = self._query(
                conn,
                """
                SELECT
                    category,
                    ROUND(SUM(amount), 2) AS total,
                    COUNT(*) AS count,
                    ROUND(
                        SUM(amount) * 100.0 / 
                        (
                            SELECT SUM(amount) 
                            FROM transactions 
                            WHERE transaction_type='debit' 
                                AND category <> 'Transfer' 
                                AND transaction_date >= date('now', '-12 months')
                        ),
                        1
                    ) AS percentage_of_total
                FROM transactions
                WHERE transaction_type='debit'
                    AND category <> 'Transfer'
                    AND transaction_date >= date('now', '-12 months')
                GROUP BY category
                ORDER BY total DESC
                """,
            )

        return {
            "summary": summary,
            "account_balances": account_balances,
            "monthly_trend": monthly_trend,
            "top_descriptions": top_descriptions,
            "top_categories": top_categories,
        }
