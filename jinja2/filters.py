# -*- coding: utf-8 -*-
"""
    jinja2.filters
    ~~~~~~~~~~~~~~

    Bundled jinja filters.

    :copyright: 2008 by Armin Ronacher, Christoph Hack.
    :license: BSD, see LICENSE for more details.
"""
import re
import math
from random import choice
try:
    from operator import itemgetter
except ImportError:
    itemgetter = lambda a: lambda b: b[a]
from urllib import urlencode, quote
from itertools import imap, groupby
from jinja2.utils import Markup, escape, pformat, urlize, soft_unicode
from jinja2.runtime import Undefined


_striptags_re = re.compile(r'(<!--.*?-->|<[^>]*>)')


def contextfilter(f):
    """Decorator for marking context dependent filters. The current context
    argument will be passed as first argument.
    """
    if getattr(f, 'environmentfilter', False):
        raise TypeError('filter already marked as environment filter')
    f.contextfilter = True
    return f


def environmentfilter(f):
    """Decorator for marking evironment dependent filters.  The environment
    used for the template is passed to the filter as first argument.
    """
    if getattr(f, 'contextfilter', False):
        raise TypeError('filter already marked as context filter')
    f.environmentfilter = True
    return f


def do_forceescape(value):
    """Enforce HTML escaping.  This will probably double escape variables."""
    if hasattr(value, '__html__'):
        value = value.__html__()
    return escape(unicode(value))


@environmentfilter
def do_replace(environment, s, old, new, count=None):
    """Return a copy of the value with all occurrences of a substring
    replaced with a new one. The first argument is the substring
    that should be replaced, the second is the replacement string.
    If the optional third argument ``count`` is given, only the first
    ``count`` occurrences are replaced:

    .. sourcecode:: jinja

        {{ "Hello World"|replace("Hello", "Goodbye") }}
            -> Goodbye World

        {{ "aaaaargh"|replace("a", "d'oh, ", 2) }}
            -> d'oh, d'oh, aaargh
    """
    if count is None:
        count = -1
    if not environment.autoescape:
        return unicode(s).replace(unicode(old), unicode(new), count)
    if hasattr(old, '__html__') or hasattr(new, '__html__') and \
       not hasattr(s, '__html__'):
        s = escape(s)
    else:
        s = soft_unicode(s)
    return s.replace(old, new, count)


def do_upper(s):
    """Convert a value to uppercase."""
    return soft_unicode(s).upper()


def do_lower(s):
    """Convert a value to lowercase."""
    return soft_unicode(s).lower()


@environmentfilter
def do_xmlattr(_environment, *args, **kwargs):
    """Create an SGML/XML attribute string based on the items in a dict.
    All values that are neither `none` nor `undefined` are automatically
    escaped:

    .. sourcecode:: html+jinja

        <ul{{ {'class': 'my_list', 'missing': None,
                'id': 'list-%d'|format(variable)}|xmlattr }}>
        ...
        </ul>

    Results in something like this:

    .. sourcecode:: html

        <ul class="my_list" id="list-42">
        ...
        </ul>

    As you can see it automatically prepends a space in front of the item
    if the filter returned something.
    """
    rv = u' '.join(
        u'%s="%s"' % (escape(key), escape(value))
        for key, value in dict(*args, **kwargs).iteritems()
        if value is not None and not isinstance(value, Undefined)
    )
    if rv:
        rv = u' ' + rv
    if _environment.autoescape:
        rv = Markup(rv)
    return rv


def do_capitalize(s):
    """Capitalize a value. The first character will be uppercase, all others
    lowercase.
    """
    return soft_unicode(s).capitalize()


def do_title(s):
    """Return a titlecased version of the value. I.e. words will start with
    uppercase letters, all remaining characters are lowercase.
    """
    return soft_unicode(s).title()


def do_dictsort(value, case_sensitive=False, by='key'):
    """ Sort a dict and yield (key, value) pairs. Because python dicts are
    unsorted you may want to use this function to order them by either
    key or value:

    .. sourcecode:: jinja

        {% for item in mydict|dictsort %}
            sort the dict by key, case insensitive

        {% for item in mydict|dicsort(true) %}
            sort the dict by key, case sensitive

        {% for item in mydict|dictsort(false, 'value') %}
            sort the dict by key, case insensitive, sorted
            normally and ordered by value.
    """
    if by == 'key':
        pos = 0
    elif by == 'value':
        pos = 1
    else:
        raise FilterArgumentError('You can only sort by either '
                                  '"key" or "value"')
    def sort_func(item):
        value = item[pos]
        if isinstance(value, basestring):
            value = unicode(value)
            if not case_sensitive:
                value = value.lower()
        return value

    return sorted(value.items(), key=sort_func)


