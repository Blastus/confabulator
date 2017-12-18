#! /usr/bin/env python3
"""Allow users to evaluate math expressions using an old engine.

This module contains a handler that can be instantiated and used to run
mathematical expressions. One should note that all tokens read by the engine
must be surrounded by whitespace in order to be properly understood."""

__author__ = 'Stephen "Zero" Chappell ' \
             '<stephen.paul.chappell@atlantis-zero.net>'
__date__ = '18 December 2017'
__version__ = 1, 0, 0
__all__ = [
    'MathExpressionEvaluator'
]

import abc

import server.timeout
from . import common


class MathExpressionEvaluator(common.Handler):
    """MathExpressionEvaluator(client) -> MathExpressionEvaluator instance"""

    def handle(self):
        """Handle math statements provided by the client by looping."""
        local = {}
        while True:
            line = self.client.input('Eval:')
            if line in common.STOP_WORDS:
                return
            try:
                self.run(line, local)
            except Exception as error:
                self.client.print(type(error).__name__, list(error.args))

    def run(self, line, local):
        """Execute the line using the local storage."""
        lines = self.tokenize(line)
        self.build_operations(lines)
        self.evaluate(lines, local)

    @staticmethod
    def tokenize(line):
        """Parse the line into its individual tokens."""
        lines = []
        # replace ';' with line separators
        string = line.replace(';', '\n')
        # the string will be evaluate line-by-line
        for line in string.split('\n'):
            tokens = []
            # ignore empty lines and comments
            if not line or line[0] == '#':
                continue
            # tokens are separated by white-space
            for token in line.split():
                # operations are processed later
                if token in {'=', '+', '-', '*', '/', '//', '%',
                             '**', '^', 'and', '&', 'or', '|',
                             '==', '!=', '>', '<', '>=', '<='}:
                    tokens.append(token)
                else:
                    # noinspection PyPep8,PyBroadException
                    try:
                        # token is constant if it can be converted to float
                        tokens.append(Constant(float(token)))
                    except:
                        # ... otherwise we assume that it is a variable
                        tokens.append(Variable(token))
            lines.append(tokens)
        return lines

    def build_operations(self, lines):
        """Create an expression tree to execute the math statement."""
        # now we work on sorting through operations
        for line_index, line in enumerate(lines):
            # assignment is optional on a line
            if '=' in line:
                # split on '=' so each section can be processed
                tokens = self.split(line)
                # single variables must be on the left of '='
                for section in tokens[:-1]:
                    assert len(section) == 1, 'Must Have Single Token'
                    assert isinstance(section[0],
                                      Variable), 'Must Assign to Variable'
                # construct an operation from the last tokens
                tokens[-1] = self.flatten(tokens[-1])
                # create as many assignment operations as needed
                op = Operation(tokens[-2][0], '=', tokens[-1])
                for token_index in range(len(tokens) - 3, -1, -1):
                    op = Operation(tokens[token_index][0], '=', op)
                # replace the line with the final operation
                lines[line_index] = op
            else:
                # no assignment? assume evaluation and printing
                op = self.flatten(line)
                lines[line_index] = Print(op, self.client.print)

    @staticmethod
    def split(line):
        """Divide the given tokens on the equal sign."""
        # split the tokens in the line on '='
        tokens = []
        while '=' in line:
            index = line.index('=')
            tokens.append(line[:index])
            line = line[index + 1:]
        return tokens + [line]

    @staticmethod
    def flatten(tokens):
        """Flatten the operations into a single operation."""
        # check for odd number of tokens
        assert len(tokens) % 2 == 1, 'Must Have Odd Number of Tokens'
        toggle = True
        # check the token construction sequence
        for token in tokens:
            if toggle:
                assert isinstance(token, (
                    Constant, Variable)), 'Must Have Constant or Variable'
            else:
                assert isinstance(token, str), 'Must Have Operation'
            toggle = not toggle
        # if there is only one token, it does not need to be flattened
        if len(tokens) == 1:
            return tokens[0]
        # construct the needed operations starting from the beginning
        op = Operation(*tokens[:3])
        for index in range(3, len(tokens), 2):
            op = Operation(op, tokens[index], tokens[index + 1])
        return op

    @staticmethod
    def evaluate(lines, local):
        """Execute an evaluation on all of the math expression lines."""
        # evaluate the lines in order with the local dictionary
        for line in lines:
            local['_'] = line.evaluate(local)


