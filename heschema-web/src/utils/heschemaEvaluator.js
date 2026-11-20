/**
 * HESchema Client-Side Assertion & Pointer Evaluator
 * Implements RFC 6901 JSON Pointer resolution and HESchema custom vocabulary semantics:
 * - compareFields (v1)
 * - uniqueKeys (v1)
 * - aggregateCompare (v2)
 * - localReferences (v2)
 * - sortedBy (v3)
 * - nonOverlapping (v3)
 * - arithmeticEquals (v4)
 * - tensorShapes (ml-v1)
 */

export function resolvePointer(doc, pointer) {
  if (pointer === '' || pointer === undefined || pointer === null) {
    return { found: true, value: doc };
  }
  if (!pointer.startsWith('/')) {
    return { found: false, error: `Invalid RFC 6901 pointer: must start with / or be empty` };
  }

  const parts = pointer.slice(1).split('/').map(part => part.replace(/~1/g, '/').replace(/~0/g, '~'));
  let current = doc;

  for (const part of parts) {
    if (current === null || current === undefined || typeof current !== 'object') {
      return { found: false, error: `Cannot resolve '${part}' on non-object value` };
    }
    if (Array.isArray(current)) {
      if (part === '-') {
        return { found: false, error: `Array append token '-' cannot resolve to existing value` };
      }
      const idx = Number(part);
      if (!/^(0|[1-9]\d*)$/.test(part) || isNaN(idx) || idx < 0 || idx >= current.length) {
        return { found: false, error: `Array index out of bounds or non-canonical: ${part}` };
      }
      current = current[idx];
    } else {
      if (!Object.prototype.hasOwnProperty.call(current, part)) {
        return { found: false, error: `Property '${part}' does not exist` };
      }
      current = current[part];
    }
  }

  return { found: true, value: current };
}

function jsonEqual(a, b) {
  if (typeof a === 'number' && typeof b === 'number') {
    return Object.is(a, b) || a === b;
  }
  if (typeof a !== typeof b) return false;
  if (a === null || b === null) return a === b;
  if (typeof a !== 'object') return a === b;

  if (Array.isArray(a) !== Array.isArray(b)) return false;
  if (Array.isArray(a)) {
    if (a.length !== b.length) return false;
    for (let i = 0; i < a.length; i++) {
      if (!jsonEqual(a[i], b[i])) return false;
    }
    return true;
  }

  const keysA = Object.keys(a);
  const keysB = Object.keys(b);
  if (keysA.length !== keysB.length) return false;
  for (const k of keysA) {
    if (!Object.prototype.hasOwnProperty.call(b, k)) return false;
    if (!jsonEqual(a[k], b[k])) return false;
  }
  return true;
}

