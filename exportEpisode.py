import json,sys,requests,re,os,xml,logging
from requests.auth import HTTPDigestAuth
from xml.etree import ElementTree
from xml.dom import minidom
import config

# Enabling debugging at http.client level (requests->urllib3->http.client)
# you will see the REQUEST, including HEADERS and DATA, and RESPONSE with HEADERS but without DATA.
# the only thing missing will be the response.body which is not logged.
# try: # for Python 3
#     from http.client import HTTPConnection
# except ImportError:
#     from httplib import HTTPConnection
# HTTPConnection.debuglevel = 1

# logging.basicConfig() # you need to initialize logging, otherwise you will not see anything from requests
# logging.getLogger().setLevel(logging.DEBUG)
# requests_log = logging.getLogger("urllib3")
# requests_log.setLevel(logging.DEBUG)
# requests_log.propagate = True

searchrequest = config.engageserver + config.searchendpoint + sys.argv[1]

archiverequest = config.archiveserver + config.archiveendpoint + sys.argv[1]

sourceauth = HTTPDigestAuth(config.sourceuser, config.sourcepassword)
targetauth = HTTPDigestAuth(config.targetuser, config.targetpassword)

# Get mediapackage from search service
searchresult = requests.get(searchrequest, auth=sourceauth, headers=config.sourceheader)
#print(searchresult.request.body)
mediapackagesearch = searchresult.json()['search-results']['result']['mediapackage']

trackfromarchive=[]
attachmentsfromarchive=[]
mediapackagearchive= dict()
archivePresentationTracks=False

#Opencast sends an Object if list cotains only one Item instead of list
def jsonMakeObjectToList(jsonobject):
    if (not isinstance(jsonobject, list)):
        tmpObject = jsonobject
        jsonobject = []
        jsonobject.append(tmpObject)
        return jsonobject
    else:
     return jsonobject


# Get mediapackage from episode/archive service
# archiveresult = requests.get(archiverequest, auth=sourceauth, headers=config.sourceheader)
# print("Archive result: " + archiveresult)
# if (archiveresult.json()['search-results'].get('result')):
#     mediapackagearchive = archiveresult.json()['search-results']['result']['mediapackage']
#     # get Tracks
#     trackfromarchive = jsonMakeObjectToList(mediapackagearchive['media']['track'])
#     attachmentsfromarchive = jsonMakeObjectToList(mediapackagearchive['attachments']['attachment'])
# else:
#     archivePresentationTracks=True
#     print ("Hint: This Episode was not Archived + Archive for Presentation Tracks")



# get all tracks from search
track = mediapackagesearch['media']['track']

# make sure that tracks are lists not only objects
if (isinstance(track, list)) :
    trackfrommediapackage = track
else:
    trackfrommediapackage = []
    trackfrommediapackage.append(track)




# get attachment lists from both services
attachments = mediapackagesearch['attachments']['attachment']
attachmentsfrommediapackage = []
# make sure that tracks are lists not only objects
if (isinstance(attachments, list)) :
    attachmentsfrommediapackage = attachments
else:
    attachmentsfrommediapackage.append(attachments)


# replace old attachments list
mediapackagesearch['attachments']['attachment'] = attachmentsfromarchive + attachmentsfrommediapackage

# merge both track lists
tracknew = trackfrommediapackage

# remove all streaming server entries
trackwithoutrtmp = []
for t in tracknew:
    url = str(t.get('url'))
    if not re.match("^rtmp", url):
        trackwithoutrtmp.append(t)

# add new tracklist to mediapackage again
mediapackagesearch['media']['track'] = trackwithoutrtmp


finalmediapackage = {}
finalmediapackage['mediapackage'] = mediapackagesearch

# write to json file with current ID
#with open(sys.argv[1]+'.json', 'w') as f:
#  json.dump(finalmediapackage, f, ensure_ascii=False)

#################### start ingesting


# empty mediapackage with the right ID
#ingest_mp = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><mediapackage xmlns="http://mediapackage.opencastproject.org" id="' + sys.argv[1]  + '" start="2016-08-01T12:44:03Z"><media/><metadata/><attachments/><publications/></mediapackage>'

#TODO? -> Check if mediapackage already exists on the target server

# create mediapackage with right id
try:
    ingest_track_resp = requests.put(config.targetserver + "/ingest/createMediaPackageWithID/"+sys.argv[1], headers=config.targetheader, auth=targetauth)
    ingest_track_resp.raise_for_status()
    ingest_mp = ingest_track_resp.text
    #print(ingest_track_resp.request.headers)
    #print("Creating the MP via the API")
    #print(ingest_mp)
