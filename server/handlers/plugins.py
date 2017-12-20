#! /usr/bin/env python3
"""Tools that are not needed for the core server's functionality.

Currently, this module only contains the MarkVShaney class. It has the
capability or "summarizing" a channel and leaving a user with a jumbled
interpretation of what is going on after reading through all the messages."""

__author__ = 'Stephen "Zero" Chappell ' \
             '<stephen.paul.chappell@atlantis-zero.net>'
__date__ = '18 December 2017'
__version__ = 1, 0, 0
__all__ = [
    'MVSHandler'
]

import collections
import functools
import itertools
import random

from . import common


class MVSHandler(common.Handler):
    """MarkVShaney(client, buffer, size, channel) -> MarkVShaney instance"""

    MARKOV_CHAIN_LENGTH = 3
    MAX_SUMMARY_FAILING = 5

    def __init__(self, client, buffer, size, channel):
        """Initialize the handler for summarizing the channel."""
        super().__init__(client)
        self.buffer = buffer
        self.size = size
        self.channel = channel

    def handle(self):
        """Provide a Mark V Shaney summary of the channel and return."""
        array = self.prepare()
        mvs = MarkVShaney(array, self.MARKOV_CHAIN_LENGTH)
        cache = mvs.build_paragraph(
            self.MAX_SUMMARY_FAILING, self.size, True, True
        )
        self.print_summary(cache)
        self.channel.connect(self.client)

    def prepare(self):
        """Process the text into a stream of sentences and return it."""
        stream = []
        for line in self.buffer:
            words = line.message.split()
            if words[-1][-1] not in MarkVShaney.TERMINATORS:
                words[-1] += random.choice(tuple(MarkVShaney.TERMINATORS))
            stream.extend(words)
        return stream

    def print_summary(self, cache):
        """Print the summary provided in the given cache."""
        if cache:
            line = '~' * max(map(len, cache))
            self.client.print(line)
            for sentence in cache:
                self.client.print(sentence)
            self.client.print(line)
        else:
            self.client.print('There is nothing worth summarizing.')


def pairwise(iterable, n=2):
    """Using a window of width n, iterate over items sourced from iterable."""
    iterators = itertools.tee(iterable, n)
    for move, iterator in enumerate(iterators):
        for _ in range(move):
            next(iterator, None)
    return zip(*iterators)


class RandomCounter:
    """RandomCounter(counter) -> RandomCounter instance"""

    def __init__(self, counter, choices=random.choices):
        """Initialize the instance with population and weight data."""
        population, weights = [], []
        for key, value in counter.items():
            population.append(key)
            weights.append(value)
        self.__population = tuple(population)
        self.__cum_weights = tuple(itertools.accumulate(weights))
        self.__choices = choices

    def __iter__(self):
        """Return the iterator object itself."""
        return self

    def __next__(self):
        """Return another completely random item from the counter."""
        return self.__choices(
            self.__population, cum_weights=self.__cum_weights
        )[0]


class MarkovChain:
    """MarkovChain(iterable, n) -> MarkovChain instance"""

    def __init__(self, iterable, n):
        """Initialize the instance by building a database of usable links."""
        links = {}
        for *root, suffix in pairwise(iterable, n):
            links.setdefault(tuple(root), collections.Counter())[suffix] += 1
        self.__links = {
            key: RandomCounter(value) for key, value in links.items()
        }

    def build_chain(self, start_point):
        """Iterate over items from the chain until a dead end is found."""
        if start_point not in self.__links:
            raise KeyError(f'could not find {start_point!r} in the links')
        yield from start_point
        while True:
            try:
                random_counter = self.__links[start_point]
            except KeyError:
                break
            else:
                item = next(random_counter)
                yield item
                prefix, *root = start_point
                root.append(item)
                start_point = tuple(root)

    @property
    def keys(self):
        """Property having valid start points for building a chain."""
        return self.__links.keys()


class SpecialDeque(collections.deque):
    """SpecialDeque([iterable[, maxlen]]) -> SpecialDeque instance"""

    @property
    def prefix(self):
        """Property allowing capture of all but last item in deque."""
        item = self.pop()
        value = tuple(self)
        self.append(item)
        return value

    @property
    def suffix(self):
        """Property allowing capture of all but first item in deque."""
        item = self.popleft()
        value = tuple(self)
        self.appendleft(item)
        return value


class MarkVShaney(MarkovChain):
    """MarkVShaney(iterable, n) -> MarkVShaney instance"""

    TERMINATORS = frozenset('!;.?')
    BAD_END = frozenset(';')
    NEW_END = functools.partial(random.choice, tuple(TERMINATORS - BAD_END))

    def __init__(self, iterable, n):
        """Initialize a MarkovChain while identifying proper start words."""
        if n < 2:
            raise ValueError('chain links may not be shorter than two')
        start_words = collections.Counter()
        super().__init__(self.__get_start_words(iterable, n, start_words), n)
        self.__start_words = RandomCounter(start_words)

    @classmethod
    def __get_start_words(cls, iterable, n, start_words):
        """Transparently yield from iterable while collecting start words."""
        buffer = SpecialDeque(maxlen=n)
        for count, item in enumerate(iterable, 1):
            yield item
            buffer.append(item)
            if count == n:
                start_words[buffer.prefix] += 1
            if count >= n and buffer[0][-1] in cls.TERMINATORS:
                start_words[buffer.suffix] += 1
        if len(buffer) < n:
            raise ValueError('iterable was too short to satisfy n')

    def build_chain(self, start_point=None):
        """Build a chain and select a proper start point if not provided."""
        if start_point is None:
            start_point = next(self.__start_words)
        yield from super().build_chain(start_point)

    def build_paragraph(self, attempts, clauses=1, good_start=False,
                        good_end=False):
        """Generate some clauses that have a relationship with each other."""
        if attempts < 1:
            raise ValueError('attempts must not be less than one')
        for _ in range(attempts):
            iterator, paragraph, sentence = self.build_chain(), [], []
            while len(paragraph) < clauses:
                try:
                    word = next(iterator)
                except StopIteration:
                    break
                else:
                    sentence.append(word)
                    if word[-1] in self.TERMINATORS:
                        paragraph.append(' '.join(sentence))
                        sentence.clear()
            else:
                if good_start:
                    sentence = paragraph[0]
                    character = sentence[0]
                    if character.islower():
                        paragraph[0] = character.upper() + sentence[1:]
                if good_end:
                    sentence = paragraph[-1]
                    character = sentence[-1]
                    if character in self.BAD_END:
                        paragraph[-1] = sentence[:-1] + self.NEW_END()
                return paragraph
        return []
