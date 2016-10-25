from setuptools import setup, find_packages
import os

name = 'seantis.dir.events'
description = (
    "Directory of upcoming Events."
)
version = '1.8'


def get_long_description():
    readme = open('README.rst').read()
    history = open(os.path.join('docs', 'HISTORY.rst')).read()
    contributors = open(os.path.join('docs', 'CONTRIBUTORS.rst')).read()

    # cut the part before the description to avoid repetition on pypi
    readme = readme[readme.index(description) + len(description):]

    return '\n'.join((readme, contributors, history))

zug_require = [
    'ftw.contentmenu',
    'izug.basetheme',
]
teamraum_require = [
    'plonetheme.teamraum'
]
tests_require = [
    'collective.betterbrowser>=0.4',
    'collective.testcaselayer',
    'mock',
    'plone.app.testing',
    'unittest2',
]

setup(name=name, version=version, description=description,
      long_description=get_long_description(),
      classifiers=[
          "Framework :: Plone",
          "Programming Language :: Python",
      ],
      keywords='',
      author='Seantis GmbH',
      author_email='info@seantis.ch',
      url='https://github.com/seantis/seantis.dir.events',
      license='GPL',
      packages=find_packages(exclude=['ez_setup']),
      namespace_packages=['seantis', 'seantis.dir'],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'setuptools',
          'Plone>=4.3',
          'python-dateutil',
          'plone.app.event[dexterity]>=1.1.6',
          'plone.app.jquerytools',
          'plone.event>=1.3',
          'plone.app.dexterity',
          'plone.synchronize',
          'plone.formwidget.recurrence[z3cform]>=1.1',
          'plone.formwidget.datetime[z3cform]>=1.0',
          'plone.protect',
          'collective.autopermission',
          'collective.dexteritytextindexer',
          'collective.z3cform.mapwidget',
          'collective.js.underscore',
          'seantis.dir.base>=1.8.1',
          'seantis.plonetools>=0.18',
          'zope.proxy',
          'pytz',
          'python-magic',
          'lxml',
          'blist',
          'functools32',
          'isodate',
          'icalendar>=3.9.2',
      ],
      extras_require=dict(
          zug=zug_require,
          teamraum=teamraum_require,
          tests=tests_require
      ),
      entry_points="""
      [z3c.autoinclude.plugin]
      target = plone
      """,
      )
