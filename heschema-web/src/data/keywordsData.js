/**
 * HESchema Assertion Keywords Data & Specifications
 */

export const KEYWORDS_DATA = {
  compareFields: {
    id: 'compareFields',
    name: 'compareFields',
    vocabulary: 'Field Comparison v1',
    dialectUri: 'https://raw.githubusercontent.com/HarshPopat23/HESchema-/main/src/heschema/field-comparison-v1.json',
    summary: 'Asserts relational comparisons (eq, ne, lt, lte, gt, gte) between two RFC 6901 pointers within the instance document.',
    operands: [
      { name: 'left', type: 'RFC 6901 JSON Pointer', description: 'Starting pointer for the left operand.' },
      { name: 'right', type: 'RFC 6901 JSON Pointer', description: 'Starting pointer for the right operand.' },
      { name: 'operator', type: 'enum (eq, ne, lt, lte, gt, gte)', description: 'Comparison operation.' },
      { name: 'mode', type: 'enum (json, number, date)', description: 'Type semantics for comparison.' }
    ],
    modeDetails: [
      { mode: 'json', operators: 'eq, ne', description: 'Deep structural equality according to JSON Schema instance equality. Number aliases (1 and 1.0) match; booleans are distinct; object key order is immaterial.' },
      { mode: 'number', operators: 'eq, ne, lt, lte, gt, gte', description: 'Finite JSON numbers without coercion or tolerance. Strings or booleans fail immediately.' },
      { mode: 'date', operators: 'eq, ne, lt, lte, gt, gte', description: 'Chronological comparison of Gregorian ASCII dates YYYY-MM-DD from year 0001 to 9999. Timestamps and time offsets fail.' }
    ],
    edgeCases: [
      'Unresolved pointers (missing properties or out-of-bounds array indices) immediately fail evaluation.',
      'The empty pointer "" selects the root or current instance node.',
      'Under "items", pointers start at that specific array item.',
      'JSON null is treated as an existing value (distinct from missing).',
      'The keyword never creates properties or marks them as evaluated for unevaluatedProperties.'
    ],
    exampleSchema: {
      "$schema": "https://raw.githubusercontent.com/HarshPopat23/HESchema-/main/src/heschema/field-comparison-v1.json",
      "type": "object",
      "required": ["minReplicas", "maxReplicas"],
      "properties": {
        "minReplicas": { "type": "integer" },
        "maxReplicas": { "type": "integer" }
      },
      "compareFields": [
        { "left": "/minReplicas", "operator": "lte", "right": "/maxReplicas", "mode": "number" }
      ]
    },
    exampleInstanceValid: {
      "minReplicas": 2,
      "maxReplicas": 10
    },
    exampleInstanceInvalid: {
      "minReplicas": 12,
      "maxReplicas": 5
    },
    presets: [
      {
        name: 'Replica Scaling Bounds (number)',
        schema: {
          "compareFields": [
            { "left": "/minReplicas", "operator": "lte", "right": "/maxReplicas", "mode": "number" }
          ]
        },
        instance: { "minReplicas": 3, "maxReplicas": 10 },
        counterexample: { "minReplicas": 15, "maxReplicas": 4 }
      },
      {
        name: 'Event Booking Window (date)',
        schema: {
          "compareFields": [
            { "left": "/checkInDate", "operator": "lt", "right": "/checkOutDate", "mode": "date" }
          ]
        },
        instance: { "checkInDate": "2027-01-10", "checkOutDate": "2027-01-15" },
        counterexample: { "checkInDate": "2027-01-20", "checkOutDate": "2027-01-15" }
      },
      {
        name: 'Escaped Pointer JSON Match (json)',
        schema: {
          "type": "array",
          "items": {
            "compareFields": [
              { "left": "/id~1source", "right": "/id~0copy", "operator": "eq", "mode": "json" }
            ]
          }
        },
        instance: [{ "id/source": { "x": 1 }, "id~copy": { "x": 1.0 } }],
        counterexample: [{ "id/source": { "x": 1 }, "id~copy": { "x": 2 } }]
      }
    ]
  },

  uniqueKeys: {
    id: 'uniqueKeys',
    name: 'uniqueKeys',
    vocabulary: 'Keyed Uniqueness v1 (also included in Relationships v1/v2/v3/v4)',
    dialectUri: 'https://raw.githubusercontent.com/HarshPopat23/HESchema-/main/src/heschema/relationships-v1.json',
    summary: 'Asserts that array elements have distinct key tuples formed by resolving one or more RFC 6901 pointers per item.',
    operands: [
      { name: 'uniqueKeys', type: 'array of RFC 6901 pointers', description: 'Non-empty array of JSON Pointers resolving from each array item.' }
    ],
    modeDetails: [
      { mode: 'single-key', operators: 'tuple comparison', description: 'e.g. ["/sku"] ensures no two objects share the same sku field value.' },
      { mode: 'composite-key', operators: 'ordered tuple matching', description: 'e.g. ["/datasetId", "/sampleId"] permits duplicate sampleId across different datasets, but rejects identical (datasetId, sampleId) pairs.' }
    ],
    edgeCases: [
      'Missing pointer values contribute an internal distinct "missing" sentinel, different from JSON null.',
      'Two missing keys collide with each other (e.g. [{price: 1}, {price: 2}] duplicate on /sku).',
      'Non-array instances succeed by definition (ignored); empty arrays pass immediately.',
      'Array indices use canonical decimal representation without leading zeros.'
    ],
    exampleSchema: {
      "$schema": "https://raw.githubusercontent.com/HarshPopat23/HESchema-/main/src/heschema/relationships-v1.json",
      "type": "array",
      "items": {
        "type": "object",
        "required": ["datasetId", "sampleId"]
      },
      "uniqueKeys": ["/datasetId", "/sampleId"]
    },
    exampleInstanceValid: [
      { "datasetId": "cohort_A", "sampleId": "S001", "reading": 42.1 },
      { "datasetId": "cohort_B", "sampleId": "S001", "reading": 38.9 },
      { "datasetId": "cohort_A", "sampleId": "S002", "reading": 50.4 }
    ],
    exampleInstanceInvalid: [
      { "datasetId": "cohort_A", "sampleId": "S001", "reading": 42.1 },
      { "datasetId": "cohort_A", "sampleId": "S001", "reading": 99.0 }
    ],
    presets: [
      {
        name: 'Single Key: SKU Uniqueness',
        schema: { "uniqueKeys": ["/sku"] },
        instance: [{ "sku": "PROD-100", "price": 10 }, { "sku": "PROD-200", "price": 15 }],
        counterexample: [{ "sku": "PROD-100", "price": 10 }, { "sku": "PROD-100", "price": 20 }]
      },
      {
        name: 'Compound Key: Dataset & Sample IDs',
        schema: { "uniqueKeys": ["/datasetId", "/sampleId"] },
        instance: [
          { "datasetId": "train", "sampleId": "01" },
          { "datasetId": "eval", "sampleId": "01" }
        ],
        counterexample: [
          { "datasetId": "train", "sampleId": "01", "value": 1 },
          { "datasetId": "train", "sampleId": "01", "value": 2 }
        ]
      }
    ]
  },

  aggregateCompare: {
    id: 'aggregateCompare',
    name: 'aggregateCompare',
    vocabulary: 'Relationships v2',
    dialectUri: 'https://raw.githubusercontent.com/HarshPopat23/HESchema-/main/src/heschema/relationships-v2.json',
    summary: 'Asserts mathematical consistency between document properties, array lengths (count), and exact integer sums (sum).',
    operands: [
      { name: 'left', type: 'Pointer | Count | Sum', description: 'Left operand resolution' },
      { name: 'operator', type: 'eq | ne | lt | lte | gt | gte', description: 'Comparison operator' },
      { name: 'right', type: 'Pointer | Count | Sum', description: 'Right operand resolution' }
    ],
    modeDetails: [
      { mode: 'count', operators: '{"count": "/items"}', description: 'Evaluates to the exact length of the selected array.' },
      { mode: 'sum', operators: '{"sum": {"array": "/items", "item": "/minor"}}', description: 'Sums integer minor units across items without rounding or float drift.' },
      { mode: 'scalar integer', operators: '"/totalCount"', description: 'Resolves an exact integer at the pointer.' }
    ],
    edgeCases: [
      'Empty arrays count to 0 and sum to 0.',
      'Non-integer values (e.g. floats 0.5, booleans, numeric strings) fail immediately.',
      'Arbitrary precision integer tokens within parser limits are preserved without 64-bit IEEE overflow.'
    ],
    exampleSchema: {
      "$schema": "https://raw.githubusercontent.com/HarshPopat23/HESchema-/main/src/heschema/relationships-v2.json",
      "type": "object",
      "aggregateCompare": [
        { "left": "/itemCount", "operator": "eq", "right": { "count": "/items" } },
        { "left": "/totalMinor", "operator": "eq", "right": { "sum": { "array": "/items", "item": "/amountMinor" } } }
      ]
    },
    exampleInstanceValid: {
      "itemCount": 2,
      "items": [{ "amountMinor": 1200 }, { "amountMinor": 350 }],
      "totalMinor": 1550
    },
    exampleInstanceInvalid: {
      "itemCount": 2,
      "items": [{ "amountMinor": 1200 }, { "amountMinor": 350 }],
      "totalMinor": 2000
    },
    presets: [
      {
        name: 'Invoice Item Count & Total Minor Sum',
        schema: {
          "aggregateCompare": [
            { "left": "/itemCount", "operator": "eq", "right": { "count": "/items" } },
            { "left": "/totalMinor", "operator": "eq", "right": { "sum": { "array": "/items", "item": "/amountMinor" } } }
          ]
        },
        instance: {
          "itemCount": 3,
          "items": [{ "amountMinor": 100 }, { "amountMinor": 250 }, { "amountMinor": 400 }],
          "totalMinor": 750
        },
        counterexample: {
          "itemCount": 3,
          "items": [{ "amountMinor": 100 }, { "amountMinor": 250 }, { "amountMinor": 400 }],
          "totalMinor": 999
        }
      },
      {
        name: 'Balanced Batch Cardinality (features == labels)',
        schema: {
          "aggregateCompare": [
            { "left": { "count": "/features" }, "operator": "eq", "right": { "count": "/labels" } }
          ]
        },
        instance: {
          "features": [[1, 2], [3, 4], [5, 6]],
          "labels": [0, 1, 0]
        },
        counterexample: {
          "features": [[1, 2], [3, 4], [5, 6]],
          "labels": [0, 1]
        }
      }
    ]
  },

  localReferences: {
    id: 'localReferences',
    name: 'localReferences',
    vocabulary: 'Relationships v2',
    dialectUri: 'https://raw.githubusercontent.com/HarshPopat23/HESchema-/main/src/heschema/relationships-v2.json',
    summary: 'Asserts foreign key integrity between two arrays in the same instance document. Every source tuple must match exactly one target row.',
    operands: [
      { name: 'source', type: 'object { array, keys }', description: 'Source array pointer and array of key pointers per item.' },
      { name: 'target', type: 'object { array, keys }', description: 'Target array pointer and array of matching key pointers per item.' }
    ],
    modeDetails: [
      { mode: 'foreign-key', operators: 'exact 1-to-1 match', description: 'Requires each source item key tuple to resolve to exactly one target row.' },
      { mode: 'compound keys', operators: 'multi-part keys', description: 'e.g. ["/dataset", "/sample"] matched against ["/dataset", "/id"].' }
    ],
    edgeCases: [
      'Duplicate target tuples fail immediately, even if no source item references them.',
      'Repeated source references to the same target are allowed.',
      'Empty source referencing empty target passes.',
      'Missing pointers or null vs missing mismatches fail.'
    ],
    exampleSchema: {
      "$schema": "https://raw.githubusercontent.com/HarshPopat23/HESchema-/main/src/heschema/relationships-v2.json",
      "type": "object",
      "localReferences": [
        {
          "source": { "array": "/predictions", "keys": ["/datasetId", "/sampleId"] },
          "target": { "array": "/samples", "keys": ["/datasetId", "/id"] }
        }
      ]
    },
    exampleInstanceValid: {
      "predictions": [
        { "datasetId": "ds1", "sampleId": "01", "pred": 0.8 },
        { "datasetId": "ds1", "sampleId": "01", "pred": 0.82 }
      ],
      "samples": [
        { "datasetId": "ds1", "id": "01", "label": 1 },
        { "datasetId": "ds1", "id": "02", "label": 0 }
      ]
    },
    exampleInstanceInvalid: {
      "predictions": [
        { "datasetId": "ds1", "sampleId": "99", "pred": 0.8 }
      ],
      "samples": [
        { "datasetId": "ds1", "id": "01", "label": 1 }
      ]
    },
    presets: [
      {
        name: 'Predictions to Ground-Truth Samples',
        schema: {
          "localReferences": [
            {
              "source": { "array": "/predictions", "keys": ["/dataset", "/sample"] },
              "target": { "array": "/samples", "keys": ["/dataset", "/id"] }
            }
          ]
        },
        instance: {
          "predictions": [{ "dataset": "A", "sample": 1 }],
          "samples": [{ "dataset": "A", "id": 1 }]
        },
        counterexample: {
          "predictions": [{ "dataset": "A", "sample": 2 }],
          "samples": [{ "dataset": "A", "id": 1 }]
        }
      }
    ]
  },

  sortedBy: {
    id: 'sortedBy',
    name: 'sortedBy',
    vocabulary: 'Relationships v3',
    dialectUri: 'https://raw.githubusercontent.com/HarshPopat23/HESchema-/main/src/heschema/relationships-v3.json',
    summary: 'Asserts monotonic order (ascending or descending) across items in an array, with strict or non-strict tie rules.',
    operands: [
      { name: 'key', type: 'RFC 6901 Pointer', description: 'Pointer from each item to its comparison value.' },
      { name: 'mode', type: 'number | date | date-time', description: 'Coordinate comparison mode.' },
      { name: 'direction', type: 'ascending | descending', description: 'Required monotonic direction.' },
      { name: 'ties', type: 'allow | forbid', description: 'Whether consecutive equal values are permitted.' }
    ],
    modeDetails: [
      { mode: 'number', operators: 'ascending / descending', description: 'Finite numbers compared by numeric value.' },
      { mode: 'date', operators: 'ascending / descending', description: 'Chronological order of ASCII YYYY-MM-DD calendar dates.' },
      { mode: 'date-time', operators: 'instant ordering', description: 'RFC 3339 timestamps with zone offset normalized to UTC instants.' }
    ],
    edgeCases: [
      'Empty arrays or arrays with <= 1 item are sorted by definition (single item still must have valid key if present).',
      'Timestamps in different timezones representing the same instant are ties.',
      'Non-array instances succeed by definition (ignored).'
    ],
    exampleSchema: {
      "$schema": "https://raw.githubusercontent.com/HarshPopat23/HESchema-/main/src/heschema/relationships-v3.json",
      "type": "array",
      "sortedBy": { "key": "/timestamp", "mode": "date-time", "direction": "ascending", "ties": "forbid" }
    },
    exampleInstanceValid: [
      { "timestamp": "2026-01-01T10:00:00Z", "event": "boot" },
      { "timestamp": "2026-01-01T10:05:00Z", "event": "ready" }
    ],
    exampleInstanceInvalid: [
      { "timestamp": "2026-01-01T10:05:00Z", "event": "ready" },
      { "timestamp": "2026-01-01T10:00:00Z", "event": "boot" }
    ],
    presets: [
      {
        name: 'Ascending Numeric Sequence with Ties Allowed',
        schema: {
          "sortedBy": { "key": "/step", "mode": "number", "direction": "ascending", "ties": "allow" }
        },
        instance: [{ "step": 1 }, { "step": 1.0 }, { "step": 2 }, { "step": 5 }],
        counterexample: [{ "step": 1 }, { "step": 3 }, { "step": 2 }]
      },
      {
        name: 'Strict Descending Calendar Dates',
        schema: {
          "sortedBy": { "key": "", "mode": "date", "direction": "descending", "ties": "forbid" }
        },
        instance: ["2026-12-31", "2026-06-15", "2026-01-01"],
        counterexample: ["2026-12-31", "2026-12-31", "2026-01-01"]
      }
    ]
  },

  nonOverlapping: {
    id: 'nonOverlapping',
    name: 'nonOverlapping',
    vocabulary: 'Relationships v3',
    dialectUri: 'https://raw.githubusercontent.com/HarshPopat23/HESchema-/main/src/heschema/relationships-v3.json',
    summary: 'Asserts that intervals defined by start and end pointers across array items do not collide.',
    operands: [
      { name: 'start', type: 'RFC 6901 Pointer', description: 'Start coordinate pointer.' },
      { name: 'end', type: 'RFC 6901 Pointer', description: 'End coordinate pointer.' },
      { name: 'bounds', type: 'half-open | closed', description: 'half-open [start, end) or closed [start, end].' },
      { name: 'mode', type: 'number | date | date-time | byte-offset | code-point-offset', description: 'Coordinate space.' }
    ],
    modeDetails: [
      { mode: 'half-open', operators: '[start, end)', description: 'Adjacent intervals sharing an endpoint do not overlap (e.g. [0, 5) and [5, 10)).' },
      { mode: 'closed', operators: '[start, end]', description: 'Adjacent intervals sharing an endpoint overlap (e.g. [0, 5] and [5, 10] collide at 5).' },
      { mode: 'code-point-offset', operators: 'text span tokens', description: 'Zero-based Unicode code point indices.' }
    ],
    edgeCases: [
      'Reversed intervals (start > end) fail immediately.',
      'Empty intervals in half-open ([2, 2)) never overlap any interval.',
      'Input array order is immaterial; unsorted items are validated correctly without reordering.'
    ],
    exampleSchema: {
      "$schema": "https://raw.githubusercontent.com/HarshPopat23/HESchema-/main/src/heschema/relationships-v3.json",
      "type": "array",
      "nonOverlapping": {
        "start": "/start",
        "end": "/end",
        "mode": "code-point-offset",
        "bounds": "half-open"
      }
    },
    exampleInstanceValid: [
      { "start": 0, "end": 10, "tag": "INTRO" },
      { "start": 10, "end": 25, "tag": "BODY" }
    ],
    exampleInstanceInvalid: [
      { "start": 0, "end": 15, "tag": "INTRO" },
      { "start": 10, "end": 25, "tag": "BODY" }
    ],
    presets: [
      {
        name: 'Half-Open Text Spans [start, end)',
        schema: {
          "nonOverlapping": { "start": "/start", "end": "/end", "mode": "code-point-offset", "bounds": "half-open" }
        },
        instance: [{ "start": 0, "end": 5 }, { "start": 5, "end": 12 }],
        counterexample: [{ "start": 0, "end": 8 }, { "start": 4, "end": 12 }]
      },
      {
        name: 'Closed Byte Ranges [start, end]',
        schema: {
          "nonOverlapping": { "start": "/s", "end": "/e", "mode": "byte-offset", "bounds": "closed" }
        },
        instance: [{ "s": 0, "e": 4 }, { "s": 5, "e": 9 }],
        counterexample: [{ "s": 0, "e": 5 }, { "s": 5, "e": 9 }]
      }
    ]
  },

  arithmeticEquals: {
    id: 'arithmeticEquals',
    name: 'arithmeticEquals',
    vocabulary: 'Relationships v4',
    dialectUri: 'https://raw.githubusercontent.com/HarshPopat23/HESchema-/main/src/heschema/relationships-v4.json',
    summary: 'Asserts exact decimal arithmetic (add, subtract, multiply, divide, percentOf) using decimal string representations to prevent IEEE float inaccuracy.',
    operands: [
      { name: 'left', type: 'RFC 6901 Pointer', description: 'Left decimal string pointer.' },
      { name: 'right', type: 'RFC 6901 Pointer', description: 'Right decimal string pointer.' },
      { name: 'result', type: 'RFC 6901 Pointer', description: 'Result decimal string pointer.' },
      { name: 'operation', type: 'add | subtract | multiply | divide | percentOf', description: 'Calculation type.' },
      { name: 'rounding', type: 'optional { scale, mode }', description: 'scale (0-18), mode: half-even, half-up, toward-zero.' }
    ],
    modeDetails: [
      { mode: 'decimal strings', operators: 'string format', description: 'Operands must be decimal strings (e.g. "12.50"). Raw JSON numbers are rejected to prevent parser rounding.' },
      { mode: 'rounding modes', operators: 'half-even, half-up, toward-zero', description: 'Peppol and financial standards compliant.' }
    ],
    edgeCases: [
      'Maximum 38 digits allowed.',
      'Scientific notation ("1e1"), leading zeros ("01"), or whitespace are rejected.',
      'Division by zero fails in every mode.',
      'Trailing fractional zeros and negative zero compare by exact value.'
    ],
    exampleSchema: {
      "$schema": "https://raw.githubusercontent.com/HarshPopat23/HESchema-/main/src/heschema/relationships-v4.json",
      "type": "object",
      "arithmeticEquals": [
        {
          "left": "/quantity",
          "right": "/unitPrice",
          "operation": "multiply",
          "result": "/lineTotal",
          "rounding": { "scale": 2, "mode": "half-even" }
        }
      ]
    },
    exampleInstanceValid: {
      "quantity": "3",
      "unitPrice": "12.505",
      "lineTotal": "37.52"
    },
    exampleInstanceInvalid: {
      "quantity": "3",
      "unitPrice": "12.505",
      "lineTotal": "37.51"
    },
    presets: [
      {
        name: 'Peppol Invoice Line Multiplication',
        schema: {
          "arithmeticEquals": [
            {
              "left": "/qty",
              "right": "/price",
              "operation": "multiply",
              "result": "/total",
              "rounding": { "scale": 2, "mode": "half-even" }
            }
          ]
        },
        instance: { "qty": "4", "price": "19.99", "total": "79.96" },
        counterexample: { "qty": "4", "price": "19.99", "total": "80.00" }
      },
      {
        name: 'Tax Percentage Calculation (percentOf)',
        schema: {
          "arithmeticEquals": [
            {
              "left": "/subtotal",
              "right": "/taxRate",
              "operation": "percentOf",
              "result": "/taxAmount",
              "rounding": { "scale": 2, "mode": "half-up" }
            }
          ]
        },
        instance: { "subtotal": "200.00", "taxRate": "18", "taxAmount": "36.00" },
        counterexample: { "subtotal": "200.00", "taxRate": "18", "taxAmount": "35.50" }
      }
    ]
  },

  tensorShapes: {
    id: 'tensorShapes',
    name: 'tensorShapes',
    vocabulary: 'ML v1',
    dialectUri: 'https://raw.githubusercontent.com/HarshPopat23/HESchema-/main/src/heschema/ml-v1.json',
    summary: 'Asserts shape and rank alignment for dense multidimensional tensors encoded as nested JSON arrays.',
    operands: [
      { name: 'path', type: 'RFC 6901 Pointer', description: 'Pointer to the tensor array.' },
      { name: 'shape', type: 'array of dimensions', description: 'Dimensions can be fixed integers (e.g. 768), symbols ("batch"), or anonymous (null).' }
    ],
    modeDetails: [
      { mode: 'fixed dimension', operators: '768, 3, etc.', description: 'Every observed array on that axis must have this exact length.' },
      { mode: 'symbolic dimension', operators: '"batch", "seq_len"', description: 'Every appearance of the symbol across all tensors in this assertion must bind to the same observed length.' },
      { mode: 'anonymous dimension', operators: 'null', description: 'Dimension length may vary between tensors, but all slices within one tensor must be rectangular.' }
    ],
    edgeCases: [
      'Empty arrays bind dimension symbols to 0.',
      'Leaves must be scalars (numbers, booleans, or strings). Nested objects or nulls fail.',
      'Ragged arrays (irregular sub-lengths) fail rectangularity checks.'
    ],
    exampleSchema: {
      "$schema": "https://raw.githubusercontent.com/HarshPopat23/HESchema-/main/src/heschema/ml-v1.json",
      "type": "object",
      "tensorShapes": [
        { "path": "/embeddings", "shape": ["batch", 3] },
        { "path": "/labels", "shape": ["batch"] }
      ]
    },
    exampleInstanceValid: {
      "embeddings": [
        [0.1, 0.2, 0.3],
        [0.4, 0.5, 0.6]
      ],
      "labels": [1, 0]
    },
    exampleInstanceInvalid: {
      "embeddings": [
        [0.1, 0.2, 0.3],
        [0.4, 0.5, 0.6]
      ],
      "labels": [1]
    },
    presets: [
      {
        name: 'Shared Batch Dimension: Embeddings & Labels',
        schema: {
          "tensorShapes": [
            { "path": "/embeddings", "shape": ["batch", 3] },
            { "path": "/labels", "shape": ["batch"] }
          ]
        },
        instance: {
          "embeddings": [[1, 2, 3], [4, 5, 6]],
          "labels": [0, 1]
        },
        counterexample: {
          "embeddings": [[1, 2, 3]],
          "labels": [0, 1]
        }
      },
      {
        name: 'Anonymous 2D Rectangular Matrix (null, null)',
        schema: {
          "tensorShapes": [{ "path": "", "shape": [null, null] }]
        },
        instance: [[1, 2, 3], [4, 5, 6]],
        counterexample: [[1, 2, 3], [4, 5]]
      }
    ]
  }
};

