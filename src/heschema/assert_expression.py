"""Checked JSON expressions with lexical lazy functions and source diagnostics."""

import json
from dataclasses import dataclass
from importlib.resources import files

from jsonschema import Draft202012Validator, ValidationError, validators

from . import expression_values as values
from .diagnostics import parts, pointer, resolve

META_SCHEMA = json.loads(files('heschema').joinpath('assert-expression-v1.json').read_text())
DIALECT = META_SCHEMA['$id']
META_VALIDATOR = Draft202012Validator(META_SCHEMA)
MAX_DEPTH = 48
MAX_STEPS = 10000
ANY = frozenset({'dynamic'})
COMPARISONS = {'eq', 'ne', 'lt', 'lte', 'gt', 'gte'}
ARITHMETIC = {'add', 'subtract', 'multiply', 'divide'}
UNARY = {'not', 'toInteger', 'date', 'timestamp', 'length'}


def kind(value):
    if isinstance(value, values.Scalar):
        return value.kind
    return {type(None): 'null', bool: 'bool', int: 'number', float: 'number',
            str: 'string', list: 'array', dict: 'object'}[type(value)]


def check_json(value):
    stack = [(value, 0)]
    remaining = MAX_STEPS
    while stack:
        item, depth = stack.pop()
        remaining -= 1
        if remaining < 0 or depth > MAX_DEPTH:
            raise ValueError('JSON value nesting or node budget exceeded')
        if isinstance(item, dict):
            if any(not isinstance(key, str) for key in item):
                raise ValueError('JSON object keys must be strings')
            stack.extend((child, depth + 1) for child in item.values())
        elif isinstance(item, list):
            stack.extend((child, depth + 1) for child in item)
        elif isinstance(item, str):
            values.text(item)
        elif type(item) is int:
            values.integer(item)
        elif type(item) is float:
            if not values.finite_number(item):
                raise ValueError('JSON numbers must be finite')
        elif item is not None and type(item) is not bool:
            raise ValueError('Expected a JSON value')


def require_type(observed, expected):
    if not (observed - {'dynamic'}) <= expected:
        raise ValueError(f'Expected expression type {sorted(expected)}, got {sorted(observed)}')


def fields(args, names, op):
    if not isinstance(args, dict) or set(args) != set(names):
        raise ValueError(f'{op} requires {", ".join(names)}')


def fresh(name, used):
    if not isinstance(name, str) or not name.isidentifier() or name in used:
        raise ValueError('Binding must be a fresh identifier')


