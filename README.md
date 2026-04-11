# Scalable Capital plugin for ofxstatement

Converts **Scalable Capital Bank** cash account statements (PDF) to OFX format
for import into GnuCash, HomeBank, or other personal finance software.

[ofxstatement](https://github.com/kedder/ofxstatement) is a tool to convert
proprietary bank statements to OFX format.

Both **English** and **German** statement PDFs are supported.


## Supported account types

- **Cash Account** (clearing / settlement account, `account_type=CHECKING`)

The PDF must have a text layer (i.e. not a scanned image); all PDFs downloaded
directly from the Scalable Capital client area qualify.


## Input format

Scalable Capital exports a PDF titled *Cash Account Statement*
(or *Kontoauszug* in German) from the client area under
**Documents > Account statements**.

The parser reads the following fields from the PDF:

| Field | Source in PDF |
|-------|---------------|
| Account IBAN | `Clearing account DE… (BIC)` / `Verrechnungskonto DE… (BIC)` |
| Bank BIC | `Clearing account DE… (BIC)` / `Verrechnungskonto DE… (BIC)` |
| Statement period | `Period DD.MM.YYYY – DD.MM.YYYY` / `Zeitraum …` |
| Start balance | `Balance on <start date>` / `Kontostand am …` / `Saldo am …` |
| End balance | `Balance on <end date>` / `Kontostand am …` / `Saldo am …` |
| Booking date | First date column in each transaction row |
| Value date | Second date column in each transaction row |
| Description | Free-text description column |
| Amount | English-locale decimal (`1,234.56` / `-1,234.56`) |


## Transaction types

Transactions are classified by matching the description text against a
built-in type map.  Entries are either **tested** (confirmed against real
Scalable Capital statements, marked ★ in source) or **best-effort** (added
for completeness but not yet verified, marked ○ in source).

### Tested (confirmed against real statements)

| Description prefix | OFX type | Category |
|--------------------|----------|----------|
| Buy of a financial instrument | `DEBIT` | ETF / fund purchase |
| Credit transfer | `XFER` | Incoming bank transfer |
| Direct debit | `DIRECTDEBIT` | Savings-plan SEPA pull |
| Withdrawal from cash account | `XFER` | Cash-out to linked bank |
| Received interest | `INT` | PRIME+ / money-market interest |
| Trade fee | `SRVCHG` | Per-trade brokerage fee |
| Vorabpauschale | `DEBIT` | Advance lump-sum fund tax (DE) |

### Best-effort (not yet verified — help wanted)

| Description prefix | OFX type | Category |
|--------------------|----------|----------|
| Sell of a financial instrument | `CREDIT` | ETF / fund sale |
| Savings plan execution | `DEBIT` | Savings plan buy |
| Deposit to cash account | `XFER` | Cash-in from linked bank |
| Dividend | `DIV` | Dividend payment |
| Advance lump-sum tax | `DEBIT` | Vorabpauschale (EN) |
| Account fee | `SRVCHG` | Account maintenance fee |
| Withholding tax | `DEBIT` | Capital gains tax |
| Tax refund | `CREDIT` | Tax correction / refund |
| Tax correction | `CREDIT` | Tax adjustment |
| Tax optimisation | `CREDIT` | Tax loss harvesting refund |
| Kapitalertragsteuer | `DEBIT` | Capital gains tax (DE) |
| Solidaritätszuschlag | `DEBIT` | Solidarity surcharge (DE) |
| Kirchensteuer | `DEBIT` | Church tax (DE) |
| Bonus | `CREDIT` | Sign-up / referral bonus |

German equivalents are also recognised (Kauf, Verkauf, Lastschrift,
Abbuchung, Zinsen, Sparplanausführung, Steuererstattung, Prämie, etc.).
See `TXN_TYPE_MAP` in `plugin.py` for the full list.

Unrecognised descriptions are logged as a `WARNING` with the prefix
`"Unknown transaction type"` and mapped to `OTHER`.

**If you use Scalable Capital** and encounter a transaction that is
misclassified or falls back to `OTHER`, please
[open an issue](https://github.com/eduralph/ofxstatement-scalable/issues)
and include the description text from your statement (amounts and dates
can be redacted).  This helps promote best-effort entries to tested and
improve the type map for everyone.


## Installation

### Dependencies

- [ofxstatement](https://github.com/kedder/ofxstatement) — the conversion
  framework this plugin hooks into
- [pdfplumber](https://github.com/jsvine/pdfplumber) — PDF text extraction

Both are declared as package dependencies and installed automatically.

```
pip install ofxstatement-scalable
```

Or from source:

```
git clone https://github.com/eduralph/ofxstatement-scalable
cd ofxstatement-scalable
python -m venv .venv
.venv/bin/pip install -e .
```


## Usage

```
ofxstatement convert -t scalable statement.pdf statement.ofx
```

Multiple files:

```bash
for f in *.pdf; do
    ofxstatement convert -t scalable "$f" "${f%.*}.ofx"
done
```

To see detailed parsing output (useful for diagnosing issues):

```
ofxstatement -d convert -t scalable statement.pdf statement.ofx
```

The output file uses the account IBAN as the account ID, so GnuCash will
automatically associate it with the correct account on re-import.
GnuCash deduplicates on the transaction ID, so re-importing a file you have
already imported is safe.


## Development setup

```
python -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/pytest tests/
```


## Contributing

Contributions are welcome.  If you have a Scalable Capital account, you can
help by running your statements through the plugin and reporting any issues:

1. Export your Cash Account Statement PDFs from the Scalable Capital client area
2. Convert them: `ofxstatement -d convert -t scalable statement.pdf statement.ofx`
3. Check the output for `WARNING` lines about unknown transaction types
4. [Open an issue](https://github.com/eduralph/ofxstatement-scalable/issues)
   with the description text (redact amounts and dates if you prefer)

Pull requests that add confirmed (★) entries to `TXN_TYPE_MAP` are especially
appreciated.


## License

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.

Copyright (C) 2026  Eduard Ralph
