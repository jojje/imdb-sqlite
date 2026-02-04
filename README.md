# imdb-sqlite
Imports IMDB TSV files into a SQLite database.

It will fetch the [files][1] from IMDB unless you've already fetched them earlier.

The program relies on the following IMDB tab separated files:

* `title.basics.tsv.gz`: Video titles such as movies, documentaries, tv series, episodes etc.
* `name.basics.tsv.gz`: People in the entertainment business.
* `title.akas.tsv.gz`: Alternative names for titles, for different languages.
* `title.principals.tsv.gz`: Mapping of who participated in which title (movie / show).
* `title.episode.tsv.gz`: Season and episode numbers, for episodes of shows.
* `title.ratings.tsv.gz`: Current rating and vote count for the titles.

## Installation

    pip install imdb-sqlite

## Usage

    usage: imdb-sqlite [OPTIONS]
    
    Imports imdb tsv interface files into a new sqlite database. Fetches them from imdb
    if not present on the machine.
    
    optional arguments:
      -h, --help       show this help message and exit
      --db FILE        Connection URI for the database to import into (default: imdb.db)
      --cache-dir DIR  Download cache dir where the tsv files from imdb will be stored
                       before the import (default: downloads)
      --no-index       Do not create any indices. Massively slower joins, but cuts the DB
                       file size approximately in half
      --only TABLES    Import only some tables. The tables to import are specified using
                       a comma delimited list, such as "people,titles". Use it to save
                       storage space.
      --verbose        Show database interaction

Just run the program with no arguments, and you'll get a file named `imdb.db`
in the current working directory.

### Hints
* Make sure the disk the database is written to has sufficient space.
  About 19 GiB is needed as of early 2026. About 9.5 GB without indices.
  (for even less storage requirement, see Disk space tips below).
* Use a SSD to speed up the import.
* To check the best case import performance, use an in-memory database: 
  `--db :memory:`.

## Example

    $ imdb-sqlite

    2026-02-04 16:30:31,311 Populating database: imdb.db
    2026-02-04 16:30:31,319 Applying schema

    2026-02-04 16:30:31,323 Importing file: downloads\name.basics.tsv.gz
    2026-02-04 16:30:31,324 Reading number of rows ...
    2026-02-04 16:30:34,373 Inserting rows into table: people
    100%|██████████████████| 15063390/15063390 [01:05<00:00, 228659.33 rows/s]
    
    2026-02-04 16:31:40,262 Importing file: downloads\title.basics.tsv.gz
    2026-02-04 16:31:40,262 Reading number of rows ...
    2026-02-04 16:31:42,777 Inserting rows into table: titles
    100%|██████████████████| 12265715/12265715 [01:06<00:00, 185564.42 rows/s]

    2026-02-04 16:32:48,879 Importing file: downloads\title.akas.tsv.gz
    2026-02-04 16:32:48,880 Reading number of rows ...
    2026-02-04 16:32:54,646 Inserting rows into table: akas
    100%|██████████████████| 54957563/54957563 [04:06<00:00, 222556.12 rows/s]

    2026-02-04 16:37:01,586 Importing file: downloads\title.principals.tsv.gz
    2026-02-04 16:37:01,587 Reading number of rows ...
    2026-02-04 16:37:11,294 Inserting rows into table: crew
    100%|██████████████████| 97617046/97617046 [06:27<00:00, 251790.20 rows/s]

    2026-02-04 16:43:38,990 Importing file: downloads\title.episode.tsv.gz
    2026-02-04 16:43:38,990 Reading number of rows ...
    2026-02-04 16:43:39,635 Inserting rows into table: episodes
    100%|████████████████████| 9462887/9462887 [00:29<00:00, 315650.53 rows/s]

    2026-02-04 16:44:09,618 Importing file: downloads\title.ratings.tsv.gz
    2026-02-04 16:44:09,618 Reading number of rows ...
    2026-02-04 16:44:09,706 Inserting rows into table: ratings
    100%|████████████████████| 1631810/1631810 [00:05<00:00, 304073.42 rows/s]

    2026-02-04 16:44:15,077 Creating table indices ...
    100%|██████████████████████████████████| 12/12 [03:19<00:00, 16.64s/index]

    2026-02-04 16:47:34,781 Analyzing DB to generate statistic for query planner ...
    2026-02-04 16:48:01,367 Import successful


### Note
The import may take a long time, since there are millions of records to
process.

The above example used python 3.10.13 on windows 10, with the working directory
being on a fast Kingston NVME SSD.

## Data model

![schema](www/schema.png)

The IMDB dataset gravitates around the notion of a title. It is the primary
entity. The title ID is what you see in the URL when you visit imdb.com. It is
the defacto ID that other movie and TV sites use to uniquely reference a movie
or show. So a bit of clarification on that ID and how the tables in the dataset
reference it is in order.

A movie has a title, a TV show has one. An episode has one as well. Well two
actually; the title of the show, and the title of the episode itself. That is
why there are two links to the same `title_id` attribute in the `titles` table,
from the `episodes` table.

To make the relationships a bit clearer, following are a few query examples

**Find movies named Casablanca and their ratings**
```sql
SELECT t.title_id, t.type, t.primary_title, t.premiered, t.genres, r.rating, r.votes
FROM titles t  INNER JOIN ratings r ON ( r.title_id = t.title_id  )
WHERE t.primary_title = 'Casablanca' AND t.type = 'movie'
```

