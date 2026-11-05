# Relationships v4

The [Relationships v4 meta-schema](../../../src/heschema/relationships-v4.json) includes [Relationships v3](../v3/README.md) and adds `arithmeticEquals`. Use its `$id` as the root `$schema`. The [ML profile](../../ml/v1/README.md) has its own dialect.

## `arithmeticEquals`

Write a nonempty array of rules. Each rule has `left`, `right`, `operation`, and `result`. The three pointers follow RFC 6901 and start at the instance evaluated by the schema containing this keyword. An empty pointer selects that instance. Missing values fail. Each rule verifies the supplied result and leaves the instance intact.

```json
{
  "$schema": "https://raw.githubusercontent.com/HarshPopat23/HESchema-/main/src/heschema/relationships-v4.json",
  "type": "object",
  "arithmeticEquals": [
    {
      "left": "/quantity",
      "right": "/unitPrice",
      "operation": "multiply",
      "result": "/lineTotal",
      "rounding": {"scale": 2, "mode": "half-even"}
    }
  ]
}
```

This accepts `{"quantity":"3","unitPrice":"12.505","lineTotal":"37.52"}`. To validate a unit conversion, multiply by a supplied conversion factor or divide by the supplied denominator. To check a tax or discount amount, use the base amount on the left and the rate on the right.

| Operation | Exact calculation |
| --- | --- |
| `add` | left + right |
| `subtract` | left − right |
| `multiply` | left × right |
| `divide` | left ÷ right |
| `percentOf` | left × right ÷ 100. A rate of `"20"` means 20 percent. |

### Representation and limits

Operands and results are decimal **strings**. They contain an optional ASCII minus, an integer part of `0` or a nonzero digit followed by digits, and optionally a decimal point followed by 1–18 digits. The total digit limit is 38, counting the zero before a decimal point. A plus sign, whitespace, exponent notation, and leading integer zeros are invalid. JSON numbers are outside this profile because a parser may already have rounded their digits before validation. Trailing fractional zeros and negative zero are accepted and compare by numeric value.

Compute the operation as an exact rational number. There is no fixed-width intermediate overflow, wrapping, or saturation. The final exact or rounded value must fit the decimal format above. A repeating quotient fails unless rounding is declared. Division by any spelling of zero fails in every mode.

### Rounding

Omit `rounding` to compare the exact result. When supplied, give an integer `scale` from 0 through 18 and one of these modes:

- `half-even` chooses the nearest value at that scale. Ties select the result whose last retained digit is even.
- `half-up` chooses the nearest value. Ties go away from zero for both signs.
- `toward-zero` discards fractional digits beyond that scale for both signs.

Round once after the entire operation, then compare numeric values. For example, a rounded result of `"2.50"` matches `"2.5"`. Add a standard `pattern` if you also need an exact number of displayed decimal places.

Use HESchema's local Python `jsonschema` backend for this dialect. The existing contract arithmetic rules still support integer minor units and opt-in computation. `arithmeticEquals` checks the submitted value. Its conformance vectors are [available as JSON](cases.json).

## Design references

Great Expectations illustrates reconciliation rules. Peppol invoice lines illustrate quantity, unit pricing, and explicit rounding requirements. General Decimal Arithmetic and Java's rounding modes informed the decimal rules. RFC 8259 discusses interoperability limits for JSON numbers, and Python documents how converting a binary float to a decimal can preserve an already-rounded value.

[Great Expectations integrity](https://docs.greatexpectations.io/docs/reference/learn/data_quality_use_cases/integrity/) · [Peppol invoice lines](https://docs.peppol.eu/poacc/billing/3.0/syntax/ubl-invoice/cac-InvoiceLine/) · [General Decimal Arithmetic](https://speleotrove.com/decimal/decarith.html) · [Java rounding modes](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/math/RoundingMode.html) · [RFC 8259](https://www.rfc-editor.org/rfc/rfc8259#section-6) · [Python decimal](https://docs.python.org/3/library/decimal.html)
