NAME = "DIY"
BASE_URL = "http://www.diynetwork.com"
ART = 'art-default.jpg'
ICON = 'icon-default.png'


# Full Episode URLs
SHOW_LINKS_URL = "http://www.diynetwork.com/full-episodes/package/index.html"

# modified links to work with DIY feeds
# NB: this is a "made up" URL, they don't have direct play URLs
# for videos (actually they do have direct play URLs but almost never use them)
# and even their listing pages are all over the map
# therefore the URL service is local (within the plugin) as opposed
# to putting it globally within the services.bundle for use with PlexIt and the like
VIDEO_URL = "http://www.diynetwork.com/video/?videoId=%s&showId=%s&season=%s&idx=%s"
VPLAYER_MATCHES = Regex("SNI.DIY.Player.FullSize\('vplayer-1','([^']*)'")
RE_AMPERSAND = Regex('&(?!amp;)')

####################################################################################################
def Start():

	# Setup the artwork and name associated with the plugin
	ObjectContainer.title1 = NAME
	HTTP.CacheTime = CACHE_1HOUR  
	ObjectContainer.art = R(ART)
	DirectoryItem.thumb = R(ICON)

####################################################################################################
@handler('/video/diy', NAME)
def MainMenu():

	oc = ObjectContainer()
	
	Log.Debug("*** Begin Processing!  Good luck!")
	
	for s in HTML.ElementFromURL(SHOW_LINKS_URL).xpath("//div[@id='full-episodes']/div/ul/li/a[@href[starts-with(.,'/diy')]]"):
		
		Log.Debug("***series*** Inside the loop.")
		
		title = s.text
		
		Log.Debug("***series*** Found {t}.".format(t=title))

		url = s.xpath("./@href")[0]
		thumb_url = s.xpath("./../div/a[@class='banner']/img/@src")[0]
		
		oc.add(
			DirectoryObject(
				key = Callback(GetSeasons, path=BASE_URL + url, title=title, thumb_url=thumb_url),
				title = title,
				thumb = Resource.ContentsOfURLWithFallback(url=thumb_url)
			)
		)
		Log.Debug("***series*** Added {t} to the DirectoryObject.".format(t=title))

	# sort our shows into alphabetical order here
	oc.objects.sort(key = lambda obj: obj.title)

	return oc

####################################################################################################
@route('/video/diy/seasons')
def GetSeasons(path, title, thumb_url):

	import re
	oc = ObjectContainer(title2=title)
	html = HTTP.Request(path).content
	matches = VPLAYER_MATCHES.search(html)
	seasonindex = 0
	seasontext = "1"

	# grab the current season link and title only on this pass, grab each season's actual shows in GetShows()
	try:
		show_id = matches.group(1)
		xml = HTTP.Request('http://www.diynetwork.com/diy/channel/xml/0,,%s,00.xml' % show_id).content.strip()
		xml = RE_AMPERSAND.sub('&amp;', xml)
		title = XML.ElementFromString(xml).xpath("//title/text()")[0].strip()
		
		title = title.replace("- ","")
		title = title.replace(",","")
		# Make sure season is a number some are listed as Season One, Season Two
		title = title.replace("Season One","Season 1")
		title = title.replace("Season Two","Season 2")

		seasonnum = title
		p = seasonnum.find("Season")
		if p > -1:
			seasontext = seasonnum.split("Season")[1].strip()
			# Eliminate anything after the season number
			k = seasontext.find(" ")
			if k > -1:
				seasontext = seasontext.split(" ")[0].strip()
			# Make sure season is a number some are listed as Season One, Season Two
			if seasontext.isdigit() is False:
				seasontext = seasonindex
		else:
			seasontext = seasonindex
		# if blog cabin, seasons are by year
		if title.find("Blog Cabin") > -1:
			seasontext = re.sub("\D","",title)

		Log.Debug("***SeasonText:%s"%seasontext)
		oc.add(
			DirectoryObject(
				key = Callback(GetShows, path=path, title=title, season=seasontext),
				title = title,
				thumb = Resource.ContentsOfURLWithFallback(url=thumb_url)
			)
		)
		Log.Debug("***season*** Added {t} to the DirectoryObject.".format(t=title))
	except:
		pass

	# now try to grab any additional seasons/listings via xpath
	# old broken url = season.xpath("./div/div[@class='crsl-wrap']/ul/li[1]/a/@href")[0]
	seasonindex = 0
	seasontext = "1"
	
	data = HTML.ElementFromURL(path)
	for season in data.xpath("//ul[@class='channel-list']/li"):
		try:
			title = season.xpath(".//h4/text()")[0].strip()
			title = title.replace("- ","")
			title = title.replace(",","")
			# Make sure season is a number some are listed as Season One, Season Two
			title = title.replace("Season One","Season 1")
			title = title.replace("Season Two","Season 2")
			seasonnum = title
			p = seasonnum.find("Season ")
			if p > -1:
				seasontext = seasonnum.split("Season ")[1].strip()
				# Eliminate anything after the season number
				k = seasontext.find(" ")
				if k > -1:
					seasontext = seasontext.split(" ")[0].strip()
				if seasontext.isdigit() is False:
					seasontext = seasonindex
			else:
				seasontext = seasonindex
			if title.find("Blog Cabin") > -1:
				seasontext = re.sub("\D","",title)
			url = season.xpath(".//div[@class='image']/a/@href")[0]
			oc.add(
				DirectoryObject(
					key = Callback(GetShows, path= BASE_URL + url, title=title, season=seasontext),
					title = title,
					thumb = Resource.ContentsOfURLWithFallback(url=thumb_url)
				)
			)
			Log.Debug("***addtnlSeason*** Added {t} to the DirectoryObject.".format(t=title))
			
		except:
			pass

	if len(oc) < 1:
		oc = ObjectContainer(header="Sorry", message="This section does not contain any videos")

	oc.objects.sort(key = lambda obj: obj.title)
			
	return oc

####################################################################################################
@route('/video/diy/shows')
def GetShows(path, title, season = "0"):

	oc = ObjectContainer(title2=title)
	html = HTTP.Request(path).content
	matches = VPLAYER_MATCHES.search(html)

	show_id = matches.group(1)
	xml = HTTP.Request('http://www.diynetwork.com/diy/channel/xml/0,,%s,00.xml' % show_id).content.strip()
	xml = RE_AMPERSAND.sub('&amp;', xml)
	index = 0
		
	for c in XML.ElementFromString(xml).xpath("//video"):
		try:
			title = c.xpath("./clipName")[0].text.strip()
			duration = Datetime.MillisecondsFromString(c.xpath("./length")[0].text)
			desc = c.xpath("./abstract")[0].text
			video_id = c.xpath("./videoId")[0].text
			thumb_url = c.xpath("./thumbnailUrl")[0].text.replace('_92x69.jpg', '_480x360.jpg')
			index = index + 1
			url = VIDEO_URL % (video_id, show_id, season, index)
						
			oc.add(
				EpisodeObject(
					url = url,
					title = title,
					duration = duration,
					summary = desc,
					season = int(season),
					index = int(index),
					thumb = Resource.ContentsOfURLWithFallback(url=thumb_url)
				)
			)
			Log.Debug("***episode*** Added {t} to the EpisodeObject.".format(t=title))
		except:
			pass

	if len(oc) < 1:
		oc = ObjectContainer(header="Sorry", message="This section does not contain any videos")

	return oc
