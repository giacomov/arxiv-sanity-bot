from arxiv_sanity_bot.config import ABSTRACT_ALLOWED_CHARACTERS


def sanitize_text(text: str) -> str:
    text = text.replace("\n", " ")

    # Remove extra white spaces
    text = " ".join(text.split())

    # Remove extraneous characters
    allowed_characters = set(ABSTRACT_ALLOWED_CHARACTERS)
    text = "".join(char for char in text if char in allowed_characters)

    # Remove double spaces
    return " ".join(text.split())
