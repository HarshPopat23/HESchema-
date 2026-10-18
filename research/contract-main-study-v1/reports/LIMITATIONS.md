# Study Boundaries and Limitations

This evaluation adheres strictly to the evidence boundaries defined in the study protocol:

1. **Dataset Scope**:
   - The dataset contains 100 researcher-authored tasks adapted from real public records.
   - Five source ecosystems (WfCommons, USGS, Citi Bike GBFS, Crossref, PyPI) and six authored task families.
   - The 20 workflow cases reuse previously inspected source material and represent exploratory reuse, not an untouched holdout.
   - Related records, shared responses, and repeated templates are correlated; 3 repeats per task do not produce independent tasks.

2. **Non-Claims**:
   - This experiment does **not** represent a survey of the entire internet or proof of a new vocabulary's universal necessity.
   - No claim of human review or publisher endorsement is made; `confirmed: true` reflects mechanical approval within this offline benchmark.
   - The benchmark does not adequately cover date ordering, currency rounding, arbitrary products, user authorization, live availability, transactional state, arbitrary graph validation, or prompt injection.

3. **Component Attribution**:
   - The primary comparison measures the whole contract package (rule representation, context projection, validation, and feedback).
   - Any observed benefit cannot be attributed solely to new vocabulary keywords without evaluating equivalent application checks (Control D) and projected schema constraints (Control C).
