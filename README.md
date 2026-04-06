# Scalable Capital plugin for ofxstatement

Converts **Scalable Capital** bank statements to OFX format for import into
GnuCash or other personal finance software.

[ofxstatement](https://github.com/kedder/ofxstatement) is a tool to convert proprietary bank statements to OFX format.


## Status

Work in progress.


## Installation

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
ofxstatement convert -t scalable statement.csv statement.ofx
```


## Development setup

```
python -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/pytest tests/
```


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
