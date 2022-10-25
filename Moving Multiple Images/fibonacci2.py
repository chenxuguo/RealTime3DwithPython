class Fib:
    """iterator that yields numbers in the Fibonacci sequence"""

    def __init__(self, max):
        self.max = max

    def __iter__(self):
        self.a = 0
        self.b = 1
        return self

    def _next(self):
        fib = self.a
        if fib > self.max:
            raise StopIteration
        self.a, self.b = self.b, self.a + self.b
        return fib



fib = Fib(100)
print(fib)
print(fib.__class__)
print(fib.__doc__)
