"""Bounded, JSON-only assertion expressions for a dedicated dialect."""

import json
import math
from importlib.resources import files

from jsonschema import Draft202012Validator, ValidationError, validators

from .diagnostics import parts, resolve
from .unique_keys import json_identity

META_SCHEMA = json.loads(files('heschema').joinpath('assert-expression-v1.json').read_text())
DIALECT = META_SCHEMA['$id']
META_VALIDATOR = Draft202012Validator(META_SCHEMA)
MAX_DEPTH = 48
MAX_STEPS = 10000
BINARY = {'eq', 'ne', 'lt', 'lte', 'gt', 'gte'}
NUMERIC = {
    'lt': lambda a, b: a < b,
    'lte': lambda a, b: a <= b,
    'gt': lambda a, b: a > b,
    'gte': lambda a, b: a >= b,
}


class ExpressionError(Exception):
    """An invalid runtime operand or an exhausted evaluation budget."""


def check_expression(node, bindings=frozenset({'root'}), depth=0):
    """Check every branch without interpreting objects inside literal."""
    if depth > MAX_DEPTH:
        raise ValueError('Expression nesting exceeds 48')
    if not isinstance(node, dict) or len(node) != 1:
        raise ValueError('An expression must be a single operator object')
    op, args = next(iter(node.items()))
    if op == 'literal':
        return
    if op in {'get', 'exists'}:
        if not isinstance(args, dict) or set(args) != {'from', 'path'}:
            raise ValueError(f'{op} requires from and path')
        if not isinstance(args['from'], str) or args['from'] not in bindings:
            raise ValueError('Unknown expression binding')
        parts(args['path'])
        return
    if op in {'all', 'some'}:
        if not isinstance(args, dict) or set(args) != {'array', 'as', 'test'}:
            raise ValueError(f'{op} requires array, as and test')
        name = args['as']
        if not isinstance(name, str) or not name.isidentifier() or name in bindings:
            raise ValueError('Predicate binding must be a fresh identifier')
        check_expression(args['array'], bindings, depth + 1)
        check_expression(args['test'], bindings | {name}, depth + 1)
        return
    if op == 'if':
        if not isinstance(args, dict) or set(args) != {'test', 'then', 'else'}:
            raise ValueError('if requires test, then and else')
        children = args.values()
    elif op == 'not':
        children = [args]
    elif op in BINARY or op in {'and', 'or'}:
        if not isinstance(args, list) or (
            len(args) != 2 if op in BINARY else len(args) < 1
        ):
            raise ValueError(f'Invalid argument count for {op}')
        children = args
    else:
        raise ValueError(f'Unknown expression operator {op!r}')
    for child in children:
        check_expression(child, bindings, depth + 1)


def boolean(value):
    if type(value) is not bool:
        raise ExpressionError('Expected a Boolean expression result')
    return value


def evaluate(node, bindings, budget):
    budget[0] -= 1
    if budget[0] < 0:
        raise ExpressionError('Expression evaluation budget exceeded')
    op, args = next(iter(node.items()))
    if op == 'literal':
        return args
    if op in {'get', 'exists'}:
        try:
            value = resolve(bindings[args['from']], args['path'])
        except KeyError:
            if op == 'exists':
                return False
            raise ExpressionError('Expression pointer could not be resolved') from None
        return True if op == 'exists' else value
    if op == 'if':
        branch = 'then' if boolean(evaluate(args['test'], bindings, budget)) else 'else'
        return evaluate(args[branch], bindings, budget)
    if op == 'not':
        return not boolean(evaluate(args, bindings, budget))
    if op in {'and', 'or'}:
        for child in args:
            value = boolean(evaluate(child, bindings, budget))
            if value == (op == 'or'):
                return value
        return op == 'and'
    if op in {'all', 'some'}:
        array = evaluate(args['array'], bindings, budget)
        if not isinstance(array, list):
            raise ExpressionError('Predicate input must be an array')
        for item in array:
            value = boolean(evaluate(
                args['test'], {**bindings, args['as']: item}, budget,
            ))
            if value == (op == 'some'):
                return value
        return op == 'all'
    left = evaluate(args[0], bindings, budget)
    right = evaluate(args[1], bindings, budget)
    if op in {'eq', 'ne'}:
        equal = json_identity(left) == json_identity(right)
        return equal if op == 'eq' else not equal
    if any(type(value) not in {int, float} or (
        type(value) is float and not math.isfinite(value)
    ) for value in (left, right)):
        raise ExpressionError('Ordering operands must be finite JSON numbers')
    return NUMERIC[op](left, right)


def _assert_expression(_validator, expression, instance, _schema):
    try:
        passed = boolean(evaluate(expression, {'root': instance}, [MAX_STEPS]))
    except ExpressionError as error:
        yield ValidationError(f'ASSERT_EXPRESSION_ERROR: {error}')
        return
    if not passed:
        yield ValidationError('ASSERT_EXPRESSION_FALSE: assertion returned false')


VALIDATOR = validators.extend(
    Draft202012Validator, {'assertExpression': _assert_expression},
)
