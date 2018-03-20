import numpy as np
import itertools


class Deck:
    """
    A Deck of cards with an iterator interface

    Attributes
    ----------
    deck_count: int
        this defaults to 1
        You can use this to make a pool of decks
    cards: list
        this should be a list of card values (for custom decks)
        if ommited, cards will be returned in the form
        (suit, value)
        for the standard 52 card deck without jokers
    autoreshuffle: bool
        defaults to false
        when true, anytime the deck is empty, cards will be returned
        to the deck and reshuffled
    """
    _suits = ['Spades', 'Diamonds', 'Clubs', 'Hearts']

    _vals = [
        'Ace',
        'King',
        'Queen',
        'Jack',
        '10', '9', '8', '7', '6', '5', '4', '3', '2'
    ]

    def __init__(self, *,
                 deck_count: int=1,
                 cards: list=None,
                 autoreshuffle: bool=False):
        self._deck_count = deck_count
        self.autoreshuffle = autoreshuffle
        self._cards = cards if cards is not None else list(
            itertools.product(self._suits, self._vals)
        )
        self.reset_deck()

    def __repr__(self):
        return "{}-card deck".format(len(self))

    def __len__(self):
        return self._deck_count * len(self._cards)

    def reset_deck(self):
        """
        resets the deck to it's original state
        """
        self._deck = {
            k: int(self._deck_count) for k in self._cards
        }

    def insert(self, card):
        """
        puts a card back into the deck at a random position

        Raises
        ------
        AttributeError
            This is raised if you try to put a card that shouldnt
            belong in this deck into it.
        """
        if card not in self._deck:
            raise AttributeError("That card isn't in this deck")
        elif self._deck[card] == self._deck_count:
            raise AttributeError(
                "You already have the maximum valid cards of this type"
                " in the deck"
            )
        else:
            self._deck[card] += 1

    def draw(self):
        """
        draws a random card from the remaining cards

        Raises
        ------
        AttributeError
            The deck is empty and is not set up to be reshuffled automatically
        """
        if self.remaining_cards == 0:
            if self.autoreshuffle:
                self.reset_deck()
            else:
                raise AttributeError("Empty deck can't be drawn from")
        possible = [k for k, v in self._deck.items() if v > 0]
        weights = [
            float(v) / self.remaining_cards
            for v in [
                self._deck[k] for k in possible
            ]
        ]

        idx = np.random.choice(range(0, len(possible)), p=weights)
        card = possible[idx]
        self._deck[card] -= 1
        return card

    @property
    def remaining_cards(self):
        return sum(self._deck.values())

    def __iter__(self):
        return self

    def __next__(self):
        if self.remaining_cards > 0:
            return self.draw()
        else:
            if self.autoreshuffle:
                return self.draw()
            else:
                raise StopIteration
