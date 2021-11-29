import hashlib
import os
import sys
import urllib

import cv2
import numpy as np
import paramiko
import requests


# resize images to 224x224
def resize_image(image):
    image = cv2.resize(image, (224, 224))
    return image


# todo upload processed image then store on ftp based on category


# subreddit list
# read from github raw
# https://github.com/alex000kim/nsfw_data_scraper/raw/master/scripts/source_urls/hentai.txt
def fetchRaw(url):
    return requests.get(url).text.split("\n")


nsfwSubs = []
sfwSubs = []
nsfwSubs.extend(fetchRaw("https://github.com/alex000kim/nsfw_data_scraper/raw/master/scripts/source_urls/hentai.txt"))
nsfwSubs.extend(fetchRaw("https://github.com/alex000kim/nsfw_data_scraper/blob/master/scripts/source_urls/porn.txt"))
nsfwSubs.extend(fetchRaw("https://github.com/alex000kim/nsfw_data_scraper/blob/master/scripts/source_urls/sexy.txt"))
nsfwSubs.extend(open("gore.txt").readlines())
sfwSubs.extend(fetchRaw("https://github.com/alex000kim/nsfw_data_scraper/blob/master/scripts/source_urls/neutral.txt"))
sfwSubs.extend(fetchRaw("https://github.com/alex000kim/nsfw_data_scraper/blob/master/scripts/source_urls/drawing.txt"))


# scrap reddit


def scrapJsonSubreddit(subreddit, after=None):
    user_agent = 'Reddit JSON API teaching example/1.0'
    num_posts = 100
    params = {'limit': num_posts}
    if after is not None: params['after'] = after
    headers = {'User-Agent': user_agent}
    response = requests.get('https://www.reddit.com/r/' + subreddit + '/new.json', headers=headers, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        return None


# sftp, get config from arg
host, port = sys.argv[1].split(":")
username, password = sys.argv[2], sys.argv[3]
transport = paramiko.Transport((host, port))
transport.connect(None, username, password)
# Go!
sftp = paramiko.SFTPClient.from_transport(transport)

defaultDir = "~/dataset"


def processImage(url, nsfw=False):
    req = urllib.urlopen(url)
    arr = np.asarray(bytearray(req.read()), dtype=np.uint8)
    img = cv2.imdecode(arr, -1)  # 'Load it as it is'
    img = resize_image(img)
    # memory file
    memFile = cv2.imencode('.jpg', img)[1]
    # hash
    hashString = hashlib.sha256(memFile.tostring()).hexdigest()
    # upload
    dirs = defaultDir + "/" + ("nsfw" if nsfw else "sfw")
    sftp.putfo(memFile, dirs + "/" + hashString + ".jpg")


def processPost(post, nsfw=False):
    if post['data']['over_18'] and not nsfw:
        return
    if post['data']['url'].endswith(".jpg") or post['data']['url'].endswith(".png"):
        try:
            processImage(post['data']['url'], nsfw)
        except Exception as e:
            print("Error processing image: " + post['data']['url'])
            print(e)


def processSubreddit(subreddit, nsfw=False):
    after = None
    while True:
        data = scrapJsonSubreddit(subreddit, after)
        if data is None:
            break
        for post in data['data']['children']:
            processPost(post, nsfw)
        if data['data']['after'] is None:
            break
        after = data['data']['after']


for s in nsfwSubs:
    processSubreddit(s, True)

for s in sfwSubs:
    processSubreddit(s, False)
