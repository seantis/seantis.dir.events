# Introduction

seantis.dir.base allows to put dexterity objects into 1-4 categories, showing those categories in a browsable and searchable catalog.
To learn more about seantis.dir.base visit [https://github.com/seantis/seantis.dir.base](https://github.com/seantis/seantis.dir.base)

seantis.dir.events builds on seantis.dir.base, adding information about upcoming events

# Dependencies

seantis.dir.events relies on Plone 4.2+ with dexterity and seantis.dir.base:

# Installation

1. Use Plone 4.2 or newer

        extends =
            http://dist.plone.org/release/4.2/versions.cfg

2. Add the module to your instance eggs

        [instance]
        ...
        eggs =
            ...
            seantis.dir.events


3. Ensure that the i18n files are compiled by adding

        [instance]
        ...
        environment-vars = 
            ...
            zope_i18n_compile_mo_files true

4. Install dexterity and seantis.dir.events using portal_quickinstaller

# License

seantis.dir.events is released under GPL v2

# Maintainer

seantis.dir.events is maintained by Seantis GmbH (www.seantis.ch)