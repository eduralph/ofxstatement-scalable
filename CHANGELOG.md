# Changelog

## [0.1.0] - 2026-04-06

### Added
- Initial release: PDF Cash Account Statement parser for Scalable Capital Bank
- IBAN and BIC extraction from the clearing account header line
- Statement period and start/end balance parsing (German locale `1.234,56`)
- Transaction rows parsed from the table (booking date, value date, description, amount)
- Stable transaction IDs (MD5 of booking date / value date / description / amount)
- `CREDIT` / `DEBIT` transaction type assigned from the amount sign
