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
Scalable Capital statement parser for ofxstatement.
"""

from typing import Iterator, Optional

from ofxstatement.plugin import Plugin
from ofxstatement.parser import StatementParser
from ofxstatement.statement import Statement, StatementLine


class ScalablePlugin(Plugin):
    """Scalable Capital statement plugin"""

    def get_parser(self, filename: str) -> "ScalableParser":
        return ScalableParser(filename)


class ScalableParser(StatementParser[str]):
    def __init__(self, filename: str) -> None:
        super().__init__()
        self.filename = filename

    def parse(self) -> Statement:
        raise NotImplementedError("ScalableParser is not yet implemented")

    def split_records(self) -> Iterator[str]:
        return iter([])

    def parse_record(self, line: str) -> Optional[StatementLine]:
        return None
