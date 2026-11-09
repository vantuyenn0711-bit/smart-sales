# Smart Sales

- Read SPEC.md, PLAN.md, DECISIONS.md and IMPLEMENTATION_STATUS.md.
- Build the Django/PostgreSQL MVP, with Vietnamese UI. Keep P2 returns/refunds/POS out of MVP claims.
- Put business changes in transactional services. Enforce roles on the server, use Decimal VND and immutable price/cost snapshots.
- Deduct stock once on confirmation; restore once on permitted unpaid cancellation. Never delete transaction history.
- Run actual checks and tests; record commands, outcomes and verification gaps. File creation is not completion.
- Do not push, publish, incur charges, expose credentials or remove existing data without user authorization.
- Keep secrets, local database files, browser state and downloaded tools out of source control.
