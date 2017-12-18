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
    'MarkVShaney'
]

import random

from . import common


class MarkVShaney(common.Handler):
    """MarkVShaney(client, buffer, size, channel) -> MarkVShaney instance"""

    markov_chain_length = 3
    max_summary_failing = 5

    def __init__(self, client, buffer, size, channel):
        """Initialize the handler for summarizing the channel."""
        super().__init__(client)
        self.buffer = buffer
        self.size = size
        self.channel = channel

    def handle(self):
        """Provide a Mark V Shaney summary of the channel and return."""
        arrays = self.prepare()
        mcv_len = self.markov_chain_length
        start = tuple(map(lambda words: tuple(words[:mcv_len - 1]), arrays))
        stop = tuple(map(lambda words: tuple(words[-mcv_len:]), arrays))
        chains = self.create_chains(arrays)
        cache = self.create_summary(start, stop, chains)
        self.print_summary(cache)
        self.channel.connect(self.client)

    def prepare(self):
        """Process the text into sentences and return them."""
        sentences = []
        for line in self.buffer:
            words = line.message.split()
            if len(words) >= self.markov_chain_length:
                sentences.append(tuple(words))
        self.size = min(self.size, len(sentences))
        return tuple(sentences)

    def create_chains(self, arrays):
        """Create the chains uses to create the randomized sentences."""
        chains = {}
        for sentence in arrays:
            length = len(sentence)
            if length >= self.markov_chain_length:
                diff = 1 - self.markov_chain_length
                for index in range(length + diff):
                    end = index - diff
                    key = tuple(sentence[index:end])
                    value = sentence[end]
                    if key in chains:
                        chains[key].append(value)
                    else:
                        chains[key] = [value]
        return chains

    def create_summary(self, start, stop, chains):
        """Create the random sentences that make up the summary."""
        cache = []
        for sentence in range(self.size):
            for attempt in range(self.max_summary_failing):
                sentence = self.create_sentence(start, stop, chains)
                if sentence not in cache:
                    break
            else:
                return cache
            cache.append(sentence)
        return cache

    def create_sentence(self, start, stop, chains):
        """Create a single Markov V Shaney sentence for the summary."""
        choice = random.SystemRandom().choice
        sentence = []
        key = choice(start)
        sentence.extend(key)
        while True:
            sentence.append(choice(chains[key]))
            if tuple(sentence[-self.markov_chain_length:]) in stop:
                return ' '.join(sentence)
            key = tuple(sentence[1 - self.markov_chain_length:])

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
