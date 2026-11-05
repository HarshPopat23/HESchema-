# Relationships v3

The [Relationships v3 meta-schema](../../../src/heschema/relationships-v3.json) adds `sortedBy` and `nonOverlapping` to the four assertions in [Relationships v2](../v2/README.md). Use its `$id` as the root `$schema`. Both new assertions apply to arrays. They succeed on empty arrays and are ignored for other instance types. Use `type: array` to require an array. Each JSON Pointer starts at its array item. The empty pointer selects the whole item.

## `sortedBy`

Require one key per item and compare adjacent keys in the array's submitted order.

```json
{
  "$schema": "https://raw.githubusercontent.com/HarshPopat23/HESchema-/main/src/heschema/relationships-v3.json",
  "type": "array",
  "sortedBy": {"key": "/at", "mode": "date-time", "direction": "ascending", "ties": "forbid"}
}
```

Set `direction` to `ascending` or `descending`. Set `ties` to `allow` for non-strict ordering or `forbid` for strict ordering. Equal keys in different timestamp offsets are ties when they represent the same instant. Even a one-item array must supply a valid key.

## `nonOverlapping`

Select a start and end for each item. Input order is immaterial, and the validator does not reorder the document.

```json
{
  "$schema": "https://raw.githubusercontent.com/HarshPopat23/HESchema-/main/src/heschema/relationships-v3.json",
  "type": "array",
  "nonOverlapping": {
    "start": "/start", "end": "/end",
    "mode": "code-point-offset", "bounds": "half-open"
  }
}
```

- `half-open` means **[start, end)**. Adjacent intervals can share a boundary. Equal endpoints describe an empty interval and never overlap.
- `closed` means **[start, end]**. Adjacent intervals sharing a boundary overlap. Equal endpoints describe an interval containing one point.
- Reversed, malformed, or missing endpoints fail. To check multiple documents, schedules, or resources independently, apply the assertion to each resource's own array.

## Coordinate modes

| Mode | Available on | Meaning |
| --- | --- | --- |
| `number` | `sortedBy` | Finite JSON numbers, with no coercion of strings or booleans. |
| `date` | Both | Gregorian calendar dates in ASCII `YYYY-MM-DD` form, years 0001–9999. |
| `date-time` | Both | Gregorian timestamps with uppercase `T`, seconds, and explicit uppercase `Z` or a numeric UTC offset. Compare instants after applying the offset and retain all fractional-second digits. Leap seconds and zone-less times are outside this profile. |
| `byte-offset` | `nonOverlapping` | Nonnegative, zero-based integer coordinates measured in bytes of the source encoding. |
| `code-point-offset` | `nonOverlapping` | Nonnegative, zero-based integer coordinates measured in Unicode code points. A combining mark occupies its own code point. |

The two offset modes explicitly declare the coordinate unit. Both check overlap in the supplied coordinates. Source length, text normalization, and byte or grapheme boundaries require a separate source-aware check. HESchema accepts integer tokens within its parser limits and integral parsed floating-point offsets within the safe integer range.

Use the Python `jsonschema` backend for local validation or prompt-only generation. The custom dialect supports same-resource static JSON Pointer schema references and one root dialect declaration. Blaze and native provider generation reject the custom dialect.

[Conformance vectors](cases.json) provide schema fragments and expected validity. Apply the v3 dialect at the root.

## Prior art

Pandas supports monotonic ordering with equal consecutive values. PostgreSQL defines inclusive and exclusive range bounds. iCalendar events and Web Annotation text selectors use an inclusive start and exclusive end. Web Annotation distinguishes code-point positions for text from byte positions for data. The timestamp profile uses RFC 3339 syntax with the restrictions above.

[Pandas monotonicity](https://pandas.pydata.org/docs/reference/api/pandas.Series.is_monotonic_increasing.html) · [PostgreSQL ranges](https://www.postgresql.org/docs/current/rangetypes.html#RANGETYPES-INCLUSIVITY) · [iCalendar event bounds](https://www.rfc-editor.org/rfc/rfc5545#section-3.6.1) · [Web Annotation selectors](https://www.w3.org/TR/annotation-model/#selectors) · [RFC 3339 timestamps](https://www.rfc-editor.org/rfc/rfc3339#section-5.6)
