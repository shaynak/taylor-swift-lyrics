# Taylor Swift Lyric Scraper

This dataset includes all Taylor Swift songs and their lyrics for analysis!

You can use it to scrape Taylor Swift songs yourself (or modify it to make it work for other artists!) or use the data found in `songs.csv` and `lyrics.csv`. Happy analysis!

# Getting started

Requires python 3.12 (3.13 not working)

Setup with venv

- `cp .env.example .env`
- add your "Client Access Token" from https://genius.com/api-clients to `.env`
- `python -m venv myenv`
- `. ./myenv/bin/activate`
- `pip install -r requirements.txt`

Running the Scraper

- `python scraper.py`
