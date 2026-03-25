"""Input validation utilities."""


def validate_pin(pin: str) -> tuple[bool, str]:
    """Validate PIN: 4-8 digits."""
    if not pin:
        return False, "Le PIN ne peut pas être vide."
    if not pin.isdigit():
        return False, "Le PIN doit contenir uniquement des chiffres."
    if len(pin) < 4:
        return False, "Le PIN doit contenir au moins 4 chiffres."
    if len(pin) > 8:
        return False, "Le PIN ne peut pas dépasser 8 chiffres."
    return True, ""


def validate_password(password: str) -> tuple[bool, str]:
    """Validate password: minimum 8 characters."""
    if not password:
        return False, "Le mot de passe ne peut pas être vide."
    if len(password) < 8:
        return False, "Le mot de passe doit contenir au moins 8 caractères."
    return True, ""


def validate_tag_name(name: str) -> tuple[bool, str]:
    """Validate tag name."""
    name = name.strip()
    if not name:
        return False, "Le nom du tag ne peut pas être vide."
    if len(name) > 30:
        return False, "Le nom du tag ne peut pas dépasser 30 caractères."
    return True, ""
