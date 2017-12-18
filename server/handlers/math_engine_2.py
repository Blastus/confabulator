#! /usr/bin/env python3
"""Provide classes that allow a more advanced math evaluation engine to run.

The module has a MathEvaluator handler class that can be used by clients to
automatically execute math statements. Users should note that a different
syntax replaces the original engine's way of parsing their expressions."""

__author__ = 'Stephen "Zero" Chappell ' \
             '<stephen.paul.chappell@atlantis-zero.net>'
__date__ = '18 December 2017'
__version__ = 1, 0, 0
__all__ = [
    'MathEvaluator'
]

import abc
import operator
import sys
import traceback

import server.timeout
from . import common


class MathEvaluator(common.Handler):
    """MathEvaluator2(client) -> MathEvaluator2 instance"""

    def handle(self):
        """Create a math evaluation loop for interacting with the client."""
        local = {}
        while True:
            line = self.client.input('>>> ')
            if line in common.STOP_WORDS:
                break
            # noinspection PyBroadException
            try:
                self.evaluate(line, local)
            except Exception:
                error = traceback.format_exception_only(*sys.exc_info()[:2])
                self.client.print(error[-1], end='')

    def evaluate(self, source, local):
        """Execute all math operations found in the source."""
        for expression in self.expressions(source):
            local['_'] = self.tokens(expression).evaluate(local)

    @staticmethod
    def expressions(source):
        """Separate expressions and yield each individually."""
        lines = source.replace('\r\n', '\n').replace('\r', '\n').split('\n')
        # noinspection PyShadowingNames
        uncommented = map(lambda line: line.split('#', 1)[0], lines)
        for line in uncommented:
            if line and not line.isspace():
                for expression in line.split(';'):
                    yield expression

    def tokens(self, string):
        """Build an expression tree by tokenizing expression."""
        evaluator = self._tokens(string)
        if isinstance(evaluator, Operation):
            if evaluator.symbol == Operation.ASSIGNMENT:
                return evaluator
        return Print(evaluator, self.client.print)

    def _tokens(self, string):
        """Private module function: recursively builds a tree."""
        expression = string.strip()
        if not expression:
            raise SyntaxError('empty expression')
        divisions = Operation.split(expression)
        if divisions:
            left, symbol, right = divisions
            return Operation(self._tokens(left), symbol, self._tokens(right))
        if len(expression.split()) > 1:
            raise SyntaxError(expression)
        if expression.startswith('0x'):
            return Constant(int(expression[2:], 16))
        if expression.startswith('0d'):
            return Constant(int(expression[2:], 10))
        if expression.startswith('0o'):
            return Constant(int(expression[2:], 8))
        if expression.startswith('0q'):
            return Constant(int(expression[2:], 4))
        if expression.startswith('0b'):
            return Constant(int(expression[2:], 2))
        if expression.isdigit():
            return Constant(int(expression))
        if expression.isidentifier():
            return Variable(expression)
        raise SyntaxError(expression)


class Expression(abc.ABC):
    """Abstract class for Expression objects."""

    @abc.abstractmethod
    def __init__(self):
        """Initialize the Expression object."""
        pass

    def __repr__(self):
        """Return a representation of this object."""
        kind = type(self).__name__
        private = f'_{kind}__'
        args = []
        for name in vars(self):
            if name.startswith(private):
                key = name[len(private):]
                value = getattr(self, name)
                args.append(f'{key}={value!r}')
        return f'{kind}({", ".join(args)})'

    @abc.abstractmethod
    def evaluate(self, bindings):
        """Calculate the value of this object."""
        pass


class Constant(Expression):
    """Class for storing all math constants."""

    def __init__(self, value):
        """Initialize the Constant object."""
        super().__init__()
        self.__value = value

    def evaluate(self, bindings):
        """Calculate the value of this object."""
        return self.__value


class Variable(Expression):
    """Class for storing all math variables."""

    def __init__(self, name):
        """Initialize the Variable object."""
        super().__init__()
        self.__name = name

    def evaluate(self, bindings):
        """Calculate the value of this object."""
        if self.__name not in bindings:
            raise NameError(self.__name)
        return bindings[self.__name]

    @property
    def name(self):
        """Property of the variable's name."""
        return self.__name


class Operation(Expression):
    """Class for executing math operations."""

    ASSIGNMENT = '->'
    OPERATORS = {ASSIGNMENT: lambda a, b: None,
                 '&&': operator.and_,
                 '||': operator.or_,
                 '+': operator.add,
                 '-': operator.sub,
                 '*': operator.mul,
                 '/': operator.floordiv,
                 '%': operator.mod,
                 '**': operator.pow,
                 '&': operator.and_,
                 '|': operator.or_,
                 '^': operator.xor,
                 '>>': operator.rshift,
                 '<<': operator.lshift,
                 '==': operator.eq,
                 '!=': operator.ne,
                 '>': operator.gt,
                 '>=': operator.ge,
                 '<': operator.lt,
                 '<=': operator.le}

    def __init__(self, left, symbol, right):
        """Initialize the Operation object."""
        super().__init__()
        self.__left = left
        self.__symbol = symbol
        self.__right = right

    def evaluate(self, bindings):
        """Calculate the value of this object."""
        if self.__symbol == self.ASSIGNMENT:
            if not isinstance(self.__right, Variable):
                raise TypeError(self.__right)
            key = self.__right.name
            value = self.__left.evaluate(bindings)
            bindings[key] = value
            return value
        return self.__operate(bindings)

    def __operate(self, bindings):
        """Execute operation defined by symbol."""
        if self.__symbol not in self.OPERATORS:
            raise SyntaxError(self.__symbol)
        a = self.__left.evaluate(bindings)
        b = self.__right.evaluate(bindings)
        return server.timeout.run_with_timeout(
            5, 0.1, self.run_operation, self.__symbol, a, b
        )

    @staticmethod
    def run_operation(symbol, a, b):
        """Execute a dictionary search to perform the work of an operation."""
        return Operation.OPERATORS[symbol](a, b)

    __operators = sorted(OPERATORS, key=len, reverse=True)

    @classmethod
    def split(cls, expression):
        """Split expression on rightmost symbol."""
        tail = cls.__split(expression)
        if tail:
            symbol, right = tail
            return expression[:-sum(map(len, tail))], symbol, right

    @classmethod
    def __split(cls, expression):
        """Private class method: help with split."""
        for symbol in cls.__operators:
            if symbol in expression:
                right = expression.rsplit(symbol, 1)[1]
                tail = cls.__split(right)
                if tail is None:
                    return symbol, right
                return tail

    @property
    def symbol(self):
        """Property of the operation's symbol."""
        return self.__symbol


class Print(Expression):
    """Class for printing all math results."""

    def __init__(self, expression, printer):
        """Initialize the Print object."""
        super().__init__()
        self.__expression = expression
        self.__print = printer

    def evaluate(self, bindings):
        """Calculate the value of this object."""
        value = self.__expression.evaluate(bindings)
        self.__print(value)
        return value