def do_default(value, default_value=u'', boolean=False):
    """If the value is undefined it will return the passed default value,
    otherwise the value of the variable:

    .. sourcecode:: jinja

        {{ my_variable|default('my_variable is not defined') }}

    This will output the value of ``my_variable`` if the variable was
    defined, otherwise ``'my_variable is not defined'``. If you want
    to use default with variables that evaluate to false you have to
    set the second parameter to `true`:

    .. sourcecode:: jinja

        {{ ''|default('the string was empty', true) }}
    """
    if (boolean and not value) or isinstance(value, Undefined):
        return default_value
    return value


@environmentfilter
def do_join(environment, value, d=u''):
    """Return a string which is the concatenation of the strings in the
    sequence. The separator between elements is an empty string per
    default, you can define ith with the optional parameter:

    .. sourcecode:: jinja

        {{ [1, 2, 3]|join('|') }}
            -> 1|2|3

        {{ [1, 2, 3]|join }}
            -> 123
    """
    # no automatic escaping?  joining is a lot eaiser then
    if not environment.autoescape:
        return unicode(d).join(imap(unicode, value))

    # if the delimiter doesn't have an html representation we check
    # if any of the items has.  If yes we do a coercion to Markup
    if not hasattr(d, '__html__'):
        value = list(value)
        do_escape = False
        for idx, item in enumerate(value):
            if hasattr(item, '__html__'):
                do_escape = True
            else:
                value[idx] = unicode(item)
        if do_escape:
            d = escape(d)
        else:
            d = unicode(d)
        return d.join(value)

    # no html involved, to normal joining
    return soft_unicode(d).join(imap(soft_unicode, value))


def do_center(value, width=80):
    """Centers the value in a field of a given width."""
    return unicode(value).center(width)


@environmentfilter
def do_first(environment, seq):
    """Return the frist item of a sequence."""
    try:
        return iter(seq).next()
    except StopIteration:
        return environment.undefined('No first item, sequence was empty.')


@environmentfilter
def do_last(environment, seq):
    """Return the last item of a sequence."""
    try:
        return iter(reversed(seq)).next()
    except StopIteration:
        return environment.undefined('No last item, sequence was empty.')


@environmentfilter
def do_random(environment, seq):
    """Return a random item from the sequence."""
    try:
        return choice(seq)
    except IndexError:
        return environment.undefined('No random item, sequence was empty.')


def do_filesizeformat(value):
    """Format the value like a 'human-readable' file size (i.e. 13 KB,
    4.1 MB, 102 bytes, etc).
    """
    # fail silently
    try:
        bytes = float(value)
    except TypeError:
        bytes = 0

    if bytes < 1024:
        return "%d Byte%s" % (bytes, bytes != 1 and 's' or '')
    elif bytes < 1024 * 1024:
        return "%.1f KB" % (bytes / 1024)
    elif bytes < 1024 * 1024 * 1024:
        return "%.1f MB" % (bytes / (1024 * 1024))
    return "%.1f GB" % (bytes / (1024 * 1024 * 1024))


def do_pprint(value, verbose=False):
    """Pretty print a variable. Useful for debugging.

    With Jinja 1.2 onwards you can pass it a parameter.  If this parameter
    is truthy the output will be more verbose (this requires `pretty`)
    """
    return pformat(value, verbose=verbose)


def do_urlize(value, trim_url_limit=None, nofollow=False):
    """Converts URLs in plain text into clickable links.

    If you pass the filter an additional integer it will shorten the urls
    to that number. Also a third argument exists that makes the urls
    "nofollow":

    .. sourcecode:: jinja

        {{ mytext|urlize(40, True) }}
            links are shortened to 40 chars and defined with rel="nofollow"
    """
    return urlize(soft_unicode(value), trim_url_limit, nofollow)


def do_indent(s, width=4, indentfirst=False):
    """
    {{ s|indent[ width[ indentfirst[ usetab]]] }}

    Return a copy of the passed string, each line indented by
    4 spaces. The first line is not indented. If you want to
    change the number of spaces or indent the first line too
    you can pass additional parameters to the filter:

    .. sourcecode:: jinja

        {{ mytext|indent(2, True) }}
            indent by two spaces and indent the first line too.
    """
    indention = ' ' * width
    if indentfirst:
        return u'\n'.join(indention + line for line in s.splitlines())
    return s.replace('\n', '\n' + indention)


