import setuptools

with open('README.md', 'r') as fh:
    long_description = fh.read()

setuptools.setup(
    name='imdb-sqlite',
    version='0.1.3',
    author='Jonas Tingeborn',
    author_email='tinjon+pip@gmail.com',
    description='Imports IMDB TSV files into a SQLite database',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/jojje/imdb-sqlite',
    packages=setuptools.find_packages(),
    license='GNU GPL v2',
    entry_points={
        'console_scripts': ['imdb-sqlite=imdb_sqlite.__main__:main'],
    },
    install_requires=[
        'tqdm>=4.4.1',
    ],
    classifiers=(
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
        'Operating System :: OS Independent',
    ),
)
