# ofxstatement-scalable - Scalable Capital statement plugin for ofxstatement
# Copyright (C) 2026  Eduard Ralph
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""Tests for ofxstatement-scalable plugin."""

from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from ofxstatement.exceptions import ParseError

from ofxstatement_scalable.plugin import ScalablePlugin, ScalableParser, _parse_amount, _txn_type


# ---------------------------------------------------------------------------
# Unit tests for _parse_amount (English locale: comma = thousands, dot = decimal)
# ---------------------------------------------------------------------------

class TestTxnType:
    def test_buy(self):
        assert _txn_type("Buy of a financial instrument") == "DEBIT"

    def test_sell(self):
        assert _txn_type("Sell of a financial instrument") == "CREDIT"

    def test_credit_transfer(self):
        assert _txn_type("Credit transfer") == "XFER"

    def test_direct_debit(self):
        assert _txn_type("Direct debit") == "DIRECTDEBIT"

    def test_withdrawal(self):
        assert _txn_type("Withdrawal from cash account") == "XFER"

    def test_received_interest(self):
        assert _txn_type("Received interest") == "INT"

    def test_trade_fee(self):
        assert _txn_type("Trade fee") == "SRVCHG"

    def test_vorabpauschale(self):
        assert _txn_type("Vorabpauschale") == "DEBIT"

    def test_case_insensitive(self):
        assert _txn_type("BUY OF A FINANCIAL INSTRUMENT") == "DEBIT"

    def test_unknown_returns_other(self):
        assert _txn_type("Something entirely new") == "OTHER"

    # German entries
    def test_de_buy(self):
        assert _txn_type("Kauf eines Finanzinstruments") == "DEBIT"

    def test_de_withdrawal(self):
        assert _txn_type("Abbuchung vom Cashkonto") == "XFER"

    def test_de_direct_debit(self):
        assert _txn_type("Lastschrift") == "DIRECTDEBIT"

    def test_de_interest(self):
        assert _txn_type("Zinsgutschrift") == "INT"


class TestParseAmount:
    def test_zero(self):
        assert _parse_amount("0.00") == Decimal("0.00")

    def test_simple(self):
        assert _parse_amount("12.34") == Decimal("12.34")

    def test_thousands(self):
        assert _parse_amount("1,234.56") == Decimal("1234.56")

    def test_negative(self):
        assert _parse_amount("-99.99") == Decimal("-99.99")

    def test_negative_thousands(self):
        assert _parse_amount("-13,864.86") == Decimal("-13864.86")

    def test_positive_sign(self):
        assert _parse_amount("+1,000.00") == Decimal("1000.00")


# ---------------------------------------------------------------------------
# Integration-style tests using synthetic extracted text matching the real PDF
# ---------------------------------------------------------------------------

# Single-page English statement (baseline)
SAMPLE_TEXT = """\
Scalable Capital Bank GmbH • Seitzstraße 8e • 80538 Munich • Germany
Cash Account Statement
Period 01.12.2025 - 31.12.2025
Document no. 2617395264
Clearing account DE19120700700756225027 (DEUTDEFFXXX)
Balance on 01.12.2025 14,466.34 EUR
Balance on 31.12.2025 1,204.44 EUR
Booking Value date Description Amount
01.12.2025 03.12.2025 Buy of a financial instrument -200.50 EUR
6.25 pcs. Xtrackers S&P 500 Swap II (Acc) (IE000HY30YW6)
01.12.2025 03.12.2025 Buy of a financial instrument -50.12 EUR
0.67 pcs. Xtrackers MSCI Pacific ex Japan Screened (Acc) (LU0322252338)
01.12.2025 03.12.2025 Buy of a financial instrument -50.12 EUR
0.24 pcs. Amundi JPX Nikkei 400 (Acc) (LU1681038912)
03.12.2025 03.12.2025 Withdrawal from cash account -13,864.86 EUR
29.12.2025 30.12.2025 Direct debit +602.96 EUR
Scalable Capital Bank GmbH HRB 217778 Managing Directors: ...
"""

# Two-page English statement: table header + footer repeat between pages
MULTIPAGE_TEXT = """\
Scalable Capital Bank GmbH • Seitzstraße 8e • 80538 Munich • Germany
Cash Account Statement
Period 01.11.2025 - 30.11.2025
Clearing account DE19120700700756225027 (DEUTDEFFXXX)
Balance on 01.11.2025 2,616.34 EUR
Balance on 30.11.2025 15,067.82 EUR
Booking Value date Description Amount
01.11.2025 01.11.2025 Credit transfer +2,000.00 EUR
03.11.2025 05.11.2025 Buy of a financial instrument -200.00 EUR
6.13 pcs. Xtrackers S&P 500 Swap II (Acc) (IE000HY30YW6)
Scalable Capital Bank GmbH HRB 217778 Managing Directors: Supervisory Board: Page
Seitzstraße 8e Registry Court: Munich Local Court Florian Prucker, Martin Krebs, Patrick Olson (Chairman)
80538 München Sales tax ID: DE300434774 Dirk Franzmeyer 1 / 2
Cash Account Statement
Period 01.11.2025 - 30.11.2025
Booking Value date Description Amount
03.11.2025 05.11.2025 Buy of a financial instrument -75.00 EUR
1.14 pcs. Xtrackers MSCI Emerging Markets (Acc) (IE00BTJRMP35)
26.11.2025 27.11.2025 Direct debit +601.48 EUR
Scalable Capital Bank GmbH HRB 217778 Managing Directors: Supervisory Board: Page
Seitzstraße 8e Registry Court: Munich Local Court Florian Prucker, Martin Krebs, Patrick Olson (Chairman)
80538 München Sales tax ID: DE300434774 Dirk Franzmeyer 2 / 2
Cash Account Statement
Period 01.11.2025 - 30.11.2025
Distribution of your deposits
on the value date 30.11.2025
"""

# German-language statement
GERMAN_TEXT = """\
Scalable Capital Bank GmbH • Seitzstraße 8e • 80538 München • Deutschland
Kontoauszug
Zeitraum 01.12.2025 - 31.12.2025
Verrechnungskonto DE19120700700756225027 (DEUTDEFFXXX)
Kontostand am 01.12.2025 14,466.34 EUR
Kontostand am 31.12.2025 1,204.44 EUR
Buchung Wertstellung Beschreibung Betrag
01.12.2025 03.12.2025 Kauf eines Finanzinstruments -200.50 EUR
6.25 Stk. Xtrackers S&P 500 Swap II (Acc) (IE000HY30YW6)
03.12.2025 03.12.2025 Abbuchung vom Cashkonto -13,864.86 EUR
29.12.2025 30.12.2025 Lastschrift +602.96 EUR
Scalable Capital Bank GmbH HRB 217778 ...
"""


def _make_parser(text: str) -> ScalableParser:
    """Return a ScalableParser whose PDF extraction is mocked to return *text*."""
    parser = ScalableParser("dummy.pdf")

    mock_page = MagicMock()
    mock_page.extract_text.return_value = text

    mock_pdf = MagicMock()
    mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
    mock_pdf.__exit__ = MagicMock(return_value=False)
    mock_pdf.pages = [mock_page]

    with patch("ofxstatement_scalable.plugin.pdfplumber.open", return_value=mock_pdf):
        parser.parse()

    return parser


class TestHeaderParsing:
    def setup_method(self):
        self.stmt = _make_parser(SAMPLE_TEXT).statement

    def test_account_id(self):
        assert self.stmt.account_id == "DE19120700700756225027"

    def test_bank_id(self):
        assert self.stmt.bank_id == "DEUTDEFFXXX"

    def test_currency(self):
        assert self.stmt.currency == "EUR"

    def test_start_date(self):
        assert self.stmt.start_date == datetime(2025, 12, 1)

    def test_end_date(self):
        assert self.stmt.end_date == datetime(2025, 12, 31)

    def test_start_balance(self):
        assert self.stmt.start_balance == Decimal("14466.34")

    def test_end_balance(self):
        assert self.stmt.end_balance == Decimal("1204.44")


class TestTransactionParsing:
    def setup_method(self):
        self.lines = _make_parser(SAMPLE_TEXT).statement.lines

    def test_transaction_count(self):
        assert len(self.lines) == 5

    def test_simple_debit_date(self):
        assert self.lines[3].date == datetime(2025, 12, 3)

    def test_simple_debit_value_date(self):
        assert self.lines[3].date_user == datetime(2025, 12, 3)

    def test_simple_debit_memo(self):
        assert self.lines[3].memo == "Withdrawal from cash account"

    def test_simple_debit_amount(self):
        assert self.lines[3].amount == Decimal("-13864.86")

    def test_simple_debit_type(self):
        assert self.lines[3].trntype == "XFER"

    def test_credit_amount(self):
        assert self.lines[4].amount == Decimal("602.96")

    def test_credit_type(self):
        assert self.lines[4].trntype == "DIRECTDEBIT"

    def test_multiline_memo_includes_continuation(self):
        # First "Buy" entry: memo should include the instrument detail line
        assert "IE000HY30YW6" in self.lines[0].memo

    def test_multiline_memo_format(self):
        assert self.lines[0].memo == (
            "Buy of a financial instrument | "
            "6.25 pcs. Xtrackers S&P 500 Swap II (Acc) (IE000HY30YW6)"
        )

    def test_duplicate_description_amount_different_ids(self):
        # Two entries share date, description, and amount (-50.12) but differ by ISIN
        assert self.lines[1].id != self.lines[2].id

    def test_duplicate_entry_memos_differ(self):
        assert "LU0322252338" in self.lines[1].memo
        assert "LU1681038912" in self.lines[2].memo


class TestEmptyStatement:
    def test_no_transactions(self):
        text = SAMPLE_TEXT.replace(
            "Booking Value date Description Amount\n",
            "Booking Value date Description Amount\nNo account movements during this period\n",
        )
        # Remove the transaction lines
        lines = text.split("\n")
        cleaned = [
            l for l in lines
            if not (
                _is_tx_line(l) or l.strip().startswith(("6.25", "0.67", "0.24"))
            )
        ]
        parser = _make_parser("\n".join(cleaned))
        assert parser.statement.lines == []


def _is_tx_line(line: str) -> bool:
    import re
    return bool(re.match(r"^\d{2}\.\d{2}\.\d{4}\s+\d{2}\.\d{2}\.\d{4}", line))


class TestMultiPage:
    def setup_method(self):
        self.lines = _make_parser(MULTIPAGE_TEXT).statement.lines

    def test_transaction_count(self):
        # 4 transactions spread across two table sections
        assert len(self.lines) == 4

    def test_first_page_last_tx(self):
        # Last tx on page 1 must not lose its continuation
        assert "IE000HY30YW6" in self.lines[1].memo

    def test_second_page_first_tx(self):
        # First tx on page 2 is picked up correctly
        assert "IE00BTJRMP35" in self.lines[2].memo

    def test_second_page_last_tx(self):
        assert self.lines[3].amount == Decimal("601.48")


class TestGermanStatement:
    def setup_method(self):
        self.stmt = _make_parser(GERMAN_TEXT).statement
        self.lines = self.stmt.lines

    def test_account_id(self):
        assert self.stmt.account_id == "DE19120700700756225027"

    def test_start_balance(self):
        assert self.stmt.start_balance == Decimal("14466.34")

    def test_period(self):
        assert self.stmt.start_date == datetime(2025, 12, 1)
        assert self.stmt.end_date == datetime(2025, 12, 31)

    def test_transaction_count(self):
        assert len(self.lines) == 3

    def test_multiline_memo(self):
        assert "IE000HY30YW6" in self.lines[0].memo

    def test_debit_type(self):
        assert self.lines[1].trntype == "XFER"  # Abbuchung vom Cashkonto

    def test_credit_type(self):
        assert self.lines[2].trntype == "DIRECTDEBIT"  # Lastschrift


class TestDocumentTypeDetection:
    def test_securities_statement_raises(self):
        text = "Securities Account Statement\nas of 31.03.2026 • Securities account 5176510410\n"
        with pytest.raises(ParseError, match="Securities Account Statement"):
            _make_parser(text)

    def test_unknown_document_raises(self):
        with pytest.raises(ParseError, match="Unrecognised"):
            _make_parser("This is not a Scalable Capital statement.\n")

    def test_cash_statement_accepted(self):
        # Should not raise — the baseline SAMPLE_TEXT contains "Cash Account Statement"
        _make_parser(SAMPLE_TEXT)


class TestAccountType:
    def test_account_type_is_checking(self):
        stmt = _make_parser(SAMPLE_TEXT).statement
        assert stmt.account_type == "CHECKING"


class TestPayeeField:
    def setup_method(self):
        self.lines = _make_parser(SAMPLE_TEXT).statement.lines

    def test_payee_set_on_simple_transaction(self):
        assert self.lines[3].payee == "Withdrawal from cash account"

    def test_payee_set_on_buy(self):
        assert self.lines[0].payee == "Buy of a financial instrument"

    def test_payee_does_not_include_continuation(self):
        # Payee is just the description; continuation goes in memo
        assert "IE000HY30YW6" not in self.lines[0].payee


class TestPdfOpenError:
    def test_non_pdf_raises_parse_error(self, tmp_path):
        f = tmp_path / "statement.pdf"
        f.write_text("This is not a PDF file\n", encoding="utf-8")
        with pytest.raises(ParseError, match="could not be opened as a PDF"):
            ScalableParser(str(f)).parse()


class TestPlugin:
    def test_get_parser(self):
        plugin = ScalablePlugin(None, {})
        parser = plugin.get_parser("some.pdf")
        assert isinstance(parser, ScalableParser)
        assert parser.filename == "some.pdf"
