# Unit economics / cohorts

1. Define unit (order, paying customer, subscription month, item, billable hour, contract). Separate user, account, transaction and paid seat. Model multiple units for multi-sided platforms.
2. Contribution per unit = recognized net sales less **all avoidable variable costs** (COGS, platform fees, variable service/support, payment processing, per-unit acquisition if incremental). Gross margin may differ; show both.
3. CAC = acquisition+sales outlays attributable to *new paying cohorts* / newly acquired paying customers. For freemium, allocate costs of recruiting/free-serving cohorts that convert; do not present paid-only processing costs as CAC. Report blended/channel/fully-loaded CAC and period.
4. Cohort retention = active customers from a specified signup cohort at t / eligible initial cohort. Paid churn, revenue churn, voluntary vs involuntary cancellation, reacquisition and reactivation differ. Use observed month-by-month retention where available; assumptions otherwise.
5. LTV in **contribution money**: sum of expected contribution across future paid periods adjusted for survival and discounts where applicable. For stationary retention r and monthly contribution c, approximate infinite-horizon LTV=c/(1-r); if r=1 it diverges, so require finite horizon. Do not conflate LTV with annual ARPU or nominal receipts.
6. LTV/CAC must use the same customer definition, geography and comparable cohorts. CAC payback uses contribution margin, not gross subscription receipts. Display assumptions alongside multiple.
7. For seasonal or lumpy business, forecast cash via explicit paid cohorts; don't assume an active paid user purchases 12 months unless evidence supports it.
8. Report CAC/LTV upside/downside and largest unknown driver; flag high assumed conversion, high retention or low CAC absent transaction data.
