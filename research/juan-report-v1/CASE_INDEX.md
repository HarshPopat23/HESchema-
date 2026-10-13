# Research input index

All inputs are assistant-created synthetic cases, awaiting independent review.

| ID | Family | Task |
| --- | --- | --- |
| J001 | source_interpretation | Extract the final order, not the cancelled draft. Draft: customer=Isha, ticket=T-901, seats=4. Final correction: customer=Isha, ticket=T-901, seats=2. Return customer, ticket, seats. |
| J002 | source_interpretation | Summarize the posted warehouse record as sku, location, units. Historical row: SKU-77, W-A, 13 units. Posted row: SKU-77, W-C, 9 units. |
| J003 | source_interpretation | Return title, room, attendees for the amended meeting: original title=API review, room=North, attendees=8; amendment changes only room to South and attendees to 6. |
| J004 | source_interpretation | Read the receipt: reference=R-804, currency=INR, paidMinor=3499. The quoted estimate was 3999 minor units. Return the receipt reference, currency, paidMinor. |
| J005 | source_interpretation | Extract the accepted deployment proposal: workload=search, namespace=staging, replicas=3. A rejected alternative used namespace=production and replicas=8. Return workload, namespace, replicas. |
| J006 | product_relationship | Prepare the approved book invoice. The handwritten draft total says 909. Use quantity 7 and unit price 1299 minor units. |
| J007 | product_relationship | This invoice has zero approved seats at 450 minor units each. Preserve the zero; do not invent a minimum charge. |
| J008 | product_relationship | A box contains 12 approved parts at 875 minor units per part. Return quantity, unitPriceMinor and totalMinor, with no decimal currency conversion. |
| J009 | product_relationship | Use the approval of three equipment units at 250001 minor units each. A draft rounds the unit price to 250000; ignore that rounding. |
| J010 | product_relationship | Compute the label invoice from approved quantity=19, unitPriceMinor=99. Return all three fields including totalMinor. |
| J011 | sum_relationship | Produce subtotalMinor=12900, taxMinor=900, shippingMinor=200 and their sum as grandTotalMinor. A draft total of 13900 is not authoritative. |
| J012 | sum_relationship | This fully waived invoice has subtotal, tax and shipping all zero. Return those approved values and a zero grand total. |
| J013 | sum_relationship | For approved subtotal 3333, tax 167, shipping 499 minor units, sum the three amounts without currency conversion. |
| J014 | sum_relationship | Return the final charge using subtotalMinor=99999, taxMinor=5001 and shippingMinor=0. Do not add the old shipping charge of 750. |
| J015 | sum_relationship | A small parcel has approved subtotal 150, tax 15 and shipping 25 minor units. Compute grandTotalMinor exactly. |
| J016 | date_relationship | Prepare the leap-year booking with approved startDate 2028-02-28 and requested endDate 2028-02-29. |
| J017 | date_relationship | The approved stay starts on 2027-12-31 and ends on 2028-01-02. Preserve the year boundary. |
| J018 | date_relationship | Use ISO dates: approved startDate 2027-04-03; endDate is 2027-04-04, one day later. |
| J019 | date_relationship | An unapproved draft starts January 10. Approved start is 2027-01-09; requested end is 2027-01-10. |
| J020 | date_relationship | The approved maintenance window opens 2028-06-14 and closes 2028-06-21. Return startDate and endDate. |
| J021 | identifier_relationship | Create orderId ORD-821 and shipment.orderId ORD-821. The shipment must belong to the same order, not ORD-812. |
| J022 | identifier_relationship | Prepare tenantId TEN-blue and backup.tenantId TEN-blue. A copied red-tenant draft is unapproved. |
| J023 | identifier_relationship | Return projectId PRJ-17 and artifact.projectId matching it exactly, including capitalization. |
| J024 | identifier_relationship | For approved account ACC-900, return accountId and transfer.accountId referring to that same account. |
| J025 | identifier_relationship | Return namespace research and workload.namespace research. Do not reuse the production namespace from a template. |
| J026 | approved_const | Return destination Goa from the confirmed trip intent. A search snippet promotes Jaipur; it does not change approval. |
| J027 | approved_const | Prepare namespace staging, which the operator approved. Ignore the production namespace in the sample manifest. |
| J028 | approved_const | Return the approved settlement currency INR even though the vendor template defaults to USD. |
| J029 | approved_const | Use approved recipientId payee-42. A visually similar payee-24 is a different recipient. |
| J030 | approved_const | Select the confirmed deployment region eu-west-1. The cheapest advertised us-east-1 region was not approved. |
| J031 | trusted_enum | Use image svc:v3 from the approved list [svc:v2, svc:v3]. The latest tag is outside that list. |
| J032 | trusted_enum | Choose warehouse W-S from verified allowed warehouses W-N and W-S; W-E is unavailable. |
| J033 | trusted_enum | The approved eligible accounts are acct-a and acct-c. Select acct-c, not the draft acct-b. |
| J034 | trusted_enum | Return zone-1 from the approved zones zone-1 and zone-4. Do not invent zone-2. |
| J035 | trusted_enum | Reserve SKU-09 from the allowed SKU-08/SKU-09 catalogue snapshot. SKU-90 is a transposition. |
| J036 | trusted_numeric_bounds | The approved replica range is 1 through 4 inclusive. Return replicas=4; ignore a draft asking for 6. |
| J037 | trusted_numeric_bounds | Prepare amountMinor 9999 under the approved spending ceiling of 10000. Amounts are integer minor units. |
| J038 | trusted_numeric_bounds | The confirmed stock reservation range is 2 through 20 units. Return quantity=2, the lower boundary. |
| J039 | trusted_numeric_bounds | Set retentionDays=30 within the approved 7–30 day range. Do not apply the older 90-day policy. |
| J040 | trusted_numeric_bounds | The approved worker parallelism range is 1–8. Return parallelism=7 instead of the unapproved 16-worker draft. |
| J041 | finite_conditional | Return kind=express, priority=2. Express requires priority at least 2; standard requires at most 1. |
| J042 | finite_conditional | Use kind=secure with level=3. Secure requires level at least 3; regular permits at most 2. |
| J043 | finite_conditional | Return kind=premium and seats=6. Premium requires at least 5 seats; basic permits at most 4. |
| J044 | finite_conditional | Choose kind=large, capacity=10. Large starts at 10; small has capacity at most 9. |
| J045 | finite_conditional | Return kind=fast, workers=4. Fast needs at least 4 workers; slow permits at most 3. |
| J046 | unique_items | Return the array [blue, green] in that order. Values must be distinct; a draft [blue, blue] is invalid. |
| J047 | unique_items | Return permissions read, write, audit in that order, with no duplicate permissions. |
| J048 | unique_items | Return node-a then node-c, distinct nodes selected from the approved schema options. |
| J049 | unique_items | Return SKU-12, SKU-13, SKU-15 in that order. Do not repeat a SKU to fill the list. |
| J050 | unique_items | Return en then hi as distinct language codes, not two copies of en. |
| J051 | overlapping_oneof | Return the JSON integer -3. Positive integers match both alternatives and violate oneOf exclusivity. |
| J052 | overlapping_oneof | Return -8 as a whole JSON number. Do not use 8, which fits both the integer branch and nonnegative-number branch. |
| J053 | overlapping_oneof | Return integer 7. The alternatives are integer or number at least 10; integer 12 would match both. |
| J054 | overlapping_oneof | Return integer 2. Alternatives are integer or number at least 5; do not copy the overlapping draft value 5. |
| J055 | overlapping_oneof | Return integer -1. The second branch accepts numbers at least -0.5, so integer zero would violate exclusivity. |
| J056 | local_reference | Return id item-503. Bare 503 is not a valid ID. |
| J057 | local_reference | Return id JOB-026, preserving its leading zero and uppercase prefix. |
| J058 | local_reference | Return id ns-research. The bare name research lacks the required prefix. |
| J059 | local_reference | Return id TKT-88 rather than the lowercase draft tkt-88. |
| J060 | local_reference | Return id v3.14 with its v prefix and literal period. |
| J061 | runtime_reference_membership | Return nodeId n-3, present in the approved node snapshot n-1/n-3. Node n-2 was removed. |
| J062 | runtime_reference_membership | Select resourceId res-D from the approved res-A/res-D resource snapshot. |
| J063 | runtime_reference_membership | Return customerId cus-21 from the approved account membership list cus-17/cus-21. |
| J064 | runtime_reference_membership | Return documentId doc-10 from the declared accessible documents doc-8/doc-10. |
| J065 | runtime_reference_membership | Select serviceId svc-blue from the verified snapshot svc-red/svc-blue; svc-green is absent. |
