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
"""
Scalable Capital Cash Account Statement parser for ofxstatement.

Supports PDF statements issued in English and German.
"""

import hashlib
import logging
import re
from datetime import datetime
from decimal import Decimal
from typing import Iterator, List, Optional, Tuple

import pdfplumber

from ofxstatement.exceptions import ParseError
from ofxstatement.plugin import Plugin
from ofxstatement.parser import StatementParser
from ofxstatement.statement import Statement, StatementLine

logger = logging.getLogger(__name__)

DATE_FMT = "%d.%m.%Y"

# --- document type detection ------------------------------------------------
_DOCTYPE_CASH_RE = re.compile(r"^(?:Cash Account Statement|Kontoauszug)$", re.MULTILINE)
_DOCTYPE_SECURITIES_RE = re.compile(
    r"^(?:Securities Account Statement|Depotauszug)$", re.MULTILINE
)

# --- transaction row --------------------------------------------------------
# DD.MM.YYYY  DD.MM.YYYY  <description>  [+-]N,NNN.NN EUR
_TX_RE = re.compile(
    r"^(\d{2}\.\d{2}\.\d{4})\s+(\d{2}\.\d{2}\.\d{4})\s+(.+?)\s+([+-]?[\d,]+\.\d{2})\s+EUR\s*$"
)

# --- table header (EN / DE) -------------------------------------------------
# When seen, we enter (or re-enter) the transaction table.
_TABLE_HEADER_RE = re.compile(
    r"^(?:Booking Value date Description Amount"
    r"|Buchung Wertstellung Beschreibung Betrag)$"
)

# --- true end of transaction table ------------------------------------------
# "Distribution of your deposits" page (EN/DE) and empty-statement notice.
_TABLE_END_RE = re.compile(
    r"^(?:Distribution of your deposits"
    r"|Verteilung Ihrer Einlagen"
    r"|No account movements"
    r"|Keine Kontobewegungen"
    r"|If you use Credit"
    r"|Wenn Sie Kredit nutzen)"        # DE equivalent
)

# --- structural lines to skip inside the table area -------------------------
# Page headers/footers that repeat on every page but carry no transaction data.
_STRUCTURAL_RE = re.compile(
    r"^(?:"
    r"Scalable Capital Bank GmbH"
    r"|Seitzstraße 8e"
    r"|80538 M"
    r"|HRB \d"
    r"|Registry Court"
    r"|Sales tax"
    r"|Managing Directors"
    r"|Supervisory Board"
    r"|Florian Prucker"
    r"|Dirk Franzmeyer"
    r"|Patrick Olson"
    r"|Cash Account Statement"
    r"|Kontoauszug"                      # DE: page title
    r"|Period \d{2}\.\d{2}"
    r"|Zeitraum \d{2}\.\d{2}"            # DE: period header
    r"|Document no\."
    r"|Dokument-?Nr\.?"                   # DE: document number
    r"|Clearing account"
    r"|Verrechnungskonto"                 # DE: clearing account label
    r"|Balance on \d{2}\.\d{2}"
    r"|Kontostand am \d{2}\.\d{2}"        # DE: balance label
    r"|Saldo am \d{2}\.\d{2}"            # DE: balance label (alt)
    r"|\d+ / \d+$"                       # page number
    r")"
)


