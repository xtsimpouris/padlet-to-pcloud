# Padlet to pCLoud
Auto download padlet posts and save them in a pCloud folder

## How did you come up with the idea?
Our kid goes to the kinder garden, and the teacher provides weekly updates to all parents through [padlet](https://padlet.com). Our main backup system is [pCloud](https://www.pcloud.com/eu). In order to copy locally all posts, a manual process was taken place. With this approach, process is automatic.

## How do I install?
1. Clone the repo
2. Create a new env (`python3 -m venv env`)
3. Get into the environment (`. env/bin/activate`)
4. Install all packages (`pip install -r ./requirements.txt`)

## How do I execute?
1. Get into the environment (`. env/bin/activate`)
2. Execute main file (`python main.py`)

## Ho do I get out of the environment
1. Execute accordingly (`deactivate`)

## How do I provide settings?
First execute will provide a small "wizard" where all missing information must be provided. All information are saved at file `settings.yaml`. In case some of the settings are wrong, you can delete the file and start over.

## Wizard requests for a padlet URL, which one?
The address of the padlet you open in the browser, e.g. `https://padlet.com/<user>/<padlet-name>`. The "wall id" the API needs is looked up from that page automatically on every run, and stored as `padlet.wallid` in `settings.yaml`.

## Can I provide the "wall id" directly instead?
Yes, remove `url` and set `wallid` under `padlet` in `settings.yaml`. To find it:
- Quickest way: `curl -sL <padlet url> | grep -oE 'wall_hashid=board_[A-Za-z0-9]+'`
- Or manually:
  1. Login to padlet
  2. Open developer tools and select "Network" tab
  3. Search for `https://padlet.com/api/10/wishes`
  4. In case no row is found, hit Refresh (F5)
  5. URL param `wall_hashid` is what we need

## I don't feel confortable with locally stored settings, is there a chance this file may be committed?
No, `settings.yaml` is always ignored
## Where is the full post text?
Filenames only carry the date, the post id and the (short) post headline. The full post text is embedded in the image as XMP metadata (`dc:title` = headline, `dc:description` = post text), without re-encoding the image. Supported for JPEG, PNG and WebP.
