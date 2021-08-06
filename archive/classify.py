#!/usr/bin/env python

import getopt, re
import os, os.path, sys, shutil
import datetime
import gdata.youtube
import gdata.youtube.service
import kaa.metadata

def PrintVideoFeed(feed):
  for entry in feed.entry:
      PrintEntryDetails(entry)


def PrintEntryDetails(entry):
  print 'Video title: %s' % entry.media.title.text
  print 'Video published on: %s ' % entry.published.text
  print 'Video description: %s' % entry.media.description.text
  print 'Video category: %s' % entry.media.category[0].text
  print 'Video tags: %s' % entry.media.keywords.text
  print 'Video watch page: %s' % entry.media.player.url
  print 'Video flash player URL: %s' % entry.GetSwfUrl()
  print 'Video duration: %s' % entry.media.duration.seconds

  # non entry.media attributes
  #print 'Video geo location: %s' % entry.geo.location()
  #print 'Video view count: %s' % entry.statistics.view_count
  #print 'Video rating: %s' % entry.rating.average

  # show alternate formats
  for alternate_format in entry.media.content:
    if 'isDefault' not in alternate_format.extension_attributes:
      print 'Alternate format: %s | url: %s ' % (alternate_format.type,
                                                 alternate_format.url)

  # show thumbnails
  for thumbnail in entry.media.thumbnail:
    print 'Thumbnail url: %s' % thumbnail.url

def init_utube():
  yt_service = gdata.youtube.service.YouTubeService()

  # The YouTube API does not currently support HTTPS/SSL access.
  yt_service.ssl = False

  yt_service.developer_key = os.environ['YOUTUBE_KEY']
  yt_service.client_id = os.environ['YOUTUBE_CLIENT_ID']
  yt_service.email = os.environ['YOUTUBE_EMAIL']
  yt_service.password = os.environ['YOUTUBE_PASS']
  yt_service.source = 'utubeit'
  yt_service.ProgrammaticLogin()
  return yt_service

ALBUM_ROOT = os.environ['ALBUM_ROOT']
SYNC_ROOT = os.environ['SYNC_ROOT']

def get_video_original_date(video):
  info = kaa.metadata.parse(video)
  d = datetime.date.fromtimestamp(info.timestamp)
  return d.year, d.month, d.day

def is_same_video(original, existing):
  return os.path.getsize(original) == os.path.getsize(existing)

def is_bad_file(existing):
  return os.path.getsize(existing) < 1000

def get_sync_file_from(video):
  sync_path = video.lstrip(ALBUM_ROOT)
  sync_path = ".".join(sync_path.split('.')[:-1])
  sync_file = os.path.join(SYNC_ROOT, sync_path)
  return sync_file

def is_already_uploaded(video):
  sync_file = get_sync_file_from(video)
  return os.path.exists(sync_file)

def update_sync_file(video):
  sync_file = get_sync_file_from(video)
  sync_path = os.path.split(sync_file)[0]
  if not os.path.exists(sync_path):
    os.makedirs(sync_path)
  if not os.path.exists(sync_file):
    create_sync_file(sync_file)

def create_sync_file(sync_file):
  try:
    sf = open(sync_file, 'w')
    sf.write("")
    sf.close()
  except Exception, e:
    print "Failed to create sync file %s" % sync_file

def get_another_filename(fname):
  i = 1
  while i < 10:
    parts = fname.split('.')
    new_fname = ".".join(parts[:-1]) + "-" + str(i) + "." + parts[-1]
    if not os.path.exists(new_fname):
      return new_fname
    else:
      i += 1
  raise Exception("Cannot create an unique name for %s" % fname) 

def get_classified_file(video):
  year, month, day = get_video_original_date(video)
  classified_file_path = os.path.join(ALBUM_ROOT, str(year), str(month), str(day))
  classified_file = os.path.join(classified_file_path, os.path.basename(video))

  if os.path.exists(classified_file_path):
    if os.path.exists(classified_file):
      if not is_same_video(video, classified_file):
        if not is_bad_file(classified_file):
          classified_file = get_another_filename(classified_file)
        else:
          # override bad file
          pass
      else:
        # don't override same file
        print "Skip duplicate video %s" % video
        return None
  else:
    os.makedirs(classified_file_path)    
  return classified_file

def classify_video(video, classified_file, delete_original):
  if delete_original:
    print "Move %s to %s" % (video, classified_file)
    shutil.move(video, classified_file)
  else:
    print "Copy %s to %s" % (video, classified_file)
    shutil.copy2(video, classified_file)
  return classified_file
  