def do_truncate(s, length=255, killwords=False, end='...'):
    """
    Return a truncated copy of the string. The length is specified
    with the first parameter which defaults to ``255``. If the second
    parameter is ``true`` the filter will cut the text at length. Otherwise
    it will try to save the last word. If the text was in fact
    truncated it will append an ellipsis sign (``"..."``). If you want a
    different ellipsis sign than ``"..."`` you can specify it using the
    third parameter.

    .. sourcecode jinja::

        {{ mytext|truncate(300, false, '&raquo;') }}
            truncate mytext to 300 chars, don't split up words, use a
            right pointing double arrow as ellipsis sign.
    """
    if len(s) <= length:
        return s
    elif killwords:
        return s[:length] + end
    words = s.split(' ')
    result = []
    m = 0
    for word in words:
        m += len(word) + 1
        if m > length:
            break
        result.append(word)
    result.append(end)
    return u' '.join(result)


def do_wordwrap(s, pos=79, hard=False):
    """
    Return a copy of the string passed to the filter wrapped after
    ``79`` characters. You can override this default using the first
    parameter. If you set the second parameter to `true` Jinja will
    also split words apart (usually a bad idea because it makes
    reading hard).
    """
    if len(s) < pos:
        return s
    if hard:
        return u'\n'.join(s[idx:idx + pos] for idx in
                          xrange(0, len(s), pos))

    # TODO: switch to wordwrap.wrap
    # code from http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/148061
    return reduce(lambda line, word, pos=pos: u'%s%s%s' %
                  (line, u' \n'[(len(line)-line.rfind('\n') - 1 +
                                len(word.split('\n', 1)[0]) >= pos)],
                   word), s.split(' '))


def do_wordcount(s):
    """Count the words in that string."""
    return len(s.split())


def do_int(value, default=0):
    """Convert the value into an integer. If the
    conversion doesn't work it will return ``0``. You can
    override this default using the first parameter.
    """
    try:
        return int(value)
    except (TypeError, ValueError):
        # this quirk is necessary so that "42.23"|int gives 42.
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return default


def do_float(value, default=0.0):
    """Convert the value into a floating point number. If the
    conversion doesn't work it will return ``0.0``. You can
    override this default using the first parameter.
    """
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def do_format(value, *args, **kwargs):
    """
    Apply python string formatting on an object:

    .. sourcecode:: jinja

        {{ "%s - %s"|format("Hello?", "Foo!") }}
            -> Hello? - Foo!
    """
    if kwargs:
        kwargs.update(idx, arg in enumerate(args))
        args = kwargs
    return soft_unicode(value) % args


def do_trim(value):
    """Strip leading and trailing whitespace."""
    return soft_unicode(value).strip()


def do_striptags(value):
    """Strip SGML/XML tags and replace adjacent whitespace by one space.
    """
    if hasattr(value, '__html__'):
        value = value.__html__()
    return u' '.join(_striptags_re.sub('', value).split())


def do_slice(value, slices, fill_with=None):
    """Slice an iterator and return a list of lists containing
    those items. Useful if you want to create a div containing
    three div tags that represent columns:

    .. sourcecode:: html+jinja

        <div class="columwrapper">
          {%- for column in items|slice(3) %}
            <ul class="column-{{ loop.index }}">
            {%- for item in column %}
              <li>{{ item }}</li>
            {%- endfor %}
            </ul>
          {%- endfor %}
        </div>

    If you pass it a second argument it's used to fill missing
    values on the last iteration.
    """
    seq = list(value)
    length = len(seq)
    items_per_slice = length // slices
    slices_with_extra = length % slices
    offset = 0
    for slice_number in xrange(slices):
        start = offset + slice_number * items_per_slice
        if slice_number < slices_with_extra:
            offset += 1
        end = offset + (slice_number + 1) * items_per_slice
        tmp = seq[start:end]
        if fill_with is not None and slice_number >= slices_with_extra:
            tmp.append(fill_with)
        yield tmp


