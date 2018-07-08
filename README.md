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
    
    Imports imdb tsv interface files into a new sqlitedatabase. Fetches them from
    imdb if not present onthe machine.
    
    optional arguments:
      -h, --help       show this help message and exit
      --db FILE        Connection URI for the database to import into. (default:
                       imdb.db)
      --cache-dir DIR  Download cache dir where the tsv files from imdb will be
                       stored before the import. (default: downloads)
      --verbose        Show database interaction (default: False)

Just run the program with no arguments, and you'll get a file named `imdb.db`
in the current working directory.

## Example

    $ imdb-sqlite
    
    2018-07-08 16:00:00,000 Populating database: imdb.db
    2018-07-08 16:00:00,001 Applying schema
    
    2018-07-08 16:00:00,005 Importing file: downloads\name.basics.tsv.gz
    2018-07-08 16:00:00,005 Reading number of rows ...
    2018-07-08 16:00:11,521 Inserting rows into table: people
    100%|█████████████████████████| 8699964/8699964 [01:23<00:00, 104387.75 rows/s]
    
    2018-07-08 16:01:34,868 Importing file: downloads\title.basics.tsv.gz
    2018-07-08 16:01:34,868 Reading number of rows ...
    2018-07-08 16:01:41,873 Inserting rows into table: titles
    100%|██████████████████████████| 5110779/5110779 [00:58<00:00, 87686.98 rows/s]
    
    2018-07-08 16:02:40,161 Importing file: downloads\title.akas.tsv.gz
    2018-07-08 16:02:40,161 Reading number of rows ...
    2018-07-08 16:02:44,743 Inserting rows into table: akas
    100%|██████████████████████████| 3625334/3625334 [00:37<00:00, 97412.94 rows/s]
    
    2018-07-08 16:03:21,964 Importing file: downloads\title.principals.tsv.gz
    2018-07-08 16:03:21,964 Reading number of rows ...
    2018-07-08 16:03:55,922 Inserting rows into table: crew
    100%|███████████████████████| 28914893/28914893 [03:45<00:00, 128037.21 rows/s]
    
    2018-07-08 16:07:41,757 Importing file: downloads\title.episode.tsv.gz
    2018-07-08 16:07:41,757 Reading number of rows ...
    2018-07-08 16:07:45,370 Inserting rows into table: episodes
    100%|█████████████████████████| 3449903/3449903 [00:21<00:00, 158265.16 rows/s]
    
    2018-07-08 16:08:07,172 Importing file: downloads\title.ratings.tsv.gz
    2018-07-08 16:08:07,172 Reading number of rows ...
    2018-07-08 16:08:08,029 Inserting rows into table: ratings
    100%|███████████████████████████| 846901/846901 [00:05<00:00, 152421.27 rows/s]
    
    2018-07-08 16:08:13,589 Creating table indices ...
    2018-07-08 16:09:16,451 Import successful


### Note
The import may take a long time, since there are millions of records to
process.

The above example used python 3.6.4 on windows 7, with the working directory
being on a SSD.  

## Hints
* Make sure the disk the database is written to has sufficient space.
  About 5 GiB is needed.
* Use a SSD to speed up the import.
* To check the best case import performance, use an in-memory database: 
  `--db :memory:`.

[1]: https://www.imdb.com/interfaces/