from setuptools import setup, find_packages
import os

version = '1.0a1'

setup(name='seantis.dir.events',
      version=version,
      description="Directory of upcoming Events",
      long_description=open("README.md").read() + "\n" +
                       open(os.path.join("docs", "HISTORY.txt")).read(),
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
          'Plone',
          'python-dateutil',
          'plone.app.event',
          'plone.app.dexterity',
          'collective.autopermission',
          'collective.testcaselayer',
          'collective.dexteritytextindexer',
          'seantis.dir.base',
          'zope.proxy'
      ],
      entry_points="""
      [z3c.autoinclude.plugin]
      target = plone
      """,
      )
