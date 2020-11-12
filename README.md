# Icecast Stream Checker
Python script to check a number of web streams and verify that the stream exists and has audio. 
Originally written for the legacy stream system at Celador Radio (now part of Bauer Media Group).

## Requirements
* Python
* FFmpeg

## Installation

### Pre-Requisites
The following Python dependencies are required
* email
* ffmpeg-python
* numpy

FFmpeg will need to be installed via your package manager.

### Script Installation
1. Copy python script to directory (e.g. /usr/local/bin/)
2. Install dependencies `sudo pip install requests python-ffmpeg email numpy`
3. Edit python script, update streams list, email settings.
4. Go

### Cronjobs
For the script to run every hour on half past the hour:
``*/30 * * * * /usr/bin/python /usr/local/bin/streamchecker/streamchecker.py >/dev/null 2>&1``

For the script to run at 8:05 every weekday and force an email to be sent:
``5 8 * * 1-5 /usr/bin/python /usr/local/bin/streamchecker/streamchecker.py -f >/dev/null 2>&1``