def upload_video(utube, video):
  date_taken = "%s-%s-%s" % get_video_original_date(video)
  vpath, vfile = os.path.split(video)
  vsize = os.path.getsize(video)
  # prepare a media group object to hold our video's meta-data
  my_media_group = gdata.media.Group(
    title=gdata.media.Title(text='vfile'),
    description=gdata.media.Description(description_type='plain',
                                      text='Video shot on %s' % date_taken),
    keywords=gdata.media.Keywords(text='suns'),
    category=[gdata.media.Category(
      text='People',
      scheme='http://gdata.youtube.com/schemas/2007/categories.cat',
      label='People &amp; Blogs')],
    player=None,
    private=gdata.media.Private()
  )

  # prepare a geo.where object to hold the geographical location
  # of where the video was recorded
  where = gdata.geo.Where()
  where.set_location((32.0, 117.0))

  # create the gdata.youtube.YouTubeVideoEntry to be uploaded
  video_entry = gdata.youtube.YouTubeVideoEntry(media=my_media_group,
                                              geo=where)

  developer_tags = [date_taken, vfile]
  video_entry.AddDeveloperTags(developer_tags)

  # set the path for the video file binary
  video_file_location = video

  new_entry = utube.InsertVideoEntry(video_entry, video_file_location)
  print "Uploaded video: ", new_entry

def walk_it(args, work_dir, video_files):
  
  utube, classify, upload, tag, delete_original = args
  print "Start to process %d videos in %s" % (len(video_files), work_dir)

  for video_file in video_files:
    video = os.path.join(work_dir, video_file)
    if not os.path.isfile(video):
      continue

    if video.upper().endswith(".AVI")\
        or video.upper().endswith(".MMPG") \
        or video.upper().endswith(".MMODD"):
      try:
        if classify:
          classified_file = get_classified_file(video)
          if classified_file:
            classify_video(video, classified_file, delete_original)
        else:
          classified_file = video
        if classified_file:
          if upload:
            if not classified_file.upper().endswith(".AVI"):
              print "Skip %s as utube does not support this format." % classified_file
            else:
              if is_already_uploaded(classified_file):
                print "%s is already uploaded" % classified_file
              else:
                print "Start uploading %s" % classified_file
                upload_video(utube, classified_file)
                update_sync_file(classified_file)
      except NotImplementedError, e:
        print "Failed to process video %s due to %s." % (video, str(e))
        raise e
    else:
      print "Skip non-video file %s" % video

def sync_utube(utube):
  uri = 'http://gdata.youtube.com/feeds/api/users/sunh11373/uploads'
  feed = utube.GetYouTubeVideoFeed(uri)
  for entry in feed.entry:
    dev_tags = entry.GetDeveloperTags()
    if dev_tags:
      date_taken, vfile = dev_tags
    else:
      print "Skip this video. ", entry
      continue

    sync_path = os.path.join(SYNC_ROOT, *date_taken.split("-"))
    if not os.path.exists(sync_path):
      os.makedirs(sync_path)
    sync_file = os.path.join(sync_path, vfile)
    if not os.path.exists(sync_file):
      create_sync_file(sync_file)
    else:
      pass
      
if __name__ == '__main__':

  upload = False
  sync = False
  classify = False
  remove_original = False
  tag = None
  work_dir = "/home/sunh11373/Pictures/staging"

  try:
    options, remainder = getopt.gnu_getopt(sys.argv[1:], 'd:t:curs',
                                               ['sourcedir=',
                                                'tag=',
                                                'classify',
                                                'upload',
                                                'removeoriginal',
                                                'sync'
                                                ])
    for opt, arg in options :       
      if opt in ('-d', '--sourcedir'):
        work_dir = arg
      elif opt in ('-t', '--tag'):
        tag = arg
      elif opt in ('-r', '--removeoriginal'):
        remove_original = True
      elif opt in ('-c', '--classify'):
        classify = True
      elif opt in ('-u', '--upload'):
        upload = True
      elif opt in ('-s', '--sync'):
        sync = True

  except getopt.GetoptError, e:
    print e
    sys.exit(2)

  if sync:
    sync_utube(init_utube())
  else:
    if (not classify) and (not upload) and (not sync):
      print "No operation specified"
      sys.exit(2)
    if (not classify) and (not work_dir.startswith(ALBUM_ROOT)):
      print "Upload only must start in album" 
      sys.exit(2)

    args = (init_utube(), classify, upload, tag, remove_original)
    os.path.walk(work_dir, walk_it, args)
