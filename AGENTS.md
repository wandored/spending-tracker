# spending-tracker

This is a simple spending tracker application that allows users to track their expenses with a minimum of categories. The data is imported from a CSV file and stored in a SQLite database. Once imported, the data is normalized, categorized, and summarized for reporting through a web dashboard.

## Features

* Import transactions from multiple financial institutions
* Normalize transaction descriptions
* Automatically categorize transactions using configurable YAML rules
* Prevent duplicate imports using transaction hashes
* Maintain a local SQLite database
* Generate financial summary metrics
* Display reports through a local web dashboard
* Produce an import audit showing newly imported transactions