except requests.exceptions.RequestException as e:  # This is the correct syntax
    raise SystemExit(e)
except requests.exceptions.HTTPError as err:
    raise SystemExit(err)


# parse Tags to String list seperated by ,
def parseTagsToString(tags):
     #fix json bug, on element=not list element
     if  type(tags) is list :
            #tags=t.get("tags")
            tags=','.join(tags)
            return tags
     else:
            #tags= t.get("tags").get("tag")
            return tags


#create correct json object
mediapackagesearch['metadata']['catalog'] = jsonMakeObjectToList(mediapackagesearch['metadata']['catalog'])

# download catalogs with curl and upload them to the target opencast (no checking for errors yet)
for c in mediapackagesearch['metadata']['catalog']:
    if (c.get('type') and c.get('url')):
        filename = str(c.get('url')).split("/")[-1]
        command = "curl -s -L --digest -u " + config.sourceuser +":" + config.sourcepassword + " -H 'X-Requested-Auth: Digest' " + c.get('url') + " -o " + filename
        #print("Curl command: " + command)
        os.system(command)
        files = {'file': open(filename, 'rb')}
        tags = parseTagsToString(c.get("tags").get("tag"))
        payload = {'flavor': c.get("type"), 'mediaPackage': ingest_mp, 'tags' : tags }
        ingest_track_resp = requests.post(config.targetserver + "/ingest/addCatalog", headers=config.targetheader, files=files, auth=targetauth, data=payload)
        ingest_mp = ingest_track_resp.text
        os.remove(filename)

# create correct json object
mediapackagesearch['attachments']['attachment']=jsonMakeObjectToList(mediapackagesearch['attachments']['attachment'])
# download attachments with curl and upload them to the target opencast (no checking for errors yet)
for a in mediapackagesearch['attachments']['attachment']:
    if (c.get('type') and c.get('url')):
        filename = str(a.get('url')).split("/")[-1]
        command = "curl -s -L --digest -u " + config.sourceuser +":" + config.sourcepassword + " -H 'X-Requested-Auth: Digest' " + a.get('url') + " -o " + filename
        #print("Curl command: " + command)
        os.system(command)
        files = {'file': open(filename, 'rb')}
        tags = parseTagsToString(a.get("tags").get("tag"))
        payload = {'flavor': a.get("type"), 'mediaPackage': ingest_mp, 'tags' : tags }
        ingest_track_resp = requests.post(config.targetserver + "/ingest/addAttachment", headers=config.targetheader, files=files, auth=targetauth, data=payload)
        ingest_mp = ingest_track_resp.text
        os.remove(filename)


# create correct json object
#mediapackagesearch['media']['track']=jsonMakeObjectToList(mediapackagesearch['media']['track'])
# download tracks with curl and upload them to the target opencast (no checking for errors yet)
for t in mediapackagesearch['media']['track']:
    if ((c.get('type') and c.get('url')) and not c.get('mimetype') == 'audio/mp3'):
        filename = str(t.get('url')).split("/")[-1]
        command = "curl -s -L --digest -u " + config.sourceuser +":" + config.sourcepassword + " -H 'X-Requested-Auth: Digest' " + t.get('url') + " -o " + filename
#        print("Curl command: " + command)
        os.system(command)
        files = {'file': open(filename, 'rb')}
        tags = parseTagsToString(t.get("tags").get("tag"))
        if (archivePresentationTracks):
            tags += ','+ 'archive'
        payload = {'flavor': t.get("type"), 'mediaPackage': ingest_mp, 'tags' : tags }
        ingest_track_resp = requests.post(config.targetserver + "/ingest/addTrack", headers=config.targetheader, files=files, auth=targetauth, data=payload)
        ingest_mp = ingest_track_resp.text
        os.remove(filename)



def prettify(elem):
    """Return a pretty-printed XML string for the Element.
    """
    rough_string = ElementTree.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")

#print(prettify(ElementTree.fromstring(ingest_mp)))

def ingestMediapackage(mediapackage):
    mediapackage=prettify(ElementTree.fromstring(ingest_mp))
    f = open('mediapackage.xml', 'w')
    f.write(mediapackage)
    f.close()
    payload = {'mediaPackage': mediapackage}
    ingest_track_resp = requests.post(config.targetserver + "/ingest/ingest/"+config.targetworkflow, headers=config.targetheader, auth=targetauth, data=payload)
    print ("Ingesting " + sys.argv[1] + " done")

ingestMediapackage(ingest_mp)