# ---------------------------------------------------------------------------
# Transaction type map
#
# Entries marked ★ are confirmed against real statements (2025–2026).
# Entries marked ○ are best-effort additions for descriptions not yet
# observed in available statements — see README caveats.
#
# Matching is case-insensitive prefix matching on the description field.
# ---------------------------------------------------------------------------
TXN_TYPE_MAP: List[Tuple[str, str]] = [
    # ── Securities ─────────────────────────────────────────────────────────
    ("Buy of a financial instrument", "DEBIT"),         # ★ ETF / fund purchase
    ("Sell of a financial instrument", "CREDIT"),       # ○ ETF / fund sale
    ("Savings plan execution", "DEBIT"),                # ○ savings plan buy
    ("Kauf eines Finanzinstruments", "DEBIT"),          # ○ DE: purchase
    ("Verkauf eines Finanzinstruments", "CREDIT"),      # ○ DE: sale
    ("Sparplanausführung", "DEBIT"),                    # ○ DE: savings plan execution
    # ── Cash account movements ─────────────────────────────────────────────
    ("Credit transfer", "XFER"),                        # ★ incoming bank transfer
    ("Direct debit", "DIRECTDEBIT"),                    # ★ savings-plan SEPA pull
    ("Withdrawal from cash account", "XFER"),           # ★ cash-out to linked bank
    ("Deposit to cash account", "XFER"),                # ○ cash-in from linked bank
    ("Überweisung", "XFER"),                            # ○ DE: bank transfer
    ("Gutschrift", "XFER"),                             # ○ DE: incoming credit
    ("Lastschrift", "DIRECTDEBIT"),                     # ○ DE: SEPA direct debit
    ("Abbuchung", "XFER"),                              # ○ DE: debit / withdrawal
    ("Auszahlung", "XFER"),                             # ○ DE: withdrawal
    ("Einzahlung", "XFER"),                             # ○ DE: deposit
    # ── Income ─────────────────────────────────────────────────────────────
    ("Received interest", "INT"),                       # ★ PRIME+ / money-market interest
    ("Dividend", "DIV"),                                # ○ dividend payment
    ("Zinsgutschrift", "INT"),                          # ○ DE: interest credit
    ("Zinsen", "INT"),                                  # ○ DE: interest
    ("Dividende", "DIV"),                               # ○ DE: dividend
    # ── Fees and taxes ─────────────────────────────────────────────────────
    ("Trade fee", "SRVCHG"),                            # ★ per-trade brokerage fee
    ("Vorabpauschale", "DEBIT"),                        # ★ DE advance lump-sum fund tax
    ("Advance lump-sum tax", "DEBIT"),                  # ○ EN: Vorabpauschale equivalent
    ("Account fee", "SRVCHG"),                          # ○ account maintenance fee
    ("Handelsgebühr", "SRVCHG"),                        # ○ DE: trading fee
    ("Transaktionsgebühr", "SRVCHG"),                   # ○ DE: transaction fee
    ("Kontoführungsgebühr", "SRVCHG"),                  # ○ DE: account fee
    # ── Tax withholding and adjustments ────────────────────────────────────
    ("Withholding tax", "DEBIT"),                       # ○ capital gains tax deduction
    ("Tax refund", "CREDIT"),                           # ○ tax correction / refund
    ("Tax correction", "CREDIT"),                       # ○ tax adjustment
    ("Tax optimisation", "CREDIT"),                     # ○ tax loss harvesting refund
    ("Kapitalertragsteuer", "DEBIT"),                   # ○ DE: capital gains tax
    ("Solidaritätszuschlag", "DEBIT"),                  # ○ DE: solidarity surcharge
    ("Kirchensteuer", "DEBIT"),                         # ○ DE: church tax
    ("Steuererstattung", "CREDIT"),                     # ○ DE: tax refund
    ("Steueroptimierung", "CREDIT"),                    # ○ DE: tax optimisation
    ("Steuerkorrektor", "CREDIT"),                      # ○ DE: tax correction
    # ── Bonus / promotional ───────────────────────────────────────────────
    ("Bonus", "CREDIT"),                                # ○ sign-up / referral bonus
    ("Prämie", "CREDIT"),                               # ○ DE: promotional credit
]


def _txn_type(description: str) -> str:
    """Map a transaction description to an OFX transaction type.

    Uses case-insensitive prefix matching against TXN_TYPE_MAP.
    Logs a warning and returns 'OTHER' for unknown descriptions.
    """
    lower = description.lower()
    for prefix, ttype in TXN_TYPE_MAP:
        if lower.startswith(prefix.lower()):
            return ttype
    logger.warning("Unknown transaction type: %r — add to TXN_TYPE_MAP?", description)
    return "OTHER"