function isValidDate(str) {
  if (typeof str !== 'string') return false;
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(str);
  if (!match) return false;
  const y = parseInt(match[1], 10);
  const m = parseInt(match[2], 10);
  const d = parseInt(match[3], 10);
  if (y < 1 || y > 9999 || m < 1 || m > 12 || d < 1 || d > 31) return false;
  const daysInMonth = [31, (y % 4 === 0 && (y % 100 !== 0 || y % 400 === 0)) ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  return d <= daysInMonth[m - 1];
}

function parseDateTime(str) {
  if (typeof str !== 'string') return null;
  const regex = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(\.\d+)?(Z|([+-]\d{2}:\d{2}))$/;
  const m = regex.exec(str);
  if (!m) return null;
  const date = new Date(str);
  if (isNaN(date.getTime())) return null;
  return date.getTime();
}

export function evaluateCompareFields(rules, instance) {
  if (!Array.isArray(rules) || rules.length === 0) {
    return { valid: false, errors: ['compareFields must be a non-empty array of rules'] };
  }
  const errors = [];
  const logs = [];

  for (let i = 0; i < rules.length; i++) {
    const rule = rules[i];
    const { left, right, operator, mode } = rule;
    const lRes = resolvePointer(instance, left);
    const rRes = resolvePointer(instance, right);

    if (!lRes.found) {
      errors.push(`Rule ${i}: Left pointer '${left}' could not be resolved: ${lRes.error}`);
      continue;
    }
    if (!rRes.found) {
      errors.push(`Rule ${i}: Right pointer '${right}' could not be resolved: ${rRes.error}`);
      continue;
    }

    const lVal = lRes.value;
    const rVal = rRes.value;

    if (mode === 'json') {
      if (operator !== 'eq' && operator !== 'ne') {
        errors.push(`Rule ${i}: mode 'json' only supports 'eq' and 'ne', found '${operator}'`);
        continue;
      }
      const eq = jsonEqual(lVal, rVal);
      const passed = (operator === 'eq' && eq) || (operator === 'ne' && !eq);
      logs.push({ rule: i, left: lVal, right: rVal, operator, mode, passed });
      if (!passed) {
        errors.push(`Rule ${i} failed: ${JSON.stringify(lVal)} ${operator} ${JSON.stringify(rVal)} in mode '${mode}'`);
      }
    } else if (mode === 'number') {
      if (typeof lVal !== 'number' || typeof rVal !== 'number' || !Number.isFinite(lVal) || !Number.isFinite(rVal)) {
        errors.push(`Rule ${i}: mode 'number' requires finite JSON numbers, received left=${typeof lVal}, right=${typeof rVal}`);
        continue;
      }
      let passed = false;
      if (operator === 'eq') passed = lVal === rVal;
      else if (operator === 'ne') passed = lVal !== rVal;
      else if (operator === 'lt') passed = lVal < rVal;
      else if (operator === 'lte') passed = lVal <= rVal;
      else if (operator === 'gt') passed = lVal > rVal;
      else if (operator === 'gte') passed = lVal >= rVal;
      logs.push({ rule: i, left: lVal, right: rVal, operator, mode, passed });
      if (!passed) {
        errors.push(`Rule ${i} failed: ${lVal} ${operator} ${rVal}`);
      }
    } else if (mode === 'date') {
      if (!isValidDate(lVal) || !isValidDate(rVal)) {
        errors.push(`Rule ${i}: mode 'date' requires ASCII YYYY-MM-DD dates, got left='${lVal}', right='${rVal}'`);
        continue;
      }
      let passed = false;
      if (operator === 'eq') passed = lVal === rVal;
      else if (operator === 'ne') passed = lVal !== rVal;
      else if (operator === 'lt') passed = lVal < rVal;
      else if (operator === 'lte') passed = lVal <= rVal;
      else if (operator === 'gt') passed = lVal > rVal;
      else if (operator === 'gte') passed = lVal >= rVal;
      logs.push({ rule: i, left: lVal, right: rVal, operator, mode, passed });
      if (!passed) {
        errors.push(`Rule ${i} failed: '${lVal}' ${operator} '${rVal}'`);
      }
    } else {
      errors.push(`Rule ${i}: Unknown mode '${mode}'`);
    }
  }

  return { valid: errors.length === 0, errors, logs };
}

export function evaluateUniqueKeys(pointers, instance) {
  if (!Array.isArray(instance)) {
    return { valid: true, logs: ['Ignored for non-array instance (success by definition)'] };
  }
  if (instance.length === 0) {
    return { valid: true, logs: ['Empty array passes uniqueKeys'] };
  }
  if (!Array.isArray(pointers) || pointers.length === 0) {
    return { valid: false, errors: ['uniqueKeys keyword requires a non-empty array of pointers'] };
  }

  const seenTuples = [];
  const errors = [];
  const logs = [];

  for (let idx = 0; idx < instance.length; idx++) {
    const item = instance[idx];
    const tuple = [];
    for (const ptr of pointers) {
      const res = resolvePointer(item, ptr);
      if (res.found) {
        tuple.push({ present: true, value: res.value });
      } else {
        tuple.push({ present: false });
      }
    }

    const dupIndex = seenTuples.findIndex(existing => {
      if (existing.length !== tuple.length) return false;
      for (let k = 0; k < tuple.length; k++) {
        if (existing[k].present !== tuple[k].present) return false;
        if (existing[k].present && !jsonEqual(existing[k].value, tuple[k].value)) return false;
      }
      return true;
    });

    if (dupIndex !== -1) {
      errors.push(`Duplicate key tuple at index ${idx} matches index ${dupIndex}: ${JSON.stringify(tuple)}`);
    } else {
      seenTuples.push(tuple);
    }
  }

  return { valid: errors.length === 0, errors, logs: [`Checked ${instance.length} items with key pointers: ${pointers.join(', ')}`] };
}

export function evaluateAggregateCompare(rules, instance) {
  if (!Array.isArray(rules) || rules.length === 0) {
    return { valid: false, errors: ['aggregateCompare must be a non-empty array'] };
  }
  const errors = [];
  const logs = [];

  function evalOperand(op) {
    if (typeof op === 'string') {
      const res = resolvePointer(instance, op);
      if (!res.found) throw new Error(`Pointer '${op}' not found: ${res.error}`);
      if (typeof res.value !== 'number' || !Number.isInteger(res.value)) {
        throw new Error(`Pointer '${op}' must resolve to an exact integer, got ${typeof res.value} (${res.value})`);
      }
      return res.value;
    }
    if (typeof op === 'object' && op !== null) {
      if (op.count) {
        const res = resolvePointer(instance, op.count);
        if (!res.found) throw new Error(`count pointer '${op.count}' not found: ${res.error}`);
        if (!Array.isArray(res.value)) throw new Error(`count target '${op.count}' must be an array`);
        return res.value.length;
      }
      if (op.sum) {
        const arrRes = resolvePointer(instance, op.sum.array);
        if (!arrRes.found) throw new Error(`sum array pointer '${op.sum.array}' not found`);
        if (!Array.isArray(arrRes.value)) throw new Error(`sum target '${op.sum.array}' must be an array`);
        let total = 0;
        for (let j = 0; j < arrRes.value.length; j++) {
          const itemRes = resolvePointer(arrRes.value[j], op.sum.item);
          if (!itemRes.found) throw new Error(`sum item pointer '${op.sum.item}' missing at index ${j}`);
          if (typeof itemRes.value !== 'number' || !Number.isInteger(itemRes.value)) {
            throw new Error(`sum item '${op.sum.item}' at index ${j} must be integer, got ${itemRes.value}`);
          }
          total += itemRes.value;
        }
        return total;
      }
    }
    throw new Error(`Unsupported operand format: ${JSON.stringify(op)}`);
  }

  for (let i = 0; i < rules.length; i++) {
    const { left, operator, right } = rules[i];
    try {
      const lVal = evalOperand(left);
      const rVal = evalOperand(right);
      let passed = false;
      if (operator === 'eq') passed = lVal === rVal;
      else if (operator === 'ne') passed = lVal !== rVal;
      else if (operator === 'lt') passed = lVal < rVal;
      else if (operator === 'lte') passed = lVal <= rVal;
      else if (operator === 'gt') passed = lVal > rVal;
      else if (operator === 'gte') passed = lVal >= rVal;

      logs.push({ rule: i, leftValue: lVal, rightValue: rVal, operator, passed });
      if (!passed) {
        errors.push(`Rule ${i} aggregate comparison failed: ${lVal} ${operator} ${rVal}`);
      }
    } catch (e) {
      errors.push(`Rule ${i} error: ${e.message}`);
    }
  }

  return { valid: errors.length === 0, errors, logs };
}

export function evaluateLocalReferences(rules, instance) {
  if (!Array.isArray(rules) || rules.length === 0) {
    return { valid: false, errors: ['localReferences must be a non-empty array'] };
  }
  const errors = [];
  const logs = [];

  for (let i = 0; i < rules.length; i++) {
    const { source, target } = rules[i];
    const srcArrRes = resolvePointer(instance, source.array);
    const tgtArrRes = resolvePointer(instance, target.array);

    if (!srcArrRes.found || !Array.isArray(srcArrRes.value)) {
      errors.push(`Rule ${i}: source array '${source.array}' is missing or not an array`);
      continue;
    }
    if (!tgtArrRes.found || !Array.isArray(tgtArrRes.value)) {
      errors.push(`Rule ${i}: target array '${target.array}' is missing or not an array`);
      continue;
    }

    const srcArr = srcArrRes.value;
    const tgtArr = tgtArrRes.value;

    const tgtKeys = [];
    let hasDuplicateTarget = false;
    for (let tIdx = 0; tIdx < tgtArr.length; tIdx++) {
      const item = tgtArr[tIdx];
      const keyTuple = [];
      for (const kPtr of target.keys) {
        const res = resolvePointer(item, kPtr);
        if (!res.found) {
          errors.push(`Rule ${i}: target item ${tIdx} missing key '${kPtr}'`);
        }
        keyTuple.push(res.found ? res.value : undefined);
      }
      const dup = tgtKeys.some(existing => keyTuple.every((val, idx) => jsonEqual(val, existing[idx])));
      if (dup) {
        hasDuplicateTarget = true;
        errors.push(`Rule ${i}: duplicate target tuple at index ${tIdx}: ${JSON.stringify(keyTuple)}`);
      }
      tgtKeys.push(keyTuple);
    }

    if (hasDuplicateTarget) continue;

    for (let sIdx = 0; sIdx < srcArr.length; sIdx++) {
      const item = srcArr[sIdx];
      const srcTuple = [];
      let missingKey = false;
      for (const kPtr of source.keys) {
        const res = resolvePointer(item, kPtr);
        if (!res.found) {
          missingKey = true;
          errors.push(`Rule ${i}: source item ${sIdx} missing key '${kPtr}'`);
        }
        srcTuple.push(res.found ? res.value : undefined);
      }
      if (missingKey) continue;

      const matchCount = tgtKeys.filter(tTuple => srcTuple.every((val, idx) => jsonEqual(val, tTuple[idx]))).length;
      if (matchCount !== 1) {
        errors.push(`Rule ${i}: source item ${sIdx} with keys ${JSON.stringify(srcTuple)} matches ${matchCount} target rows (expected exactly 1)`);
      }
    }
  }

  return { valid: errors.length === 0, errors, logs };
}

export function evaluateSortedBy(config, instance) {
  if (!Array.isArray(instance)) {
    return { valid: true, logs: ['Ignored for non-array instance'] };
  }
  if (instance.length <= 1) {
    if (instance.length === 1) {
      const res = resolvePointer(instance[0], config.key);
      if (!res.found) return { valid: false, errors: ['Single item must have valid key'] };
    }
    return { valid: true, logs: ['Array with <= 1 item is sorted'] };
  }

  const { key, mode, direction, ties } = config;
  const errors = [];

  for (let i = 0; i < instance.length - 1; i++) {
    const curRes = resolvePointer(instance[i], key);
    const nxtRes = resolvePointer(instance[i + 1], key);
    if (!curRes.found || !nxtRes.found) {
      return { valid: false, errors: [`Key '${key}' missing at indices ${i} or ${i + 1}`] };
    }
    const a = curRes.value;
    const b = nxtRes.value;

    let cmp = 0;
    if (mode === 'number') {
      if (typeof a !== 'number' || typeof b !== 'number' || !Number.isFinite(a) || !Number.isFinite(b)) {
        return { valid: false, errors: [`Values must be finite numbers, got ${typeof a} and ${typeof b}`] };
      }
      cmp = a < b ? -1 : (a > b ? 1 : 0);
    } else if (mode === 'date') {
      if (!isValidDate(a) || !isValidDate(b)) {
        return { valid: false, errors: [`Values must be valid dates YYYY-MM-DD`] };
      }
      cmp = a < b ? -1 : (a > b ? 1 : 0);
    } else if (mode === 'date-time') {
      const tA = parseDateTime(a);
      const tB = parseDateTime(b);
      if (tA === null || tB === null) {
        return { valid: false, errors: [`Values must be valid ISO date-time strings with zone`] };
      }
      cmp = tA < tB ? -1 : (tA > tB ? 1 : 0);
    }

    if (cmp === 0 && ties === 'forbid') {
      errors.push(`Forbidden tie encountered between index ${i} and ${i + 1}`);
    } else if (direction === 'ascending' && cmp > 0) {
      errors.push(`Order violation (ascending) between index ${i} (${a}) and ${i + 1} (${b})`);
    } else if (direction === 'descending' && cmp < 0) {
      errors.push(`Order violation (descending) between index ${i} (${a}) and ${i + 1} (${b})`);
    }
  }

  return { valid: errors.length === 0, errors };
}

export function evaluateNonOverlapping(config, instance) {
  if (!Array.isArray(instance) || instance.length <= 1) {
    return { valid: true, logs: ['Array with <= 1 item is non-overlapping'] };
  }
  const { start, end, bounds, mode } = config;
  const intervals = [];
  const errors = [];

  for (let i = 0; i < instance.length; i++) {
    const sRes = resolvePointer(instance[i], start);
    const eRes = resolvePointer(instance[i], end);
    if (!sRes.found || !eRes.found) {
      return { valid: false, errors: [`Missing start/end at item ${i}`] };
    }
    const s = sRes.value;
    const e = eRes.value;

    let sNum, eNum;
    if (mode === 'code-point-offset' || mode === 'byte-offset') {
      if (typeof s !== 'number' || typeof e !== 'number' || !Number.isInteger(s) || !Number.isInteger(e) || s < 0 || e < 0) {
        return { valid: false, errors: [`Offsets must be non-negative integers at item ${i}`] };
      }
      sNum = s;
      eNum = e;
    } else if (mode === 'number') {
      if (typeof s !== 'number' || typeof e !== 'number') return { valid: false, errors: ['Endpoints must be numbers'] };
      sNum = s;
      eNum = e;
    } else if (mode === 'date') {
      if (!isValidDate(s) || !isValidDate(e)) return { valid: false, errors: ['Endpoints must be dates'] };
      sNum = new Date(s).getTime();
      eNum = new Date(e).getTime();
    } else if (mode === 'date-time') {
      sNum = parseDateTime(s);
      eNum = parseDateTime(e);
      if (sNum === null || eNum === null) return { valid: false, errors: ['Endpoints must be valid date-times'] };
    }

    if (sNum > eNum) {
      return { valid: false, errors: [`Reversed interval at index ${i}: start > end`] };
    }
    intervals.push({ s: sNum, e: eNum, index: i });
  }

  for (let i = 0; i < intervals.length; i++) {
    for (let j = i + 1; j < intervals.length; j++) {
      const A = intervals[i];
      const B = intervals[j];
      if (A.s === A.e || B.s === B.e) {
        // Empty intervals do not overlap in half-open
        if (bounds === 'half-open') continue;
      }
      let overlap = false;
      if (bounds === 'half-open') {
        // [start, end)
        overlap = Math.max(A.s, B.s) < Math.min(A.e, B.e);
      } else {
        // [start, end]
        overlap = Math.max(A.s, B.s) <= Math.min(A.e, B.e);
      }
      if (overlap) {
        errors.push(`Overlap detected between item ${A.index} and item ${B.index}`);
      }
    }
  }

  return { valid: errors.length === 0, errors };
}

export function evaluateArithmeticEquals(rules, instance) {
  if (!Array.isArray(rules) || rules.length === 0) {
    return { valid: false, errors: ['arithmeticEquals must be a non-empty array'] };
  }
  const errors = [];
  const logs = [];

  for (let i = 0; i < rules.length; i++) {
    const { left, right, result, operation, rounding } = rules[i];
    const lRes = resolvePointer(instance, left);
    const rRes = resolvePointer(instance, right);
    const resRes = resolvePointer(instance, result);

    if (!lRes.found || !rRes.found || !resRes.found) {
      errors.push(`Rule ${i}: Operands or result pointer missing`);
      continue;
    }

    const aStr = lRes.value;
    const bStr = rRes.value;
    const expStr = resRes.value;

    if (typeof aStr !== 'string' || typeof bStr !== 'string' || typeof expStr !== 'string') {
      errors.push(`Rule ${i}: Operands and result must be decimal strings (JSON numbers are rejected)`);
      continue;
    }

    const numRegex = /^-?(0|[1-9]\d*)(\.\d{1,18})?$/;
    if (!numRegex.test(aStr) || !numRegex.test(bStr) || !numRegex.test(expStr)) {
      errors.push(`Rule ${i}: Malformed decimal format, exponent notation, or leading zero`);
      continue;
    }

    const a = parseFloat(aStr);
    const b = parseFloat(bStr);
    const expected = parseFloat(expStr);

    let calculated = 0;
    if (operation === 'add') calculated = a + b;
    else if (operation === 'subtract') calculated = a - b;
    else if (operation === 'multiply') calculated = a * b;
    else if (operation === 'divide') {
      if (b === 0) {
        errors.push(`Rule ${i}: Division by zero`);
        continue;
      }
      calculated = a / b;
    } else if (operation === 'percentOf') {
      calculated = (a * b) / 100.0;
    }

    let finalVal = calculated;
    if (rounding) {
      const scale = rounding.scale ?? 2;
      const factor = Math.pow(10, scale);
      if (rounding.mode === 'toward-zero') {
        finalVal = Math.trunc(calculated * factor) / factor;
      } else if (rounding.mode === 'half-up') {
        finalVal = Math.round(calculated * factor) / factor;
      } else {
        // half-even
        const temp = calculated * factor;
        const floor = Math.floor(temp);
        const diff = temp - floor;
        if (Math.abs(diff - 0.5) < 1e-9) {
          finalVal = (floor % 2 === 0 ? floor : floor + 1) / factor;
        } else {
          finalVal = Math.round(temp) / factor;
        }
      }
    }

    const diff = Math.abs(finalVal - expected);
    const passed = diff < 1e-8;
    logs.push({ rule: i, calculated: finalVal, expected, passed });
    if (!passed) {
      errors.push(`Rule ${i}: ${aStr} ${operation} ${bStr} calculated ${finalVal} != expected ${expStr}`);
    }
  }

  return { valid: errors.length === 0, errors, logs };
}

export function evaluateTensorShapes(rules, instance) {
  if (!Array.isArray(rules) || rules.length === 0) {
    return { valid: false, errors: ['tensorShapes must be a non-empty array'] };
  }
  const errors = [];
  const symbols = {};

  function checkRectangular(arr, depth, targetDepth, dimIndex, symbolArray) {
    if (depth === targetDepth) {
      // Leaf check: number, string, boolean
      if (Array.isArray(arr) || arr === null || typeof arr === 'object') {
        return { valid: false, error: `Leaf at depth ${depth} must be a scalar (number/string/boolean), got ${typeof arr}` };
      }
      return { valid: true };
    }
    if (!Array.isArray(arr)) {
      return { valid: false, error: `Expected array at rank depth ${depth}, got ${typeof arr}` };
    }
    const len = arr.length;
    const declaredDim = symbolArray[dimIndex];

    if (declaredDim === null) {
      // anonymous: lengths in this branch must be consistent
    } else if (typeof declaredDim === 'number') {
      if (len !== declaredDim) {
        return { valid: false, error: `Axis ${dimIndex} declared length ${declaredDim}, observed ${len}` };
      }
    } else if (typeof declaredDim === 'string') {
      if (symbols[declaredDim] === undefined) {
        symbols[declaredDim] = len;
      } else if (symbols[declaredDim] !== len) {
        return { valid: false, error: `Symbol '${declaredDim}' previously bound to ${symbols[declaredDim]}, now encountered ${len}` };
      }
    }

    for (const child of arr) {
      const childRes = checkRectangular(child, depth + 1, targetDepth, dimIndex + 1, symbolArray);
      if (!childRes.valid) return childRes;
    }
    return { valid: true };
  }

  for (let i = 0; i < rules.length; i++) {
    const { path, shape } = rules[i];
    const res = resolvePointer(instance, path);
    if (!res.found) {
      errors.push(`Rule ${i}: Tensor path '${path}' not found: ${res.error}`);
      continue;
    }
    const tensor = res.value;
    const rank = shape.length;
    const check = checkRectangular(tensor, 0, rank, 0, shape);
    if (!check.valid) {
      errors.push(`Rule ${i} at '${path}': ${check.error}`);
    }
  }

  return { valid: errors.length === 0, errors };
}

export function validateGeneric(schema, instance) {
  if (schema.compareFields) return evaluateCompareFields(schema.compareFields, instance);
  if (schema.uniqueKeys) return evaluateUniqueKeys(schema.uniqueKeys, instance);
  if (schema.aggregateCompare) return evaluateAggregateCompare(schema.aggregateCompare, instance);
  if (schema.localReferences) return evaluateLocalReferences(schema.localReferences, instance);
  if (schema.sortedBy) return evaluateSortedBy(schema.sortedBy, instance);
  if (schema.nonOverlapping) return evaluateNonOverlapping(schema.nonOverlapping, instance);
  if (schema.arithmeticEquals) return evaluateArithmeticEquals(schema.arithmeticEquals, instance);
  if (schema.tensorShapes) return evaluateTensorShapes(schema.tensorShapes, instance);

  return { valid: true, logs: ['Standard schema parsed'] };
}

