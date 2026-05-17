# Updated to support Serializd and Backloggd!
I hacked on the original letterboxd poster and added backloggd and serializd to it. use the branch add-serializd+backloggd
Now you can review pretty much all media and it posts to your followers on bluesky with pretty embed links
Use [The modiified branch of the Bluesky crossposter](https://github.com/stephenrberg/bluesky-crossposter) and it sends those posts to twitter, instagram, threads and mastodon! use the branch stephenrberg-features
this branch also cuts out bluesky exclusive hashtags and will use your first hashtag as the topic on threads. It also resizes images right for instagram

# Letterboxd-BlueSky-Poster
[![Docker Hub](https://img.shields.io/static/v1.svg?color=086dd7&labelColor=555555&logoColor=ffffff&label=&message=docker%20hub&logo=Docker)](https://hub.docker.com/r/finiteui/letterboxd-bluesky-poster)

This is a simple self hosted project to tweet out your Letterboxd diary entries.

The project reads Letterboxd's RSS feed using [feedparser](https://github.com/kurtmckee/feedparser) to find new diary entries for a givern user, and posts them to Twitter using the [official atproto python package](https://github.com/MarshalX/atproto).

## Example
![image](https://github.com/user-attachments/assets/2e6b5f61-a024-4262-b3df-a32fed99a972)

## Deployment
The project can be run locally, but was designed to be run on Docker.

The image is hosted on [Docker Hub](https://hub.docker.com/r/finiteui/letterboxd-bluesky-poster) and can be deployed from there.
To deploy the project on docker:
- Create a new directory and download the included [docker-compose](docker-compose.yml) file into it.
- In the directory, create a file named .env with the contents defined below.
- In the terminal, navigate to this directory, and run ```docker compose up -d```

If the Letterboxd-Tweeter.env file variables are correct, you should be up and running.
![image](https://github.com/user-attachments/assets/a207a86b-bfef-43be-9709-217fd3a1c726)

## ENV File
This project relies on an env file named .env with configuration variables to run. An example can be found [here](.env.example).
The file needs the following:
```
LETTERBOXD_ACCOUNT = Your Letterboxd account name
BLUESKY_USERNAME = Your full BlueSky user name (no @)
BLUESKY_APP_PASSWORD = A valid BlueSky app password
```

## BlueSky App Passwords
A BlueSky app password is used to access the BlueSky API. These can be generated here: https://bsky.app/settings/app-passwords
