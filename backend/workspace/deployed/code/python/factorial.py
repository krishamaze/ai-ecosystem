def factorial(n: int) -> int:
    """Calculate the factorial of a non-negative integer using recursion.

    Args:
        n: The non-negative integer for which to calculate the factorial.

    Returns:
        The factorial of n.

    Raises:
        ValueError: If n is negative.
    """
    if not isinstance(n, int):
        raise TypeError("Input must be an integer.")
    if n < 0:
        raise ValueError("Factorial is not defined for negative numbers.")
    if n == 0:
        return 1
    else:
        return n * factorial(n - 1)