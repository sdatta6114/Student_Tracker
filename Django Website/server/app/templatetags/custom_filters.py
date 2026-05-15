from django import template

# Initialize the template library
register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Allows fetching a dictionary value using a dynamic key in templates.
    Used for showing student attendance status badges.
    """
    if dictionary:
        return dictionary.get(key)
    return None