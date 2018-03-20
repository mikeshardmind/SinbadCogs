import numpy as np
from typing import Hashable, Iterable


class Selector:

    def __init__(self, *selectfrom):
        self.selectable = set(selectfrom)

    def select(self, *exclude):
        return np.random.choice([
            s for s in self.selectable if s not in exclude
        ])

    def insert(self, *items):
        self.selectable += set(items)

    def remove(self, *items):
        self.selectable -= set(items)

    def __iter__(self):
        return self

    def __next__(self):
        return self.select()


class StatefulSelector:

    def __init__(self,
                 selectfrom: Iterable[Hashable],
                 *, backtoback: bool=False):
        self.selectable = {
            k: 1 for k in selectfrom
        }
        self.backtoback = backtoback
        self.last = None

    def insert(self, *items):
        bias = sum(self.selectable.values()) / len(self.selectable.values())
        self.selectable.update(
            {k: bias for k in items}
        )

    def remove(self, *items):
        self.selectable = {
            k: v for k, v in self.selectable.items()
            if k not in items
        }

    def select(self, *exclude):
        items, bias = zip(
            *[(i, b) for i, b in self.selectable
              if i not in exclude]
        )
        weights = self.weights_from_bias(bias)
        choice = np.random.choice(items, p=weights)

        self.selectable = {
            k: v + 1 for k, v in self.selectable
        }
        self.selectable[choice] = 1
        self.last = choice
        return choice

    @staticmethod
    def weights_from_bias(bias: list):
        return [float(b) / sum(bias) for b in bias]

    def __next__(self):
        if self.backtoback:
            return self.choice()
        else:
            return self.choice(self.last)