def check_expression(node, bindings=None, depth=0, functions=None, budget=None):
    """Infer known result types and inspect every branch before evaluating data."""
    bindings = {'root': ANY} if bindings is None else bindings
    functions = {} if functions is None else functions
    budget = [MAX_STEPS] if budget is None else budget
    budget[0] -= 1
    if depth > MAX_DEPTH or budget[0] < 0:
        raise ValueError('Expression nesting or node budget exceeded')
    if not isinstance(node, dict) or len(node) != 1:
        raise ValueError('An expression must be a single operator object')
    op, args = next(iter(node.items()))

    def check(child, expected=None, scope=bindings, funcs=functions):
        result = check_expression(child, scope, depth + 1, funcs, budget)
        if expected is not None:
            require_type(result, expected)
        return result

    if op == 'literal':
        check_json(args)
        return frozenset({kind(args)})
    if op in {'get', 'exists'}:
        fields(args, ('from', 'path'), op)
        if not isinstance(args['from'], str) or args['from'] not in bindings:
            raise ValueError('Unknown expression binding')
        parts(args['path'])
        return frozenset({'bool'}) if op == 'exists' else (
            bindings[args['from']] if args['path'] == '' else ANY
        )
    if op in {'all', 'some'}:
        fields(args, ('array', 'as', 'test'), op)
        fresh(args['as'], bindings)
        check(args['array'], {'array'})
        check(args['test'], {'bool'}, {**bindings, args['as']: ANY})
        return frozenset({'bool'})
    if op == 'define':
        fields(args, ('name', 'params', 'body', 'in'), op)
        fresh(args['name'], functions)
        params = args['params']
        if not isinstance(params, list) or any(
            not isinstance(p, str) or not p.isidentifier() or p in bindings for p in params
        ) or len(set(params)) != len(params):
            raise ValueError('Function parameters must be fresh distinct identifiers')
        result = check(args['body'], scope={**bindings, **dict.fromkeys(params, ANY)})
        return check(args['in'], funcs={**functions, args['name']: (params, result, args['body'], bindings, functions)})
    if op == 'call':
        fields(args, ('name', 'args'), op)
        if not isinstance(args['name'], str) or args['name'] not in functions:
            raise ValueError('Unknown expression function')
        params, _result, body, scope, funcs = functions[args['name']]
        if not isinstance(args['args'], list) or len(args['args']) != len(params):
            raise ValueError('Function argument count mismatch')
        types = [check(arg) for arg in args['args']]
        return check(body, scope={**scope, **dict(zip(params, types))}, funcs=funcs)
    if op == 'if':
        fields(args, ('test', 'then', 'else'), op)
        check(args['test'], {'bool'})
        return check(args['then']) | check(args['else'])
    if op in UNARY:
        expected = {'bool'} if op == 'not' else (
            {'string', 'number'} if op == 'toInteger' else {'string'}
        )
        check(args, expected)
        return frozenset({{'not': 'bool', 'toInteger': 'number', 'date': 'date',
                           'timestamp': 'timestamp', 'length': 'number'}[op]})
    if op == 'decimal':
        if isinstance(args, str):
            values.decimal(args)
        else:
            check(args, {'string'})
        return frozenset({'decimal'})
    if op == 'round':
        fields(args, ('value', 'scale', 'mode'), op)
        if type(args['scale']) is not int or not 0 <= args['scale'] <= 18:
            raise ValueError('Rounding scale must be an integer from 0 to 18')
        if args['mode'] not in ('half-even', 'half-up', 'toward-zero'):
            raise ValueError('Unknown decimal rounding mode')
        check(args['value'], {'decimal'})
        return frozenset({'decimal'})
    if op == 'slice':
        fields(args, ('value', 'start', 'end', 'unit'), op)
        if args['unit'] not in ('codePoint', 'grapheme'):
            raise ValueError('Unknown Unicode slice unit')
        if any(type(args[k]) is not int or args[k] < 0 for k in ('start', 'end')):
            raise ValueError('Slice bounds must be nonnegative integers')
        if args['start'] > args['end']:
            raise ValueError('Slice start exceeds end')
        check(args['value'], {'string'})
        return frozenset({'string'})
    if op in COMPARISONS | ARITHMETIC | {'and', 'or', 'matches'}:
        if not isinstance(args, list) or (len(args) < 1 if op in {'and', 'or'} else len(args) != 2):
            raise ValueError(f'Invalid argument count for {op}')
        expected = {'bool'} if op in {'and', 'or'} else (
            {'decimal'} if op in ARITHMETIC else {'string'} if op == 'matches' else None
        )
        types = [check(arg, expected) for arg in args]
        if op in {'lt', 'lte', 'gt', 'gte'}:
            for observed in types:
                require_type(observed, {'number', 'decimal', 'date', 'timestamp'})
            if not any('dynamic' in item for item in types) and types[0] != types[1]:
                raise ValueError('Ordering operands must have matching types')
        if op == 'matches' and 'literal' in args[1] and isinstance(args[1]['literal'], str):
            values.pattern(args[1]['literal'])
        return frozenset({'decimal'} if op in ARITHMETIC else {'bool'})
    raise ValueError(f'Unknown expression operator {op!r}')


@dataclass
class Result:
    value: object
    path: tuple | None = None
    expression: tuple = ()


class ExpressionError(Exception):
    def __init__(self, message, path=None, expression=()):
        super().__init__(message)
        self.path = path
        self.expression = expression


def boolean(value):
    if type(value) is not bool:
        raise ValueError('Expected a Boolean expression result')
    return value


def equal(left, right, budget):
    budget[0] -= 1
    if budget[0] < 0:
        raise ValueError('Expression evaluation budget exceeded')
    a, b = kind(left), kind(right)
    if a != b:
        return False
    if a == 'object':
        return left.keys() == right.keys() and all(equal(left[k], right[k], budget) for k in left)
    if a == 'array':
        return len(left) == len(right) and all(equal(a, b, budget) for a, b in zip(left, right))
    return left == right


@dataclass
class Lazy:
    expression: dict
    bindings: dict
    functions: dict
    location: tuple


