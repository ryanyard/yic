#!/usr/bin/python
from urllib2 import urlopen, quote
from BeautifulSoup import BeautifulSoup
from subprocess import call
from optparse import OptionParser
import os, sys, logging
 
url = "http://domain.com"
path = "/path/"
build = "build"
tmp_path = "/tmp/yic"
log_path = "/var/log/"
script_prefix = "/scripts/"
datafile_prefix = "/datafiles/"
datafile = {}

logging.basicConfig(filename=log_path + 'yic.log',level=logging.DEBUG) 

def cleanup():
  # need to work on this
  return

def getFastestMirror():
  # need to get code from plugin, module?
  return

def getYumURLs():
  # parse the mirror list
  return

def logit():
  # clean up logging routine
  return

def snapshot():
  # get the snapshot plugin code, module?
  return

def listFile(prefix, file):
  page = urlopen(url + path + build + prefix)
  soup = BeautifulSoup(page)
  try:
    for item in soup.findAll('a', href=True):
      this_href = item["href"]
      if this_href.endswith(file):
        remote_file = quote(this_href, safe=":/")
        print remote_file
  except(), e:
    logging.debug('yic.listFile: Unable to find valid yum baserepo URLs')
 
def getFile(prefix, file):
  page = urlopen(url + path + build + prefix)
  soup = BeautifulSoup(page)
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
    logging.debug('yic.getFile: Unable to find valid yum baserepo URLs')
 
def processDataFile(prefix, file):
  logging.info('======================================================================')
  logging.info('Processing DATAFILE: %s', file)
  logging.info('======================================================================')
  try:
    with open(tmp_path + datafile_prefix + file) as rcfile:
      for line in rcfile:
        (key, val) = line.strip().replace('"','').split('=', 2)
        datafile[(key)] = val
    rcfile.close
    install()
    uninstall()
  except(), e:
     logging.debug('yic.processDataFile: Failure')
 
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
      logging.info('======================================================================')
      logging.info('Processing PRESCRIPTS: %s', rc)
      logging.info('======================================================================')
 
def processPreScripts(prefix):
  if datafile['PRE_INSTALL_SCRIPTS'].endswith(".sh"):
    for sh in datafile['PRE_INSTALL_SCRIPTS'].split(' '):
      getFile(prefix, sh)
      preInstallScript(sh)
      logging.info('======================================================================')
      logging.info('Processing PRESCRIPTS: %s', sh)
      logging.info('======================================================================')
    
def processPreUnScripts(prefix):
  if datafile['PRE_UNINSTALL_SCRIPTS'].endswith(".sh"):
    for sh in datafile['PRE_UNINSTALL_SCRIPTS'].split(' '):
      getFile(prefix, sh)
      logging.info('======================================================================')
      logging.info('Processing PREUNSCRIPTS: %s', sh)
      logging.info('======================================================================')
 
def processPostScripts(prefix):
  if datafile['POST_INSTALL_SCRIPTS'].endswith(".sh"):
    for sh in datafile['POST_INSTALL_SCRIPTS'].split(' '):
      getFile(prefix, sh)
      postInstallScript(sh)
      logging.info('======================================================================')
      logging.info('Processing POSTSCRIPTS: %s', sh)
      logging.info('======================================================================')
 
def processPostUnScripts(prefix):
  if datafile['POST_UNINSTALL_SCRIPTS'].endswith(".sh"):
    for sh in datafile['POST_UNINSTALL_SCRIPTS'].split(' '):
      getFile(prefix, sh)
      logging.info('======================================================================')
      logging.info('Processing POSTUNSCRIPTS: %s', sh)
      logging.info('======================================================================')
 
def preInstallScript(file):
  script = tmp_path + script_prefix + file
  chmod = "/usr/bin/sudo /bin/chmod 755 " + script
  sudo_script = "/usr/bin/sudo " + script
  try:
    call(chmod, shell=True)
    call(sudo_script, shell=True)
  except(), e:
    logging.debug('yic.preInstallScript: Failure')
 
def postInstallScript(file):
  script = tmp_path + script_prefix + file
  chmod = "/usr/bin/sudo /bin/chmod 755 " + script
  sudo_script = "/usr/bin/sudo " + script
  try:
    call(chmod, shell=True)
    call(sudo_script, shell=True)
  except(), e:
    logging.debug('yic.postInstallScript: Failure') 

def installRPMs():
  if datafile['RPMLIST']:
    try:
      for rpm in datafile['RPMLIST'].split(' '):
        yum = "/usr/bin/sudo /usr/bin/yum -y install " + rpm
        call(yum, shell=True)
    except(), e:
      logging.debug('yic.installRPMs: Failure')

def removeRPMs():
  if datafile['RPMLIST']:
    try:
      for rpm in datafile['RPMLIST'].split(' '):
        yum = "/usr/bin/sudo /usr/bin/yum -y remove " + rpm
        call(yum, shell=True)
    except(), e:
      logging.debug('yic.removeRPMs: Failure')
 
def main():
  parser = OptionParser(usage="usage: %prog [options] filename",
                        version="%prog 1.0")
  parser.add_option("-f", "--file", type="string", dest="filename",
                    help="datafile name", metavar="FILE")
  (options, args) = parser.parse_args()

  processDataFiles(script_prefix, sys.argv[2])
 
if __name__ == '__main__':
    main()
