import sys,requests,re,os
from requests.auth import HTTPDigestAuth

import config

#Digest login source server
sourceauth = HTTPDigestAuth(config.sourceuser, config.sourcepassword)

#Source Engage Server data
searchrequest = config.engageserver + '/search/episode.json?limit=20'

print(searchrequest)

#Opencast sends an Object if list cotains only one Item instead of list
def jsonMakeObjectToList(jsonobject):
    if (not isinstance(jsonobject, list)):
        tmpObject = jsonobject
        jsonobject = []
        jsonobject.append(tmpObject)
        return jsonobject
    else:
     return jsonobject

# Get mediapackage from search service
searchresult = requests.get(searchrequest, auth=sourceauth, headers=config.sourceheader)

mediapackagesearch = searchresult.json()['search-results']['result']
total = searchresult.json()['search-results']['total']
print(total)
i=0
mediapackagesearch=jsonMakeObjectToList(mediapackagesearch)


#proint each Episode id to file
f = open('episodelist.txt', 'w')
while i <= int(total):
    searchrequest = config.engageserver + '/search/episode.json?limit=20&offset=' + str(i)
    searchresult = requests.get(searchrequest, auth=sourceauth, headers=config.sourceheader)
    mediapackagesearch = searchresult.json()['search-results']['result']

    for mediapackage in mediapackagesearch:
        f.write(mediapackage['id'] + '\n')

    i += 20

f.close()
