# imdb-sqlite
Imports IMDB TSV files into a SQLite database.

It will fetch the [files][1] from IMDB unless you've already fetched them earlier.

The program relies on the following IMDB tab separated files:

* `title.basics.tsv.gz`: Video titles such as movies, documentaries, tv series, episodes etc.
* `name.basics.tsv.gz`: People in the entertainment business.
* `title.akas.tsv.gz`: Alternative names for titles, for different languages.
* `title.principals.tsv.gz`: Mapping of who participated in which title (movie / show).
* `title.episode.tsv.gz`: season and episode numbers, for episodes of shows.
* `title.ratings.tsv.gz`: Current rating and vote count for the titles.

## Installation

    pip install imdb-sqlite

## Usage

    usage: imdb-sqlite [-h] [--db DB] [--cache-dir CACHE_DIR] [--verbose]
    
    Imports imdb tsv interface files into a new sqlitedatabase. Fetches them from
    imdb if not present onthe machine.
    
    optional arguments:
      -h, --help       show this help message and exit
      --db FILE        Connection URI for the database to import into. (default:
                       imdb.db)
      --cache-dir DIR  Download cache dir where the tsv files from imdb will be
                       stored before the import. (default: downloads)
      --verbose        Show database interaction (default: False)

Just run the program with no arguments, and you'll get a file named `imdb.db` in the current working directory.

_Note_: the import may take a long time, since there are millions of records to import. 

_Hints_:
* Make sure the disk the database is written to has sufficient space. About 5 GiB is needed.
* Use a SSD to speed up the import.

[1]: https://www.imdb.com/interfaces/