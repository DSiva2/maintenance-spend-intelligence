# Planted Patterns (Answer Key)

These are the problems deliberately built into the synthetic data. Use this file **after** your analysis, to check whether your methods found them. In interviews, be open that the data is synthetic and these patterns were designed; what you are demonstrating is the method for finding, explaining, and acting on them.

`po_line_truth.csv` flags every affected PO line in the `pattern_flags` column.

## Spend and contract leakage

| Pattern | Where | Flag |
|---|---|---|
| Lake Charles shifts valve buying to Bayou Valve & Supply Co, a non-contracted supplier charging 22 to 35% above market, starting January 2024 | C02 Valves, site LCH | `premium_spot_supplier` |
| Conroe and Freeport buy MRO parts from Pelican Industrial Supply LLC at a 22 to 35% premium | C11 MRO Parts, sites CNR and FRP | `premium_spot_supplier` |
| About 5% of purchases from contracted suppliers skip the contract and are priced 4 to 10% above market | All categories | `contract_bypassed` |
| Atchafalaya Insulation Co's contract expires June 30, 2025, but purchases continue at 6% higher prices with no contract | C06 Insulation | `expired_contract` |
| Coastal Hydro Services LLC is blocked for safety violations on June 1, 2024, but Pasadena keeps buying from it | C08 Industrial Cleaning, site PAS | `blocked_supplier` |

## Invoice and billing problems

| Pattern | Where | Flag |
|---|---|---|
| Gulf Coast Scaffold Services LLC bills a 15% mark-up on pass-through materials from July 2024, against an 8% contract cap | C05 Scaffolding | `markup_over_cap` |
| Invoice unit prices above the PO price: about 10% of Ironclad Industrial Services Inc lines, about 1.5% elsewhere | Mostly C04 | `invoice_price_over_po` |
| Suppliers bill the full ordered quantity when only part was received | All | `billed_undelivered` |
| Duplicate invoices: same PO line billed twice, sometimes with a slightly changed invoice number | All | `duplicate_invoice` |
| Freeport pays invoices in 10 to 20 days regardless of 45 or 60 day terms, tying up working capital | Site FRP | (see `invoices.csv`) |

## Supplier risk and performance

| Pattern | Where |
|---|---|
| Delta Rotating Equipment Inc's on-time delivery falls from about 94% to about 55% during 2025, with longer delays | C01 Pump & Compressor Repair |
| Two active contractors (Bayport Mechanical LP, Pelican Scaffold & Rigging LLC) have insurance that expired May 31, 2025 | `vendor_master.csv` |

## Process and operations

| Pattern | Where |
|---|---|
| Pasadena's requisition-to-PO cycle time is about three to four times longer than other plants | `po_lines.csv` dates, site PAS |
| Spend spikes during each plant's turnaround, with materials bought in the six weeks before | All sites, see `sites.csv` |
| Baton Rouge pump failures rise sharply in 2025, increasing seal and bearing demand | `work_orders.csv`, `wo_parts.csv` |

## Data quality problems (for Phase 3)

| Problem | Approximate extent |
|---|---|
| Same supplier under 1 to 4 vendor records with different spellings | 48 suppliers, 99 vendor records |
| Missing category code | About 15% of PO lines |
| Missing material number | About 10% of material lines (all service lines have none by design) |
| Inconsistent, abbreviated, and misspelled descriptions | Most lines |
| Vague descriptions with no item detail ("MISC LABOR", "SERVICES RENDERED") | About 3% of lines |
| Plant names typed several ways | About 4% of lines |
| Inconsistent units of measure ("EA", "Each", "ea", "LS") | About 7% of lines |
| Missing requisition dates | About 1% of lines |
| Decimal-point price errors (price 100 times too high) | A handful of lines |
| Missing tax IDs in the vendor master | About 20% of vendor records |
