def is_palindrome(text: str) -> bool:
    """Checks if a given string is a palindrome.

    A palindrome is a string that reads the same forwards and backward.
    This function ignores case and non-alphanumeric characters.

    Args:
        text: The string to check.

    Returns:
        True if the string is a palindrome, False otherwise.
        Returns False if the input is not a string.
    """
    if not isinstance(text, str):
        return False

    processed_text = ''.join(filter(str.isalnum, text)).lower()
    return processed_text == processed_text[::-1]
