# Project Charter: Maintenance Spend Intelligence

**From data to decisions in maintenance procurement**

## Background

GulfChem Industries is a fictional specialty chemical company with five plants on the U.S. Gulf Coast: Baton Rouge and Lake Charles in Louisiana, and Freeport, Pasadena, and Conroe in Texas. The plants spend roughly $100 million a year on maintenance and industrial services across 12 categories, from valves and MRO parts to scaffolding, contractor labor, and inspection services. Each plant also runs a major turnaround every few years.

Procurement data sits in the ERP system, but it is messy: suppliers appear under several names, many purchase lines have no category, and descriptions are typed inconsistently. As a result, nobody has a reliable view of spend, supplier performance, or contract compliance.

## Problem statement

Maintenance spending has risen sharply over the past three years, and leadership cannot explain why. Procurement needs to determine whether the increase comes from market prices, higher volume, buying outside contracts, supplier billing errors, or process problems, and then act on it.

## Objective

Build an analytics capability that turns maintenance procurement data into measurable business value: savings, cost avoidance, working capital improvement, and lower supply risk.

## Key business questions

| Analytics level | Question |
|---|---|
| Descriptive | What do we spend, with whom, at which plants, and how well do suppliers perform? |
| Diagnostic | Why did spend rise? Where is money leaking outside contracts or through billing errors? |
| Predictive | Where are prices heading? Which suppliers are becoming risky? What spare parts will we need? |
| Prescriptive | Which suppliers should get our volume? When should we lock in prices? How much inventory should we hold? |
| Autonomous | Which checks can run automatically, with a human approving the actions? |

## Stakeholders

| Stakeholder | Interest |
|---|---|
| Procurement leadership | Savings, contract compliance, supplier risk |
| Plant and maintenance managers | Reliable suppliers, fast purchasing, no production delays |
| Turnaround managers | Contractor capacity and cost control during shutdowns |
| Finance | Verified savings, EBITDA impact, working capital |
| Accounts payable | Accurate invoices, fewer disputes |
| Health, safety and environment | Qualified contractors with valid safety records and insurance |

## Key performance indicators

| KPI | Definition |
|---|---|
| Total spend | Sum of PO line amounts, by site, category, supplier, and month |
| Spend under contract | Share of spend placed on an active contract |
| Contract leakage | Spend that should have gone through a contract but did not, plus overbilling against contract terms |
| Price variance | Difference between prices paid and the best or contracted price for the same item |
| On-time delivery | Share of receipts delivered on or before the promised date |
| PO cycle time | Days from requisition to purchase order |
| Days payable outstanding | Average days from invoice to payment, compared with contract terms |
| Identified value | Dollar value of recommendations, split into hard savings, cost avoidance, and working capital |

## Scope

**In scope:** maintenance and industrial services spend for five plants, January 2023 to December 2025; purchase orders, goods receipts, invoices, contracts, supplier master data, and maintenance work orders.

**Out of scope:** direct materials (raw materials and packaging), capital projects, and non-maintenance indirect spend.

## Data approach

Real procurement data is confidential, so internal data is synthetic, generated to reflect how ERP and procurement systems actually behave, including realistic data quality problems. Price movements follow real U.S. Bureau of Labor Statistics price indices from FRED. All company and supplier names are fictional.

## Deliverables

1. Clean, classified spend data in a SQL star schema
2. Power BI dashboard covering spend, suppliers, compliance, and process efficiency
3. Diagnostic analysis quantifying the drivers of spend growth and leakage
4. Predictive models for prices, supplier risk, and spare parts demand
5. Prescriptive recommendations with a quantified business case
6. A prototype invoice audit agent with human approval
7. Executive summary and presentation

## Success criteria

The project succeeds if it produces a prioritized list of actions, each with a dollar value, an owner, and a next step, that a procurement leader could act on immediately.
