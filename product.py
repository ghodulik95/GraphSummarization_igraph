from sortedcontainers import SortedList
import primefac
from gmpy2 import mpfr

class Rational:
    def __init__(self):
        self.numerator = SortedList()
        self.denominator = SortedList()

    def multiply_by(self,f):
        self.numerator.update(primefac.primefac(f))

    def divide_by(self,d):
        self.denominator.update(primefac.primefac(d))

    def value(self):
        if len(self.numerator) == 0 or len(self.denominator) == 0:
            return None
        numerator_index = 0
        denominator_index = 0
        while numerator_index < len(self.numerator) and denominator_index < len(self.denominator):
            if self.numerator[numerator_index] == self.denominator[denominator_index]:
                del self.numerator[numerator_index]
                del self.denominator[denominator_index]
            elif self.numerator[numerator_index] < self.denominator[denominator_index]:
                numerator_index += 1
            else:
                denominator_index += 1

        self.numerator.add(1)
        self.denominator.add(1)
        num_product = reduce(lambda x, y: mpfr(x)*y, self.numerator)
        den_product = reduce(lambda x, y: mpfr(x)*y, self.denominator)
        if num_product <= 0 or den_product <= 0:
            return 0
        val = num_product/den_product
        if val > 1:
           return 1

        return val

if __name__ == "__main__":
    r = Rational()
    r.multiply_by(2)
    r.multiply_by(3)
    r.multiply_by(4)
    r.divide_by(3)
    r.divide_by(50)
    print r.numerator
    print r.denominator
    print r.value()