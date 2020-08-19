import sys,requests,re,os,time
from requests.auth import HTTPDigestAuth

import config

if sys.argv[1]:
    limit = sys.argv[1]

if sys.argv[2]:
    timeout = sys.argv[2]

episodes =  open("episodelist.txt", "r+")
for i in range(int(limit)):
    episode = episodes.readline()
    print "Ingesting id: "+  episode + "\n"
    command = 'python exportEpisode.py '+ episode
    print command +"\n"
    os.system(command)
    if timeout:
        time.sleep(int(timeout))