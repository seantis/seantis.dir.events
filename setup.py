from setuptools import setup, find_packages
import os

version = '1.0a1'

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
          'plone.app.event[ploneintegration, dexterity]',
          'plone.app.dexterity',
          'plone.app.testing',
          'plone.formwidget.recurrence[z3cform]',
          'plone.formwidget.datetime[z3cform]',
          'collective.autopermission',
          'collective.testcaselayer',
          'collective.dexteritytextindexer',
          'collective.z3cform.mapwidget',
          'seantis.dir.base>=1.5.2',
          'zope.proxy',
          'pytz',
          'python-magic',
          'mock',
          'M2Crypto',
          'lxml',
          'blist',
          'functools32',
          'isodate',
          'icalendar',
          'collective.betterbrowser'
      ],
      entry_points="""
      [z3c.autoinclude.plugin]
      target = plone
      """,
      )
