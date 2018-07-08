#!/usr/bin/env python
#
# imdb-sqlite - Imports IMDB TSV files into a SQLite database
# Copyright (C) 2018  Jonas Tingeborn
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
import argparse
import gzip
import logging
import os
import shutil
import sqlite3
import sys
from collections import OrderedDict
from contextlib import contextmanager

from tqdm import tqdm

try:
    from urllib.request import urlopen
except ImportError:
    from urllib2 import urlopen

logger = logging.getLogger('imdbimporter')


class Column:
    """Table column configuration"""
    def __init__(self, name, type='VARCHAR', pk=None, index=None, unique=None, null=True):
        self.name = name
        self.type = type
        self.pk = pk
        self.index = index
        self.unique = unique
        self.null = null


# Files and their corresponding mapping functions used to import into the
# database. The files are imported in order listed, and are obtained from:
# https://www.imdb.com/interfaces/

# <filename>: ( <table-name>, {<tsv-header>: column} )
TSV_TABLE_MAP = OrderedDict([
    ('name.basics.tsv.gz',
        ('people', OrderedDict([
            ('nconst',            Column(name='person_id', type='VARCHAR PRIMARY KEY')),
            ('primaryName',       Column(name='name', index=True)),
            ('birthYear',         Column(name='born', type='INTEGER')),
            ('deathYear',         Column(name='died', type='INTEGER')),
        ]))),
    ('title.basics.tsv.gz',
        ('titles', OrderedDict([
            ('tconst',            Column(name='title_id', type='VARCHAR PRIMARY KEY')),
            ('titleType',         Column(name='type', index=True)),
            ('primaryTitle',      Column(name='primary_title', index=True)),
            ('originalTitle',     Column(name='original_title', index=True)),
            ('isAdult',           Column(name='is_adult', type='INTEGER')),
            ('startYear',         Column(name='premiered', type='INTEGER')),
            ('endYear',           Column(name='ended', type='INTEGER')),
            ('runtimeMinutes',    Column(name='runtime_minutes', type='INTEGER')),
            ('genres',            Column(name='genres')),
        ]))),
    ('title.akas.tsv.gz',
        ('akas', OrderedDict([
            ('titleId',           Column(name='title_id', index=True)),
            ('title',             Column(name='title', index=True)),
            ('region',            Column(name='region')),
            ('language',          Column(name='language')),
            ('types',             Column(name='types')),
            ('attributes',        Column(name='attributes')),
            ('isOriginalTitle',   Column(name='is_original_title', type='INTEGER')),
        ]))),
    ('title.principals.tsv.gz',
        ('crew', OrderedDict([
            ('tconst',            Column(name='title_id', index=True)),
            ('nconst',            Column(name='person_id', index=True)),
            ('category',          Column(name='category')),
            ('job',               Column(name='job')),
            ('characters',        Column(name='characters')),
        ]))),
    ('title.episode.tsv.gz',
        ('episodes', OrderedDict([
            ('tconst',            Column(name='episode_title_id', type='INTEGER', index=True)),
            ('parentTconst',      Column(name='show_title_id', type='INTEGER', index=True)),
            ('seasonNumber',      Column(name='season_number', type='INTEGER')),
            ('episodeNumber',     Column(name='eposide_number', type='INTEGER')),
        ]))),
    ('title.ratings.tsv.gz',
        ('ratings', OrderedDict([
            ('tconst',            Column(name='title_id', type='VARCHAR PRIMARY KEY')),
            ('averageRating',     Column(name='rating', type='INTEGER')),
            ('numVotes',          Column(name='votes', type='INTEGER')),
        ]))),
])


class Database:
    """ Shallow DB abstraction """

    def __init__(self, uri=':memory:'):
        exists = os.path.exists(uri)
        self.connection = sqlite3.connect(uri, isolation_level=None)
        self.connection.executescript("""
            PRAGMA encoding="UTF-8";
            PRAGMA foreign_keys=TRUE;
            PRAGMA synchronous=OFF;
        """)

        if not exists:
            logger.info('Applying schema')
            self.create_tables()

        # using a cursor is a smidgen faster, due to fewer function calls
        self.cursor = self.connection.cursor()

    def create_tables(self):
        sqls = [self._create_table_sql(table, mapping.values())
                for table, mapping in TSV_TABLE_MAP.values()]
        sql = '\n'.join(sqls)
        logger.debug(sql)
        self.connection.executescript(sql)

    def create_indices(self):
        sqls = [self._create_index_sql(table, mapping.values())
                for table, mapping in TSV_TABLE_MAP.values()]
        sql = '\n'.join([s for s in sqls if s])
        logger.debug(sql)
        self.connection.executescript(sql)
        self.commit()

    def begin(self):
        logger.debug('TX BEGIN')
        return self.cursor.execute('BEGIN')

    def commit(self):
        logger.debug('TX COMMIT')
        self.connection.commit()

    def rollback(self):
        self.connection.rollback()

    def execute(self, sql, values=None):
        if logger.isEnabledFor(logging.DEBUG):  # Speedup for hot code path
            logger.debug('{sql} = {values}'.format(sql=sql, values=values))
        return self.cursor.execute(sql, values)

    def close(self):
        logger.debug('DB CLOSE')
        self.cursor.close()
        self.connection.close()

    @staticmethod
    def _create_table_sql(table_name, columns):
        lines = ['CREATE TABLE %s (' % table_name]

        # Declare columns
        cols = ('  {name} {type}{pk}{unique}{null}'.format(
                    name=c.name,
                    type=c.type,
                    pk=(' PRIMARY KEY' if c.pk else ''),
                    unique=(' UNIQUE' if c.unique and not c.pk else ''),
                    null=(' NOT NULL' if c.pk or not c.null else ''),
                ) for c in columns)
        lines.append(',\n'.join(cols))
        lines.append(');')

        return '\n'.join(lines) + '\n'

    @staticmethod
    def _create_index_sql(table_name, columns):
        lines = ['CREATE INDEX ix_{table}_{col} ON {table} ({col});'
                 .format(table=table_name, col=c.name)
                 for c in columns
                 if c.index and not c.pk and not c.unique]
        return '\n'.join(lines)


