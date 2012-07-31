def format_explanation(explanation, indent='  ', indent_level=0):
    """Return explanation in an easier to read format

    Easier to read for me, at least.

    """
    if not explanation:
        return ''

    # Note: This is probably a crap implementation, but it's an
    # interesting starting point for a better formatter.
    line = ('%s%s %2.4f' % ((indent * indent_level),
                            explanation['description'],
                            explanation['value']))

    if 'details' in explanation:
        details = '\n'.join(
            [format_explanation(subtree, indent, indent_level + 1)
             for subtree in explanation['details']])
        return line + '\n' + details

    return line
