import sqlite3


class CategoryManager:
    def __init__(self, db_path, categories):
        self.db_path = db_path

        self.default = categories["default"]
        self.rules = categories["rules"]

    def get_category(self, description):

        description = description.upper()

        for category, patterns in self.rules.items():
            for pattern in patterns:
                if pattern.upper() in description:
                    return category

        return self.default

    def sync_database(self):

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            cursor = conn.execute("""
                SELECT
                    id,
                    description,
                    category
                FROM transactions
            """)

            updated = 0

            for row in cursor:
                new_category = self.get_category(row["description"])

                if new_category != row["category"]:
                    conn.execute(
                        """
                        UPDATE transactions
                        SET category = ?
                        WHERE id = ?
                        """,
                        (
                            new_category,
                            row["id"],
                        ),
                    )

                    updated += 1

            conn.commit()

        print(f"Updated {updated} transaction categories.")
