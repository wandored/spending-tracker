from flask import Flask, render_template
from utils.metrics import FinancialReportService

app = Flask(__name__)

report_service = FinancialReportService("data/spending_tracker.db")


@app.route("/")
def dashboard():

    report = report_service.get_report_data()

    return render_template(
        "dashboard.html",
        report=report,
    )


if __name__ == "__main__":
    app.run(
        debug=True,
        host="0.0.0.0",
        port=5000,
    )
