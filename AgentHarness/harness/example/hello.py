"""Example module providing basic arithmetic operations."""


def add(a: int, b: int) -> int:
    """Return the sum of two integers.

    Args:
        a: The first integer.
        b: The second integer.

    Returns:
        The sum of a and b.
    """
    return a + b


def main() -> None:
    """Entry point for the hello module demo."""
    result = add(3, 4)
    print(f"add(3, 4) = {result}")


if __name__ == "__main__":
    main()
