""" Module for raeding the MPD file
    Author: Parikshit Juluri
    Contact : pjuluri@umkc.edu

"""
from __future__ import division
import re
import config_dash


# Try to import the C implementation of ElementTree which is faster
# In case of ImportError import the pure Python implementation
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

MEDIA_PRESENTATION_DURATION = 'mediaPresentationDuration'
MIN_BUFFER_TIME = 'minBufferTime'


def get_tag_name(xml_element):
    """ Module to remove the xmlns tag from the name
        eg: '{urn:mpeg:dash:schema:mpd:2011}SegmentTemplate'
             Return: SegmentTemplate
    """
    try:
        tag_name = xml_element[xml_element.find('}')+1:]
    except TypeError:
        return None
    return tag_name


def get_playback_time(playback_duration):
    """ Get the playback time(in seconds) from the string:
        Eg: PT0H1M59.89S
    """
    # Get all the numbers in the string
    numbers = re.split('[PTHMS]', playback_duration)
    # remove all the empty strings
    numbers = [value for value in numbers if value != '']
    numbers.reverse()
    total_duration = 0
    for count, val in enumerate(numbers):
        if count == 0:
            # Seconds
            total_duration += float(val)
        elif count == 1:
            # Minutes to seconds
            total_duration += float(val) * 60
        elif count == 2:
            # Hours to seconds
            total_duration += float(val) * 60 * 60
    return total_duration


class MediaObject(object):
    """Object to handel audio and video stream """
    def __init__(self):
        self.min_buffer_time = None
        self.start = None
        self.timescale = None
        self.segment_duration = None
        self.initialization = None
        self.base_url = None
        self.url_list = list()


def get_url_list(media, segment_duration,  playback_duration):
    """
    Moduel to get the List of URLs
    """
    # Counting the init file
    total_playback = segment_duration
    segment_count = media.start
    # Get the Base URL string
    base_url = media.base_url
    base_url = base_url.split('$')
    base_url[1] = base_url[1].replace('$', '')
    base_url[1] = base_url[1].replace('Number', '')
    base_url = ''.join(base_url)
    while True:
        media.url_list.append(base_url % segment_count)
        segment_count += 1
        if total_playback > playback_duration:
            break
        total_playback += segment_duration
    return media


def read_mpd(mpd_file, dashplayback):
    """ Module to read the MPD file"""
    config_dash.LOG.info("Reading the MPD file")
    try:
        tree = ET.parse(mpd_file)
    except IOError:
        config_dash.LOG.error("MPD file not found. Exiting")
        return None
    root = tree.getroot()
    if 'MPD' in get_tag_name(root.tag).upper():
        if MEDIA_PRESENTATION_DURATION in root.attrib:
            dashplayback.playback_duration = get_playback_time(root.attrib[MEDIA_PRESENTATION_DURATION])
        if MIN_BUFFER_TIME in root.attrib:
            dashplayback.min_buffer_time = get_playback_time(root.attrib[MIN_BUFFER_TIME])
    child_period = root[0]

    for adaptation_set in child_period:
        playback_object = dashplayback.video
        for media_info in adaptation_set:
            if "SegmentTemplate" in get_tag_name(media_info.tag):
                # All bandwidths have the same template
                playback_object['base_url'] = media_info.attrib['media']
                playback_object['start'] = int(media_info.attrib['startNumber'])
                playback_object['timescale'] = float(media_info.attrib['timescale'])
                playback_object['initialization'] = media_info.attrib['initialization']
            if "Representation" in get_tag_name(media_info.tag):
                bandwidth = int(media_info.attrib['bandwidth'])
                print bandwidth
                #return media_info
                playback_object[bandwidth] = MediaObject()
                playback_object[bandwidth].segment_sizes = []
                for segment_info in media_info:
                    print get_tag_name(segment_info.tag)
                    if "SegmentSize" in get_tag_name(segment_info.tag):
                        config_dash.LOG.info("Reading the Segment Sizes")
                        try:
                            segment_size = segment_info.attrib['size']
                        except KeyError, e:
                            config_dash.LOG.error("Error in reading Segment sizes :{}".format(e))
                            continue
                        playback_object[bandwidth].segment_sizes.append(segment_size)
    return dashplayback