def ensure_downloaded(files, cache_dir):
    """
    Download the collection of +files+ into cache_dir unless they already
    exist there.
    """
    if not os.path.exists(cache_dir):
        os.mkdir(cache_dir)

    for filename in files:
        url = 'https://datasets.imdbws.com/{}'.format(filename)
        ofn = os.path.join(cache_dir, filename)

        if os.path.exists(ofn):
            return

        logger.info('GET %s -> %s', url, ofn)
        with urlopen(url) as response:
            if not response.status == 200:
                raise RuntimeError('Failed to download "{url}". HTTP response code: '
                                   '{code}'.format(url=url, code=response.status))
            with open(ofn, 'wb') as f:
                shutil.copyfileobj(response, f)


def tsv(f, null='\\N'):
    """
    Read a Tab separated file and yield a dict for each "record".
    Similar to python's csv.DictReader but faster and handles imdb nulls.
    """
    headers = [x.strip() for x in next(f).split("\t")]
    for s in f:
        values = [(x.strip() if x and x != null else None) for x in s.split("\t")]
        yield dict(zip(headers, values))


def count_lines(f):
    """Count lines in an iterable"""
    i = 0
    for _ in f:
        i += 1
    return i


def import_file(db, filename, table, column_mapping):
    """
    Import a imdb file into a given table, using a specific tsv value to column mapping
    """
    fopen = gzip.open if filename.endswith('.gz') else open

    @contextmanager
    def text_open(fn, encoding='utf-8'):
        """Yields utf-8 decoded strings, one per line, from a [gzipped] text file"""
        try:
            # Fast python3 text decoding
            with fopen(fn, 'rt', encoding=encoding) as tf:
                yield tf
        except TypeError:
            # Fallback to slower python2 compatible variant
            with fopen(filename, 'rb') as bf:
                yield (b.decode('utf-8') for b in bf)

    logger.info('Importing file: {}'.format(filename))

    headers = column_mapping.keys()
    columns = [c.name for c in column_mapping.values()]
    placeholders = ['?' for _ in columns]
    sql = 'INSERT INTO {table} ({columns}) VALUES({values})'.format(
        table=table,
        columns=', '.join(columns),
        values=','.join(placeholders)
    )

    logger.info('Reading number of rows ...')
    with fopen(filename, 'rb') as f:
        total_rows = count_lines(f) - 1  # first line is header

    logger.info('Inserting rows into table: {}'.format(table))
    db.begin()
    try:
        with text_open(filename) as tf:
            for row in tqdm(tsv(tf), total=total_rows, unit=' rows'):
                values = [row[h] for h in headers if h in row]
                db.execute(sql, list(values))
        db.commit()
    except Exception:
        db.rollback()
        raise


def main():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description='Imports imdb tsv interface files into a new sqlite'
                    'database. Fetches them from imdb if not present on'
                    'the machine.'
    )
    parser.add_argument('--db', metavar='FILE', default='imdb.db',
                        help='Connection URI for the database to import into.')
    parser.add_argument('--cache-dir', metavar='DIR', default='downloads',
                        help='Download cache dir where the tsv files from imdb will be stored before the import.')
    parser.add_argument('--verbose', action='store_true',
                        help='Show database interaction')
    opts = parser.parse_args()

    logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)
    if opts.verbose:
        logger.setLevel(logging.DEBUG)

    if os.path.exists(opts.db):
        logger.warning('DB already exists: ({db}). Refusing to modify. Exiting'.format(db=opts.db))
        return 1

    ensure_downloaded(TSV_TABLE_MAP.keys(), opts.cache_dir)
    logger.info('Populating database: {}'.format(opts.db))
    db = Database(uri=opts.db)

    for filename, table_mapping in TSV_TABLE_MAP.items():
        table, column_mapping = table_mapping
        import_file(db, os.path.join(opts.cache_dir, filename),
                    table, column_mapping)

    logger.info('Creating table indices ...')
    db.create_indices()

    db.close()
    logger.info('Import successful')
    return 0


if __name__ == '__main__':
    sys.exit(main())
