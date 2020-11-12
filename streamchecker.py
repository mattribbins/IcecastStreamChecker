#!/usr/bin/python
# -*- coding: utf-8 -*-

# Icecast Stream Checker
#
# Author: Matt Ribbins (mattribbins.co.uk) for Celador Radio
# Description: Checks web streams are alive, report results either on screen or via email.
# Dependencies: python3, requests, python-ffmpeg, numpy
# Usage: ./streamchecker.py

import sys
import getopt
import smtplib
import urllib2
import ffmpeg
import numpy
import socket
import time
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
from gevent import monkey

##########
# Config #
##########
# Icecast servers
hosts = ['http://icecast-server:8000']

# Streams to check
streams = ['sam-bristol', 'sam-swindon', 'sam-hants', 'sam-dorset', 'sam-thames', 'fire-bournemouth', 'anglian-nnr',
           'anglian-norwich', 'anglian-beach', 'anglian-town', 'anglian-dream', 'breeze-nglos', 'breeze-bristol',
           'breeze-bath', 'breeze-wwilts', 'breeze-nsoms', 'breeze-wsoms', 'breeze-ssoms', 'breeze-ndorset',
           'breeze-sdevon', 'breeze-southampton', 'breeze-winchester', 'breeze-portsmouth', 'breeze-ehants',
           'breeze-andover', 'breeze-basingstoke', 'breeze-newbury', 'breeze-reading']
formats = ['-src', '-48.aac', '-96.aac', '-128.aac', '-96.mp3']

# Audio check settings
silence_threshold = 100

# Email settings
email_send_on_ok = False
email_format = "plain"

# Email server SMTP settings
smtp_server = "smtp.server"
smtp_port = "25"
smtp_username = ""
smtp_password = ""
smtp_sender = "Celador Streamchecker <streamchecker@mprdev.click>"
smtp_destination = "changeme@mprdev.click"

# Debug prints on/off
debug_print = False
##########


ver = "1.3.1.5"
log = ""
monkey.patch_all()


def main():
    global opts
    success = 0
    fail = 0
    force_email = email_send_on_ok
    output("Stream Checker {0} \r\nRunning on {1}\r\n".format(ver,socket.gethostname()))
    output("Started at: {}".format(time.strftime("%d %b %Y %H:%M:%S", time.gmtime())))
    # Any inline arguments to consider?
    try:
        opts, args = getopt.getopt(sys.argv[1:], "f", ["force-email="])
    except getopt.GetoptError as e:
        output("Args error. " + e.message)
        exit(1)
    for opt, arg in opts:
        # Force email?
        if opt in ("-f", "--force-email"):
            debug("Force email enabled")
            force_email = True
    # Go through all streams, host by host
    for host in hosts:
        output("Checking streams on host " + host)
        list = celador_generate_streams(streams, formats)
        for stream in list:
            url = host + "/" + stream
            result, message = check_stream(url)
            if result is not True:
                fail += 1
                output("FAIL: [{2}] {1} {0}".format(message, stream, time.strftime("%H:%M:%S", time.gmtime())))
            else:
                success += 1
                debug("OK: {1}, {0}".format(message, stream))

    output("Finished at: %s" % time.strftime("%d %b %Y %H:%M:%S", time.gmtime()))
    output("\r\nSUMMARY")
    output(str(len(streams)) + " stations(s) checked on " + str(len(hosts)) + " server(s).")
    output(str(success) + " streams are alive.")
    output(str(fail) + " have failed.")
    if force_email is True:
        send_email(log, fail)
    elif fail > 0:
        send_email(log, fail)


def output(string):
    global log
    print string
    log = log + string + "\r\n"


def debug(string):
    global debug_print
    if debug_print is True:
        print string


def get_avg_peak_audio(url):
    audio, err = (ffmpeg
                  .input(url)
                  .output('-', format='s16le', acodec='pcm_s16le', ac=1, ar='16k', t="00:00:01")
                  .overwrite_output()
                  .run(capture_stdout=True)
                  )
    data = numpy.fromstring(audio, dtype=numpy.int16)
    peak = int(round(numpy.average(numpy.abs(data)) * 2))
    return peak


def check_stream(url):
    debug("GET: " + url)
    request = urllib2.Request(url)
    # Try to open the URL, read header value
    try:
        request.add_header('Icy-MetaData', 1)
        response = urllib2.urlopen(request)
        icy_metaint_header = response.headers.get('icy-metaint')
        icy_format = response.headers.get('Content-Type')
        if icy_metaint_header is not None:
            debug(str(response.getcode()))
            metaint = int(icy_metaint_header)
            read_buffer = metaint + 255
            content = response.read(read_buffer)
            title = content[metaint:].split(";")[0]
            debug(title)
        if icy_format == "audio/mpeg":
            format = "mp3"
            debug("We detect %s" % format)
        elif icy_format == "audio/aac":
            format = "aac"
            debug("We detect %s" % format)
        else:
            raise Exception("Unknown audio format, cannot check audio is valid.")

        # Now check if there is valid audio (i.e. not silence)
        peak = get_avg_peak_audio(url)
        debug("Peak %d" % peak)
        if peak < silence_threshold:
            # Double check to ensure this is not a false positive.
            debug("Double checking...")
            peak = get_avg_peak_audio(url)
            if peak < silence_threshold:
                raise Exception("No audio! Peak level %d" % peak)
        return True, "200"
    except urllib2.URLError as e:
        return False, "{0} {1}".format(str(e.code), e.reason)
    except ffmpeg.Error as e:
        # We are not too worried if ffmpeg errors occur for the silence detector
        return True, ("WARNING ffmpeg {0} ".format(e.message))
    except Exception as e:
        return False, "{0}".format(e.message)


def send_email(body, fail_count):
    debug("Sending email... " + smtp_server)
    server = smtplib.SMTP(smtp_server, smtp_port)
    if smtp_username is not "":
        server.login(smtp_username, smtp_password)
    msg = MIMEMultipart()
    msg['From'] = smtp_sender
    msg['To'] = smtp_destination
    # Do we send normal OK or error FAIL email?
    if fail_count > 0:
        msg['Subject'] = "Streamchecker - Streams FAILED"
        msg['X-Priority'] = '2'
    else:
        msg['Subject'] = "Streamchecker - Streams OK"
    # Send the message
    msg.attach(MIMEText(body, 'plain'))
    text = msg.as_string()
    debug(text)
    try:
        server.set_debuglevel(debug_print)
        server.sendmail(smtp_sender, smtp_destination, text)
        server.quit()
    except smtplib.SMTPException as e:
        debug("Email failed to send. " + e.message)
    except Exception as e:
        debug("Email error " + e.message)


def celador_generate_streams(streams, formats):
    output = []
    for stream in streams:
        for format in formats:
            output.append(stream + "" + format)
    return output


if __name__ == "__main__":
    main()