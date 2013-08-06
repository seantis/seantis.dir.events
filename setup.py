from setuptools import setup, find_packages
import os

version = '1.0a2'

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

setup(name='seantis.dir.events',
      version=version,
      description="Directory of upcoming Events",
      long_description="\n".join(
          (
              open("README.md").read(),
              open(os.path.join("docs", "HISTORY.txt")).read()
          )
      ),
      # Get more strings from
      # http://pypi.python.org/pypi?:action=list_classifiers
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
          'plone.app.event[ploneintegration, dexterity]>=1.0rc2',
          'plone.event>=1.0rc1',
          'plone.app.dexterity',
          'plone.formwidget.recurrence[z3cform]',
          'plone.formwidget.datetime[z3cform]>=1.0b5',
          'collective.autopermission',
          'collective.dexteritytextindexer',
          'collective.z3cform.mapwidget',
          'collective.js.underscore',
          'seantis.dir.base>=1.5.7',
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