def evaluate(node, bindings, budget, functions=None, location=(), depth=0):
    functions = {} if functions is None else functions
    budget[0] -= 1
    if budget[0] < 0:
        raise ExpressionError('Expression evaluation budget exceeded', expression=location)
    if depth > MAX_DEPTH:
        raise ExpressionError('Expression evaluation nesting exceeded', expression=location)
    op, args = next(iter(node.items()))
    here = (*location, op)

    def run(child, suffix=(), scope=bindings, funcs=functions):
        return evaluate(child, scope, budget, funcs, (*here, *suffix), depth + 1)

    source = Result(None, expression=here)
    try:
        if op == 'literal':
            return Result(args, expression=here)
        if op in {'get', 'exists'}:
            binding = bindings[args['from']]
            if isinstance(binding, Lazy):
                binding = evaluate(binding.expression, binding.bindings, budget,
                                   binding.functions, binding.location, depth + 1)
            source = binding
            path = (*binding.path, *parts(args['path'])) if binding.path is not None else None
            try:
                value = resolve(binding.value, args['path'])
            except KeyError:
                if op == 'exists':
                    return Result(False, path, here)
                raise ExpressionError('Expression pointer could not be resolved', path, here) from None
            return Result(True if op == 'exists' else value, path, here)
        if op == 'define':
            closure = (args, bindings, functions, here)
            return run(args['in'], ('in',), funcs={**functions, args['name']: closure})
        if op == 'call':
            definition, scope, funcs, definition_path = functions[args['name']]
            arguments = {
                name: Lazy(arg, bindings, functions, (*here, 'args', i))
                for i, (name, arg) in enumerate(zip(definition['params'], args['args']))
            }
            return evaluate(definition['body'], {**scope, **arguments}, budget, funcs,
                            (*definition_path, 'body'), depth + 1)
        if op == 'if':
            source = run(args['test'], ('test',))
            branch = 'then' if boolean(source.value) else 'else'
            return run(args[branch], (branch,))
        if op in {'and', 'or'}:
            for i, child in enumerate(args):
                source = run(child, (i,))
                if boolean(source.value) == (op == 'or'):
                    return source
            return Result(op == 'and', source.path, here)
        if op in {'all', 'some'}:
            source = run(args['array'], ('array',))
            if not isinstance(source.value, list):
                raise ValueError('Predicate input must be an array')
            array = source
            for i, item in enumerate(array.value):
                path = (*array.path, i) if array.path is not None else None
                result = run(args['test'], ('test',), {
                    **bindings, args['as']: Result(item, path, here),
                })
                source = result
                if boolean(result.value) == (op == 'some'):
                    return result
            return Result(op == 'all', array.path, here)
        if op in UNARY | {'decimal'}:
            source = Result(args, expression=here) if op == 'decimal' and isinstance(args, str) else run(args)
            value = source.value
            if op == 'not':
                result = not boolean(value)
            elif op == 'toInteger':
                result = values.integer(value)
            elif op in {'date', 'timestamp'}:
                result = values.temporal(value, op)
            elif op == 'length':
                result = len(values.text(value))
            else:
                result = values.decimal(value)
            return Result(result, source.path, here)
        if op == 'round':
            source = run(args['value'], ('value',))
            return Result(values.rounded(source.value, args['scale'], args['mode']), source.path, here)
        if op == 'slice':
            source = run(args['value'], ('value',))
            result = values.slice_text(source.value, args['start'], args['end'], args['unit'])
            return Result(result, source.path, here)
        left = run(args[0], (0,))
        right = run(args[1], (1,))
        source = left if left.path is not None else right
        a, b = left.value, right.value
        if op in {'eq', 'ne'}:
            result = equal(a, b, budget)
            result = result if op == 'eq' else not result
        elif op == 'matches':
            source = right
            pattern = values.pattern(b)
            source = left
            result = pattern.search(values.text(a)) is not None
        elif op in ARITHMETIC:
            result = values.arithmetic(op, a, b)
        else:
            if kind(a) != kind(b) or kind(a) not in {'number', 'decimal', 'date', 'timestamp'}:
                raise ValueError('Ordering operands must have matching numeric or temporal types')
            if kind(a) == 'number':
                if not values.finite_number(a) or not values.finite_number(b):
                    raise ValueError('Ordering operands must be finite JSON numbers')
            else:
                a, b = a.value, b.value
            if op == 'lt':
                result = a < b
            elif op == 'lte':
                result = a <= b
            elif op == 'gt':
                result = a > b
            else:
                result = a >= b
        return Result(result, source.path, here)
    except (ValueError, TimeoutError) as error:
        raise ExpressionError(str(error), source.path, here) from None


def _assert_expression(_validator, expression, instance, _schema):
    try:
        check_json(instance)
        result = evaluate(expression, {'root': Result(instance, ())}, [MAX_STEPS])
        if type(result.value) is not bool:
            raise ExpressionError('Expected a Boolean expression result', result.path, result.expression)
        passed = result.value
    except (ExpressionError, ValueError) as error:
        issue = ValidationError(f'ASSERT_EXPRESSION_ERROR: {error}', path=getattr(error, 'path', ()) or ())
        issue.expression_reason = 'ASSERT_EXPRESSION_ERROR'
        issue.expression_location = pointer(getattr(error, 'expression', ()))
        yield issue
        return
    if not passed:
        issue = ValidationError('ASSERT_EXPRESSION_FALSE: assertion returned false', path=result.path or ())
        issue.expression_reason = 'ASSERT_EXPRESSION_FALSE'
        issue.expression_location = pointer(result.expression)
        yield issue


VALIDATOR = validators.extend(Draft202012Validator, {'assertExpression': _assert_expression})