def _make_id(date: datetime, amount: Decimal, memo: str, seq: int) -> str:
    """Stable 16-hex-char transaction ID derived from key fields.

    Includes a sequence number to distinguish transactions that share the
    same date, amount, and memo (e.g. multiple identical ETF purchases).
    """
    raw = f"{date.isoformat()}|{amount}|{seq}|{memo}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _parse_amount(s: str) -> Decimal:
    """Parse an English-locale decimal string (comma = thousands separator).

    Examples: '+602.96', '-13,864.86', '14,466.34', '0.00'
    """
    return Decimal(s.replace(",", ""))


class ScalablePlugin(Plugin):
    """Scalable Capital statement plugin"""

    def get_parser(self, filename: str) -> "ScalableParser":
        return ScalableParser(filename)


class ScalableParser(StatementParser[str]):
    def __init__(self, filename: str) -> None:
        super().__init__()
        self.filename = filename

    def parse(self) -> Statement:
        logger.info("Parsing %s", self.filename)
        self.statement = Statement()
        self.statement.currency = "EUR"
        self.statement.account_type = "CHECKING"

        try:
            pdf_cm = pdfplumber.open(self.filename)
        except Exception as exc:
            raise ParseError(
                0,
                f"{self.filename!r} could not be opened as a PDF.",
            ) from exc

        with pdf_cm as pdf:
            n_pages = len(pdf.pages)
            pages_text = []
            total_lines = 0
            for i, page in enumerate(pdf.pages, 1):
                text = page.extract_text() or ""
                page_lines = len(text.splitlines())
                total_lines += page_lines
                logger.debug("  Page %d/%d: %d lines", i, n_pages, page_lines)
                pages_text.append(text)
        logger.info("PDF: %d page(s), %d lines total", n_pages, total_lines)

        full_text = "\n".join(pages_text)

        if _DOCTYPE_SECURITIES_RE.search(full_text):
            raise ParseError(
                0,
                "Securities Account Statements are not supported — "
                "please use a Cash Account Statement PDF.",
            )
        if not _DOCTYPE_CASH_RE.search(full_text):
            raise ParseError(
                0,
                "Unrecognised Scalable Capital document. "
                "Expected a Cash Account Statement PDF.",
            )

        self._parse_header(full_text)
        self._parse_transactions(full_text)

        logger.info("Done: %d transaction(s)", len(self.statement.lines))
        return self.statement

    def _parse_header(self, text: str) -> None:
        # IBAN and BIC — language-independent DE IBAN pattern
        m = re.search(r"(DE\d{20})\s+\(([\w]+)\)", text)
        if m:
            self.statement.account_id = m.group(1)
            self.statement.bank_id = m.group(2)
            masked = m.group(1)[:4] + "…" + m.group(1)[-4:]
            logger.debug("IBAN found: %s, BIC: %s", masked, m.group(2))
        else:
            logger.warning("IBAN/BIC not found — account_id will be unset")

        # Period: EN "Period" / DE "Zeitraum"
        m = re.search(
            r"(?:Period|Zeitraum)\s+(\d{2}\.\d{2}\.\d{4})\s+-\s+(\d{2}\.\d{2}\.\d{4})",
            text,
        )
        if m:
            self.statement.start_date = datetime.strptime(m.group(1), DATE_FMT)
            self.statement.end_date = datetime.strptime(m.group(2), DATE_FMT)
            logger.debug("Period: %s – %s", m.group(1), m.group(2))
        else:
            logger.warning("Period not found in header")

        # Balances: EN "Balance on" / DE "Kontostand am" / "Saldo am"
        balance_re = re.compile(
            r"(?:Balance on|Kontostand am|Saldo am)"
            r"\s+\d{2}\.\d{2}\.\d{4}\s+([\d,]+\.\d{2})\s+EUR"
        )
        balances = balance_re.findall(text)
        if len(balances) >= 1:
            self.statement.start_balance = _parse_amount(balances[0])
        if len(balances) >= 2:
            self.statement.end_balance = _parse_amount(balances[-1])
        logger.debug(
            "Balances: start=%s end=%s",
            self.statement.start_balance,
            self.statement.end_balance,
        )

    def _parse_transactions(self, text: str) -> None:
        """Scan all lines, entering transaction-table mode at each table header.

        The header "Booking Value date Description Amount" (or its German
        equivalent) is repeated on every page that contains transactions.
        Structural header/footer lines within the table area are silently
        skipped.  The scan stops when a "Distribution of your deposits" section
        or an empty-statement notice is encountered.
        """
        in_table = False
        pending: Optional[dict] = None
        txn_seq = 0

        for line in text.split("\n"):
            # Table header — enter (or re-enter) table mode
            if _TABLE_HEADER_RE.match(line):
                in_table = True
                logger.debug("Entered transaction table")
                continue

            if not in_table:
                continue

            # True end of transaction data
            if _TABLE_END_RE.match(line):
                logger.debug("End of transaction table")
                break

            m = _TX_RE.match(line)
            if m:
                if pending is not None:
                    sl = self._emit(pending, txn_seq)
                    if sl is not None:
                        self.statement.lines.append(sl)
                txn_seq += 1
                pending = {
                    "booking": m.group(1),
                    "value": m.group(2),
                    "description": m.group(3).strip(),
                    "amount_str": m.group(4),
                    "continuation": [],
                }
                logger.debug(
                    "Txn #%d: %s %s %s",
                    txn_seq,
                    m.group(1),
                    m.group(3).strip().split()[0],
                    m.group(4),
                )
            elif pending is not None:
                if _STRUCTURAL_RE.match(line):
                    logger.debug("Skipped structural line: %r", line[:60])
                    continue
                stripped = line.strip()
                if stripped:
                    pending["continuation"].append(stripped)
                    logger.debug(
                        "Continuation for txn #%d (now %d lines)",
                        txn_seq,
                        len(pending["continuation"]),
                    )
            else:
                stripped = line.strip()
                if stripped and not _STRUCTURAL_RE.match(line):
                    logger.debug(
                        "Skipped unrecognised line in table (no pending txn): %r",
                        line[:80],
                    )

        if pending is not None:
            sl = self._emit(pending, txn_seq)
            if sl is not None:
                self.statement.lines.append(sl)

    def _emit(self, t: dict, seq: int) -> Optional[StatementLine]:
        """Convert a parsed transaction dict to a StatementLine."""
        booking_date = datetime.strptime(t["booking"], DATE_FMT)
        value_date = datetime.strptime(t["value"], DATE_FMT)
        amount = _parse_amount(t["amount_str"])

        description = t["description"]
        ttype = _txn_type(description)

        # Payee: the description text (e.g. "Buy of a financial instrument")
        # Memo: description + continuation lines for full detail
        memo = description
        if t["continuation"]:
            memo += " | " + " | ".join(t["continuation"])

        line = StatementLine()
        line.date = booking_date
        line.date_user = value_date
        line.payee = description
        line.memo = memo
        line.amount = amount
        line.trntype = ttype
        line.id = _make_id(booking_date, amount, memo, seq)

        if booking_date != value_date:
            logger.debug(
                "  Value date differs: booked=%s valued=%s",
                booking_date.strftime(DATE_FMT),
                value_date.strftime(DATE_FMT),
            )

        logger.debug(
            "  → %s %s payee=%r amount=%s",
            ttype,
            booking_date.strftime(DATE_FMT),
            description,
            amount,
        )
        return line

    def split_records(self) -> Iterator[str]:
        return iter([])

    def parse_record(self, line: str) -> Optional[StatementLine]:
        return None