class Expression(abc.ABC):
    """Expression() -> TypeError exception"""

    @abc.abstractmethod
    def __init__(self):
        """This is a base class for math expressions."""
        pass

    def __repr__(self):
        """Provide a useful representation of the expression object."""
        kind = type(self).__name__
        private = f'_{kind}__'
        args = []
        for name in self.__dict__:
            if name.startswith(private):
                value = self.__dict__[name]
                name = name[len(private):]
                args.append(f'{name}={value!r}')
        return f'{kind}({", ".join(args)})'

    @abc.abstractmethod
    def evaluate(self, dictionary):
        """Expressions should be able to evaluate themselves."""
        pass


class Constant(Expression):
    """Constant(value) -> Constant instance"""

    def __init__(self, value):
        """Initialize the constant with its value."""
        super().__init__()
        self.__value = value

    def evaluate(self, dictionary):
        """Return the value when evaluated."""
        return self.__value


class Variable(Expression):
    """Variable(name) -> Variable instance"""

    def __init__(self, name):
        """Initialize the variable with its name."""
        super().__init__()
        self.__name = name

    def evaluate(self, dictionary):
        """Try to find and return the value of the variable."""
        if self.__name not in dictionary:
            raise Exception('Unknown variable: ' + self.__name)
        return dictionary[self.__name]

    @property
    def name(self):
        """Property of the variable's name."""
        return self.__name


class Operation(Expression):
    """Operation(left, op, right) -> Operation instance"""

    def __init__(self, left, op, right):
        """Initialize the operation with each side and operator."""
        super().__init__()
        self.__left = left
        self.__op = op
        self.__right = right

    def evaluate(self, dictionary):
        """Evaluate the operation based on the stored operator."""
        if self.__op == '=':
            assert isinstance(self.__left, Variable), 'Must Assign to Variable'
            name = self.__left.name
            value = self.__right.evaluate(dictionary)
            dictionary[name] = value
            return value
        x = self.__left.evaluate(dictionary)
        y = self.__right.evaluate(dictionary)
        return server.timeout.run_with_timeout(
            5, 0.1, self.run_operation, self.__op, x, y
        )

    @staticmethod
    def run_operation(operation, x, y):
        """Execute a switch that performs the work of an operation."""
        if operation == '+':
            return x + y
        if operation == '-':
            return x - y
        if operation == '*':
            return x * y
        if operation == '/':
            return x / y
        if operation == '//':
            return x // y
        if operation == '%':
            return x % y
        if operation == '**':
            return x ** y
        if operation == '^':
            return float(int(x) ^ int(y))
        if operation == 'and':
            return x and y
        if operation == '&':
            return float(int(x) & int(y))
        if operation == 'or':
            return x or y
        if operation == '|':
            return float(int(x) | int(y))
        if operation == '==':
            return float(x == y)
        if operation == '!=':
            return float(x != y)
        if operation == '>':
            return float(x > y)
        if operation == '<':
            return float(x < y)
        if operation == '>=':
            return float(x >= y)
        if operation == '<=':
            return float(x <= y)
        raise Exception('Unknown operator: ' + operation)


class Print(Expression):
    """Print(expression, printer) -> Print instance"""

    def __init__(self, expression, printer):
        """Initialize the Print instance with an expression and printer."""
        super().__init__()
        self.__expression = expression
        self.__print = printer

    def evaluate(self, dictionary):
        """Print the expression with the printer and return."""
        value = self.__expression.evaluate(dictionary)
        self.__print(value)
        return value
