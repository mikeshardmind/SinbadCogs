import numpy as np


class Die:
    """
    This is a basic die with an iterator interface

    Attributes
    ----------

    sides: int
        defaults to 6, must be a positive integer
    """

    def __init__(self, sides: int = 6):
        self.sides = int(sides)
        if sides < 1:
            raise ValueError("No negative sided dice")

    def __repr__(self):
        return "{}-sided {}".format(self.sides, self.__class__.__name__)

    def roll(self):
        """
        rolls the die
        """
        return np.random.choice(self.sides) + 1

    def rolls(self, n: int):
        """
        rolls the die multiple times

        Parameters
        ----------
        n: int
            number of rolls
        """
        for i in range(0, n):
            yield self.roll()

    def __iter__(self):
        return self

    def __next__(self):
        return self.roll()


class StatefulDie(Die):
    """
    This die exhibits the gamblers fallacy
    it's useful for tabletop, so people don't get down on a bad luck streak
    but not reccomended for gambling
    the distribution of rolls over a large sample size will be
    equivalent to a normal die, but the placement of the rolls will
    not be. You should use the same die rather than reinitialize it.

    Attributes
    ----------

    sides: int
        defaults to 6, must be a positive integer
    """

    def __init__(self, sides: int = 6):
        super().__init__(sides)
        self._rolls_since = np.ones(sides)

    def roll(self):
        result = np.random.choice(range(1, self.sides + 1), p=self._weights)
        self._rolls_since += 1
        self._rolls_since[result - 1] = 1
        return result

    @property
    def _weights(self):
        return self._rolls_since / float(sum(self._rolls_since))
