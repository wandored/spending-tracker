# Bank import parsers


class CapitalOneImporter:
    def __init__(self, file_path):
        self.file_path = file_path

    def import_data(self):
        import csv as _csv
        from datetime import datetime

        # implement parsing logic for capital one csv format
        transactions = []
        with open(self.file_path, "r", newline="", encoding="utf-8") as file:
            reader = _csv.reader(file)
            next(reader, None)  # skip header row)

            for row in reader:
                _account, description, date, type, amount, balance = row[:6]

                # convert date to YYYY-MM-DD format
                try:
                    new_date = datetime.strptime(date, "%m/%d/%y").strftime("%Y-%m-%d")
                except ValueError:
                    print(f"Error parsing date for: {row}")
                    continue

                transactions.append(
                    {
                        "transaction_date": new_date,
                        "description": description,
                        "transaction_type": type.lower(),
                        "amount": float(amount),
                        "balance": float(balance),
                    }
                )
        return transactions


class AmexImporter:
    def __init__(self, file_path):
        self.file_path = file_path

    def import_data(self):
        import csv as _csv
        from datetime import datetime

        # implement parsing logic for capital one csv format
        transactions = []
        with open(self.file_path, "r", newline="", encoding="utf-8") as file:
            reader = _csv.reader(file)
            next(reader, None)  # skip header row)

            for row in reader:
                date, description, _card_member, _account, amount = row[:5]

                # convert date to YYYY-MM-DD format
                try:
                    new_date = datetime.strptime(date, "%m/%d/%Y").strftime("%Y-%m-%d")
                except ValueError:
                    print(f"Error parsing date for: {row}")
                    continue

                amount = float(amount)

                if amount < 0:
                    type = "credit"
                    amount = abs(amount)
                else:
                    type = "debit"

                transactions.append(
                    {
                        "transaction_date": new_date,
                        "description": description,
                        "transaction_type": type,
                        "amount": float(amount),
                        "balance": None,
                    }
                )
        return transactions


class CitiImporter:
    def __init__(self, file_path):
        self.file_path = file_path

    def import_data(self):
        import csv as _csv
        from datetime import datetime

        # implement parsing logic for capital one csv format
        transactions = []
        with open(self.file_path, "r", newline="", encoding="utf-8") as file:
            reader = _csv.reader(file)
            next(reader, None)  # skip header row)

            for row in reader:
                _status, date, description, debit, credit = row[:5]

                # convert date to YYYY-MM-DD format
                try:
                    new_date = datetime.strptime(date, "%m/%d/%Y").strftime("%Y-%m-%d")
                except ValueError:
                    print(f"Error parsing date for: {row}")
                    continue

                if debit:
                    type = "debit"
                    amount = float(debit)
                elif credit:
                    type = "credit"
                    amount = abs(float(credit))
                else:
                    print(f"Error parsing type for : {row}")
                    continue

                transactions.append(
                    {
                        "transaction_date": new_date,
                        "description": description,
                        "transaction_type": type,
                        "amount": amount,
                        "balance": None,
                    }
                )
        return transactions


class BPCardImporter:
    def __init__(self, file_path):
        self.file_path = file_path

    def import_data(self):
        import csv as _csv
        from datetime import datetime

        # implement parsing logic for capital one csv format
        transactions = []
        with open(self.file_path, "r", newline="", encoding="utf-8") as file:
            reader = _csv.reader(file)

            for row in reader:
                date, amount, description = row[:3]

                amount = float(amount)
                if amount < 0:
                    type = "debit"
                    amount = abs(float(amount))
                elif amount >= 0:
                    type = "credit"
                    amount = float(amount)
                else:
                    print(f"Error parsing type for : {row}")
                    continue

                transactions.append(
                    {
                        "transaction_date": date,
                        "description": description,
                        "transaction_type": type,
                        "amount": amount,
                        "balance": None,
                    }
                )
        return transactions
