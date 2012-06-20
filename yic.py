#!/usr/bin/python
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# written by Ed Brand
#            Ryan Yard <ryard@redhat.com>

from urllib2 import urlopen, quote
from BeautifulSoup import BeautifulSoup
from subprocess import call
from optparse import OptionParser
import os, sys, time, logging, inspect
import yic_snapshot, yic_fastmirror
 
path = "/path/"
build = "build"
tmp_path = "/tmp/yic"
script_prefix = "/scripts/"
datafile_prefix = "/datafiles/"
datafile = {}
snapshot_file = "/root/.snapshot"
mirrorlist = ["http://localhost/", "http://localhost/"]
#mirrorlist = ["http://mirror.overthewire.com.au/pub/epel/", "http://epel.mirrors.arminco.com/", "http://mirror.iprimus.com.au/epel/"]

log_file = "/var/log/yic/yic.log"
log_format = '%(asctime)s - %(name)s:%(levelname)s:%(message)s'
logging.basicConfig(format=log_format, filename=log_file, level=logging.DEBUG) 

def cleanup():
  # need to work on this
  return

def getFastestMirror():
  global url
  url = yic_fastmirror.FastestMirror(mirrorlist).get_mirrorlist()[0]
  print "Result: " + url
  return url

def funcname():
  return inspect.stack()[1][3]

def logit(function, log):
  logging.info('======================================================================')
  logging.info('Processing %s : %s', function, log)
  logging.info('======================================================================')

def snapShot():
  if os.path.exists(snapshot_file):
    snapshot_tag = "yic_" + time.strftime("%Y%m%d%H%M%S")
    volumes = yic_snapshot.get_volumes()
    for volume in volumes:
      yic_snapshot.create_lvm_snapshot(snapshot_tag, volume)
    return 
  else:
    logit(funcname(), "No Snapshot")

def listFile():
  page = urlopen(url + path + build + datafile_prefix)
  soup = BeautifulSoup(page)
  try:
    for item in soup.findAll('a', href=True):
      this_href = item["href"]
      if this_href.endswith(".rc"):
        remote_file = quote(this_href, safe=":/")
        print remote_file
  except(), e:
    logging.debug('%s: Unable to find valid yum baserepo URLs', funcname())
 
def getFile(prefix, file):
  page = urlopen(url + path + build + prefix)
  soup = BeautifulSoup(page)
  if not os.path.exists(tmp_path + prefix):
    os.makedirs(tmp_path + prefix)
  try:
    for item in soup.findAll('a', href=True):
      this_href = item["href"]
      if this_href.endswith(file):
        local_file = this_href.split("/")[-1]
        remote_file = quote(this_href, safe=":/")
        rfile = urlopen(url + path + build + prefix + remote_file)
        with open(tmp_path + prefix + local_file, "w") as lfile:
          lfile.write(rfile.read())
  except(), e:
    logging.debug('%s: Unable to find valid yum baserepo URLs', funcname())
 
def processDataFile(prefix, file):
  logit(funcname(), file)
  try:
    with open(tmp_path + datafile_prefix + file) as rcfile:
      for line in rcfile:
        (key, val) = line.strip().replace('"','').split('=', 2)
        datafile[(key)] = val
    rcfile.close
    install()
    uninstall()
  except(), e:
     logging.debug('%s: Failure', funcname())
 
def install():
  processPreScripts(script_prefix)
  installRPMs()
  processPostScripts(script_prefix)

def uninstall():
  processPreUnScripts(script_prefix)
  removeRPMs()
  processPostUnScripts(script_prefix)

def processDataFiles(prefix, file):
  getFile (datafile_prefix, file)
  processDataFile(prefix, file)
  if datafile['DATAFILES'].endswith(".rc"):
    for rc in datafile['DATAFILES'].split(' '):
      getFile (datafile_prefix, rc)
      processDataFile(prefix, rc)
      logit(funcname(), file)
 
def processPreScripts(prefix):
  if datafile['PRE_INSTALL_SCRIPTS'].endswith(".sh"):
    for sh in datafile['PRE_INSTALL_SCRIPTS'].split(' '):
      getFile(prefix, sh)
      preInstallScript(sh)
      logit(funcname(), sh)
    
def processPreUnScripts(prefix):
  if datafile['PRE_UNINSTALL_SCRIPTS'].endswith(".sh"):
    for sh in datafile['PRE_UNINSTALL_SCRIPTS'].split(' '):
      getFile(prefix, sh)
      logit(funcname(), sh)
 
def processPostScripts(prefix):
  if datafile['POST_INSTALL_SCRIPTS'].endswith(".sh"):
    for sh in datafile['POST_INSTALL_SCRIPTS'].split(' '):
      getFile(prefix, sh)
      postInstallScript(sh)
      logit(funcname(), sh)
 
def processPostUnScripts(prefix):
  if datafile['POST_UNINSTALL_SCRIPTS'].endswith(".sh"):
    for sh in datafile['POST_UNINSTALL_SCRIPTS'].split(' '):
      getFile(prefix, sh)
      logit(funcname(), sh)
 
def preInstallScript(file):
  script = tmp_path + script_prefix + file
  chmod = "/usr/bin/sudo /bin/chmod 755 " + script
  sudo_script = "/usr/bin/sudo " + script
  try:
    call(chmod, shell=True)
    call(sudo_script, shell=True)
  except(), e:
    logging.debug('%s: Failure', funcname())
 
def postInstallScript(file):
  script = tmp_path + script_prefix + file
  chmod = "/usr/bin/sudo /bin/chmod 755 " + script
  sudo_script = "/usr/bin/sudo " + script
  try:
    call(chmod, shell=True)
    call(sudo_script, shell=True)
  except(), e:
    logging.debug('%s: Failure', funcname()) 

def installRPMs():
  if datafile['RPMLIST']:
    try:
      for rpm in datafile['RPMLIST'].split(' '):
        yum = "/usr/bin/sudo /usr/bin/yum -y install " + rpm
        call(yum, shell=True)
    except(), e:
      logging.debug('%s: Failure', funcname())

def removeRPMs():
  if datafile['RPMLIST']:
    try:
      for rpm in datafile['RPMLIST'].split(' '):
        yum = "/usr/bin/sudo /usr/bin/yum -y remove " + rpm
        call(yum, shell=True)
    except(), e:
      logging.debug('%s: Failure', funcname())
 
def main():
  parser = OptionParser(usage="usage: %prog [options] filename",
                        version="%prog 1.0")
  parser.add_option("-f", "--file", type="string", dest="filename",
                    help="datafile name", metavar="FILE")
  (options, args) = parser.parse_args()
  snapShot()
  getFastestMirror()
  processDataFiles(script_prefix, sys.argv[2])
 
if __name__ == '__main__':
    main()