If the title type is omitted, we'd get results for tv series and other
production types named Casablanca. The current set of title types in IMDB are
the following:

```
{ movie, short, tvEpisode, tvMiniSeries, tvMovie, tvPilot,
  tvSeries, tvShort, tvSpecial, video, videoGame }
```

**Find all episodes of the TV show _Better off Ted_ and rank them by rating**
```sql
-- // table aliases: st = show-title, et = episode-title
SELECT st.primary_title, st.premiered, st.genres, e.season_number,
       e.episode_number, et.primary_title, r.rating, r.votes
FROM  titles AS st
INNER JOIN       episodes  e ON ( e.show_title_id = st.title_id )
INNER JOIN       titles   et ON ( e.episode_title_id = et.title_id )
LEFT  OUTER JOIN ratings   r ON ( et.title_id = r.title_id )
WHERE st.primary_title = 'Better Off Ted'
AND   st.type = 'tvSeries'
ORDER BY r.rating DESC
```

**Find which productions both Robert De Niro and Al Pacino acted together on**
```sql
SELECT t.title_id, t.type, t.primary_title, t.premiered, t.genres,
       c1.characters AS 'Pacino played', c2.characters AS 'Deniro played'
FROM people p1
INNER JOIN crew   c1 ON ( c1.person_id = p1.person_id )
INNER JOIN titles  t ON ( t.title_id = c1.title_id )
INNER JOIN crew   c2 ON ( c2.title_id = t.title_id )
INNER JOIN people p2 ON ( p2.person_id = c2.person_id )
WHERE p1.name = 'Al Pacino'
AND   p2.name = 'Robert De Niro'
AND   c1.category = 'actor' AND c1.category = c2.category
```

As indicated in the query, each person can participate in a production in
different roles. The crew.category designates the participation role in the
production. The current set of crew categories are:
```
{ actor, actress, archive_footage, archive_sound, cinematographer, composer,
  director, editor, producer, production_designer, self, writer }
```

### Performance tips
Prefix your query with the `EXPLAIN QUERY PLAN`. If you see `SCAN TABLE` in
there, particularly in the beginning, it means the DB is doing a brute-force
search through all the data in the column. This is _very_ slow. You want the
query plan to say `SEARCH` everywhere. If the query shows autoindex rather than
using an explicit index, then that may also be the cause for slow joins. The
tables are very large, which can result in a lot of I/O without explicit
indices. To resolve, create an index for the column indicated as being scanned
or using autoindex and rerun the query plan. Hopefully that results in a
massive query speedup.

For example `sqlite3 imdb.db "CREATE INDEX myindex ON <table-name> (<slow-column>)"`

### Disk space tips
The imported data as of 2026 produces a database file that is about 19 GiB.
About half of that space is for indices used to speed up query lookups and
joins. The default indices take up about as much as the data.

To cater for use cases where people just want to use the tool as part of some
ETL-step, for refreshing the dataset every now and then, and then simply export
the full tables (e.g. for data science using pandas/ML), a `--no-index` flag is
available. When specifying this flag, no indices will be created, which not
only saves about 50% disk space, but also speeds up the overall import process.
When this flag is provided, the DB file will be just 9.5 GiB as of date of
writing.

If you know precisely which indices you need, omitting the default indices may
also be a good idea, since you'd then not waste disk space on indices you don't
need. Simply create the indices you _do_ need manually, as illustrated in the
performance tip above.

As an indicator, following is the current space consumption spread across the tables.

Full import

* default (includes indices): 19 GB
* without indices: 9.5 GB

Sizes of the respective tables when doing selective import of only a single
table without indices.

```
* crew:     46% (4.4 GB)
* akas:     28% (2.7 GB)
* titles:   14% (1.3 GB)
* people:    8% (0.8 GB)
* episodes:  3% (0.3 GB)
* ratings:   1% (0.1 GB)
```

Percentages are the relative space consumption of the full index-free import
(~9.5 GB).

Fair to say, "who played what character", or "fetched a doughnut to what
VIP-of-wasting-space" accounts for about half the storage. If you can live
without those details then there's a massive storage saving to be made. Also, if
you don't need all the aliases for all the titles, like the portuguese title of
some bollywood flick, then the akas can also be skipped. Getting rid of those
two tables shaves off 3/4 of the required space. That's significant.

If you don't care about characters, and just want to query movies or shows, their
ratings and perhaps per-episode ratings as well, then 2 GiB of storage suffices
as you only need tables titles, episodes and ratings. However if you actually
want to query those tables as well, then you'd want to create indices, either
manually or use the default. This ups the space requirement about 50% (3GB).
I.e. just provide the command line argument `--only titles,ratings,episodes`.


## PyPI
Current status of the project is:
[![Build Status](https://github.com/jojje/imdb-sqlite/actions/workflows/python-publish.yml/badge.svg)](https://github.com/jojje/imdb-sqlite/actions/workflows/python-publish.yml)


This project uses an automated build and release process.
The module in the [pypi][2] repository is automatically built and released from
the github source, upon any version tagged commit to the master branch.

Click the status link and check out the logs if you're interested in the
package lineage; meaning how the released pypi module was constructed from
source.

[1]: https://www.imdb.com/interfaces/
[2]: https://pypi.org/project/imdb-sqlite/