from setuptools import setup, find_packages
import os

name = 'seantis.dir.events'
description = (
    "Directory of upcoming Events."
)
version = '1.2.2'


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
    'plone.app.testing',
    'mock'
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
          'plone.app.event[ploneintegration, dexterity]>=1.0.3',
          'plone.event>=1.0',
          'plone.app.dexterity',
          'plone.synchronize',
          'plone.formwidget.recurrence[z3cform]>=1.1',
          'plone.formwidget.datetime[z3cform]>=1.0',
          'collective.autopermission',
          'collective.dexteritytextindexer',
          'collective.z3cform.mapwidget',
          'collective.js.underscore',
          'seantis.dir.base>=1.7',
          'seantis.plonetools>=0.9',
          'zope.proxy',
          'pytz',
          'python-magic',
          'lxml',
          'blist',
          'functools32',
          'isodate',
          'icalendar>=3.5',
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