def do_batch(value, linecount, fill_with=None):
    """
    A filter that batches items. It works pretty much like `slice`
    just the other way round. It returns a list of lists with the
    given number of items. If you provide a second parameter this
    is used to fill missing items. See this example:

    .. sourcecode:: html+jinja

        <table>
        {%- for row in items|batch(3, '&nbsp;') %}
          <tr>
          {%- for column in row %}
            <tr>{{ column }}</td>
          {%- endfor %}
          </tr>
        {%- endfor %}
        </table>
    """
    result = []
    tmp = []
    for item in value:
        if len(tmp) == linecount:
            yield tmp
            tmp = []
        tmp.append(item)
    if tmp:
        if fill_with is not None and len(tmp) < linecount:
            tmp += [fill_with] * (linecount - len(tmp))
        yield tmp


def do_round(value, precision=0, method='common'):
    """Round the number to a given precision. The first
    parameter specifies the precision (default is ``0``), the
    second the rounding method:

    - ``'common'`` rounds either up or down
    - ``'ceil'`` always rounds up
    - ``'floor'`` always rounds down

    If you don't specify a method ``'common'`` is used.

    .. sourcecode:: jinja

        {{ 42.55|round }}
            -> 43
        {{ 42.55|round(1, 'floor') }}
            -> 42.5
    """
    if not method in ('common', 'ceil', 'floor'):
        raise FilterArgumentError('method must be common, ceil or floor')
    if precision < 0:
        raise FilterArgumentError('precision must be a postive integer '
                                  'or zero.')
    if method == 'common':
        return round(value, precision)
    func = getattr(math, method)
    if precision:
        return func(value * 10 * precision) / (10 * precision)
    else:
        return func(value)


def do_sort(value, reverse=False):
    """Sort a sequence. Per default it sorts ascending, if you pass it
    `True` as first argument it will reverse the sorting.
    """
    return sorted(value, reverse=reverse)


@environmentfilter
def do_groupby(environment, value, attribute):
    """Group a sequence of objects by a common attribute.

    If you for example have a list of dicts or objects that represent persons
    with `gender`, `first_name` and `last_name` attributes and you want to
    group all users by genders you can do something like the following
    snippet:

    .. sourcecode:: html+jinja

        <ul>
        {% for group in persons|groupby('gender') %}
            <li>{{ group.grouper }}<ul>
            {% for person in group.list %}
                <li>{{ person.first_name }} {{ person.last_name }}</li>
            {% endfor %}</ul></li>
        {% endfor %}
        </ul>

    Additionally it's possible to use tuple unpacking for the grouper and
    list:

    .. sourcecode:: html+jinja

        <ul>
        {% for grouper, list in persons|groupby('gender') %}
            ...
        {% endfor %}
        </ul>

    As you can see the item we're grouping by is stored in the `grouper`
    attribute and the `list` contains all the objects that have this grouper
    in common.
    """
    expr = lambda x: environment.subscribe(x, attribute)
    return sorted(map(_GroupTuple, groupby(sorted(value, key=expr), expr)))


class _GroupTuple(tuple):
    __slots__ = ()
    grouper = property(itemgetter(0))
    list = property(itemgetter(1))

    def __new__(cls, (key, value)):
        return tuple.__new__(cls, (key, list(value)))


FILTERS = {
    'replace':              do_replace,
    'upper':                do_upper,
    'lower':                do_lower,
    'escape':               escape,
    'e':                    escape,
    'forceescape':          do_forceescape,
    'capitalize':           do_capitalize,
    'title':                do_title,
    'default':              do_default,
    'd':                    do_default,
    'join':                 do_join,
    'count':                len,
    'dictsort':             do_dictsort,
    'length':               len,
    'reverse':              reversed,
    'center':               do_center,
    'indent':               do_indent,
    'title':                do_title,
    'capitalize':           do_capitalize,
    'first':                do_first,
    'last':                 do_last,
    'random':               do_random,
    'filesizeformat':       do_filesizeformat,
    'pprint':               do_pprint,
    'truncate':             do_truncate,
    'wordwrap':             do_wordwrap,
    'wordcount':            do_wordcount,
    'int':                  do_int,
    'float':                do_float,
    'string':               soft_unicode,
    'list':                 list,
    'urlize':               do_urlize,
    'format':               do_format,
    'trim':                 do_trim,
    'striptags':            do_striptags,
    'slice':                do_slice,
    'batch':                do_batch,
    'sum':                  sum,
    'abs':                  abs,
    'round':                do_round,
    'sort':                 do_sort,
    'groupby':              do_groupby,
    'safe':                 Markup,
    'xmlattr':              do_xmlattr
}
