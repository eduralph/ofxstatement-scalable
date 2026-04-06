# Scalable Capital plugin for ofxstatement

Converts **Scalable Capital Bank** cash account statements to OFX format for
import into GnuCash or other personal finance software.

[ofxstatement](https://github.com/kedder/ofxstatement) is a tool to convert
proprietary bank statements to OFX format.


## Supported account types

- **Cash Account** (clearing / settlement account, `account_type=CHECKING`)

The PDF must have a text layer (i.e. not a scanned image); all PDFs downloaded
directly from the Scalable Capital client area qualify.


## Input format

Scalable Capital exports a PDF titled *Cash Account Statement* from the client
area under **Documents → Account statements**.

The parser reads the following fields from the PDF:

| Field | Source in PDF |
|-------|---------------|
| Account IBAN | `Clearing account DE… (BIC)` header line |
| Bank BIC | `Clearing account DE… (BIC)` header line |
| Statement period | `Period DD.MM.YYYY – DD.MM.YYYY` |
| Start balance | `Balance on <start date>` |
| End balance | `Balance on <end date>` |
| Booking date | First date column in each transaction row |
| Value date | Second date column in each transaction row |
| Description | Free-text description column |
| Amount | German-locale decimal (`1.234,56` / `-1.234,56`) |


## Transaction types

Transactions are classified by the sign of the amount:

| Condition | OFX type |
|-----------|----------|
| Amount ≥ 0 | `CREDIT` |
| Amount < 0 | `DEBIT` |


## Caveats

The transaction type mapping is intentionally simple because Scalable Capital
Cash Account Statements do not include a machine-readable keyword field — only
a free-text description.  If you need finer-grained OFX types (e.g. `XFER`,
`DIRECTDEBIT`, `INT`), please
[open an issue](https://github.com/eduralph/ofxstatement-scalable/issues)
and include a (anonymised) sample description line.


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


## Status

Work in progress — tested against a Scalable Capital Cash Account Statement
PDF exported in 2025.
Feedback and pull requests welcome.


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
