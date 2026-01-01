"""
Slug generation utility
"""
import re
import unicodedata


def generate_slug(text: str) -> str:
    """
    Generate a URL-friendly slug from text
    
    Args:
        text: Text to convert to slug
        
    Returns:
        URL-friendly slug
    """
    # Convert to lowercase
    text = text.lower()
    
    # Remove accents/diacritics
    text = unicodedata.normalize('NFKD', text)
    text = text.encode('ascii', 'ignore').decode('ascii')
    
    # Replace spaces and special characters with hyphens
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    
    # Remove leading/trailing hyphens
    text = text.strip('-')
    
    return text


def make_unique_slug(base_slug: str, existing_slugs: list, max_length: int = 255) -> str:
    """
    Make a slug unique by appending a number if needed
    
    Args:
        base_slug: Base slug to make unique
        existing_slugs: List of existing slugs
        max_length: Maximum length of the slug
        
    Returns:
        Unique slug
    """
    slug = base_slug[:max_length]
    counter = 1
    
    while slug in existing_slugs:
        suffix = f"-{counter}"
        # Ensure we don't exceed max_length
        available_length = max_length - len(suffix)
        slug = f"{base_slug[:available_length]}{suffix}"
        counter += 1
    
    return slug

