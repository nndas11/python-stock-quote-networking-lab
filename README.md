# Python networking lab: stock quotes

## Setup and run

Requires Python 3.10 or newer. Uses only the standard library; there are no third-party packages to install. Tested locally with Python 3.14.2.

1. Create a Twelve Data account and obtain an API key at [Twelve Data](https://twelvedata.com/). Choose a plan that supports your intended symbols and data freshness.
2. In a terminal, change to this directory and set your key:

   ```sh
   export TWELVEDATA_API_KEY='replace-with-your-key'
   bash run.sh
   ```

   The run script creates a local `.venv` on first use and launches the program. It can also be called from another directory using its full path.
3. Enter `ADBE` or another supported stock symbol. Enter `quit` or `exit` to stop; Ctrl-C and end-of-input also exit cleanly.

Windows PowerShell alternative:

```powershell
py -3 -m venv .venv
$env:TWELVEDATA_API_KEY = 'replace-with-your-key'
.\.venv\Scripts\python.exe stock_quotes.py
```

Keep your real key out of source files, screenshots, and submissions. The program sends it in an HTTPS authorization header and does not log it.

## API research and selection

| API | Python integration | Suitability |
| --- | --- | --- |
| [Twelve Data quote API](https://twelvedata.com/docs/mcp) | HTTPS and JSON through `urllib.request`; an [official Python client](https://github.com/twelvedata/twelvedata-python) is also available | One quote response contains company name, symbol, close/latest price, change, percentage change, currency, exchange, and timestamp. Selected for this lab. |
| [Alpha Vantage](https://www.alphavantage.co/documentation/) | HTTPS and JSON through `urllib.request` | `GLOBAL_QUOTE` supplies price and changes; `SYMBOL_SEARCH` supplies names. Default quotes update at the end of each trading day; real-time/delayed access requires the corresponding entitlement. |

Research checked October 13, 2026. Plans, quotas, and coverage can change. The current computer time is printed first; the provider's quote time is printed separately in UTC. The application reports the latest available quote and does not promise real-time access. Changes are the provider's differences from the previous close, not changes since the user's last lookup. Numbers use `Decimal` and are displayed to two decimal places.

Input accepts up to 20 letters, digits, dots, or hyphens. This lab supports provider stock symbols, not every possible instrument or exchange-qualified identifier. The returned exchange and currency make the provider's selection visible. An international production version should require exchange selection for ambiguous symbols.

## My design approach using AI tools — nine points

1. **Define Agile requirements myself.** Write a user story: “As a student, I can enter a stock symbol and see the company name, price, signed changes, and time, then enter another symbol.” Define acceptance criteria for positive, negative, and zero changes, invalid input, outages, and clean exit. Deliver input/output first, networking second, and resilience third.
2. **Research and choose the API.** Compare documented providers for field coverage, freshness, limits, licensing, and cost. Choose Twelve Data because a single quote response supplies the required fields. Ask AI to summarize official documentation, then personally verify the endpoint and record the decision.
3. **Own the architecture.** Separate the command-line loop, symbol validation, provider adapter, quote record, and formatter. Give an AI coding agent small implementation tasks within these boundaries. I decide interfaces and tradeoffs and review every generated change; the running application retrieves data directly without an LLM.
4. **Make setup reproducible.** Use a Python virtual environment, standard-library networking, a run script, and Git. Configure the API key through an environment variable. If dependencies become necessary, pin and review them before adoption.
5. **Design resilience explicitly.** Set a 10-second socket timeout and at most three attempts with increasing delays for transient network/server failures. Handle authentication, unknown symbols, quotas, malformed JSON, and missing fields with readable errors. Do not retry permanent failures automatically or fabricate a price. Keep the input loop usable after an error. The socket timeout is not a strict total request deadline.
6. **Protect data integrity and security.** Validate user input and provider responses, verify HTTPS certificates, avoid secret logging, and use decimal arithmetic for prices. Show currency, exchange, and quote time separately from retrieval time so users can judge freshness.
7. **Check applicable industry obligations.** Verify provider/exchange permissions for personal use, attribution, storage, and redistribution before expanding the application. Publish source code without credentials or licensed data. This lab does not establish regulatory compliance; production requirements depend on the use case and jurisdiction. See [Twelve Data terms](https://twelvedata.com/terms).
8. **Plan interoperability.** Keep provider-specific JSON behind the adapter and return a stable `Quote` record. A later JSON/REST interface can use explicit field names, decimal strings, ISO 8601 timestamps, currency/exchange identifiers, versioning, and documented errors. Design that contract myself before asking AI to implement it.
9. **Verify and improve incrementally.** Use synthetic offline tests for success, errors, retries, and repeated input; perform an authenticated live smoke test before submission. Use AI to propose edge cases and review code, then independently inspect results. In later sprints, add CI and sanitized operational metrics for failures and latency if deployment requires them.

## Verification

```sh
python3 -m unittest discover -s . -p 'test_*.py' -v
```

Tests use synthetic fixtures and mocked HTTP responses, so no credentials, quota, or network are needed. They check formatting, response validation, network exhaustion, transient recovery, permanent HTTP failures, provider errors, missing credentials, repeated input, and EOF/Ctrl-C. No authenticated live quote was verified during preparation because no user API key was supplied.

For a live smoke test, run the script with your key, look up a supported symbol, then enter an invalid symbol and finally another valid symbol. Confirm the timestamp, currency, and exchange, and compare against the same provider's data for the same time. A subscription with end-of-day data cannot fulfill a strict real-time requirement; obtain the needed entitlement if your instructor requires it.

## Submission

Upload `stock_quotes.py` and `run.sh` to Canvas, or submit a GitHub link containing them. Include this README and `test_stock_quotes.py` for setup, research, design, and test evidence. This repository contains the submission files and `.gitignore`, but no virtual environment or credentials. Review the code and adapt the design explanation to reflect your own decisions and course requirements before submission.
