import os
import textwrap


def assert_unix():
    """ Asserts that the current platform is unix. This serves as a runtime
    error to users that start seantis.dir.events on windows and it also
    documents where platform independence has not yet been achieved.

    """

    assert os.name == 'posix', textwrap.dedent("""

    ##########################################################
    seantis.dir.events currently only supports unix/osx/linux.
    ##########################################################
    """)