#
#  syncContacts.py
#  Synchronize with Google Gmail Contacts
#  Based on GData Sample Codes
#
#   Originally developed by Cristiano Lazzari <crlazzari@gmail.com>
#   Date Nov 27, 2009
#   
#   Modified by Daniel Mescheder
#   Date Jan 20, 2012

import sys
import getopt
import getpass
import atom
import gdata.contacts
import gdata.contacts.client
import gdata.contacts.data
import gdata.contacts.service
import string
import os
import gdata.data
import re

city_re = re.compile("([^,]+)(, [^ ]+)? ([^ ]+)")
name_re = re.compile("^(.+?) ((?:von |van |de )?[^ ]+)$")
image_dir = "%s/.bbdb-images" % os.path.expanduser("~")


def test(user, pw):
  gd_client = create_client(user,pw)
  for e in iter_feed(gd_client):
    print format_entry(e)

def iter_feed(gd_client):
  """
  Iterate over a paginated feed.
  """
  feed = gd_client.GetContactsFeed()
  while feed:
    for entry in feed.entry:
      yield entry
    # Check whether there is another page and if yes
    next_link = feed.GetNextLink()
    feed = None
    if next_link:
      feed = gd_client.GetContactsFeed(uri=next_link.href)

def create_client(email, password):
  """
    Takes an email and password corresponding to a gmail account to
    initialize a Contacts feed.
    
    Args:
      email: [string] The e-mail address of the account to use for the sample.
      password: [string] The password corresponding to the account specified by
          the email parameter.    
  """
  gd_client = gdata.contacts.service.ContactsService()
  gd_client.email = email
  gd_client.password = password
  gd_client.source = 'syncContacts'
  gd_client.ProgrammaticLogin()
  return gd_client

def contacts_to_bbdb(gd_client):
  fname = "%s/.bbdb" % os.path.expanduser("~")
  with open(fname, 'w') as f:
    f.write(';; -*-coding: utf-8-emacs;-*-\n')
    f.write(';;; file-version: 6\n')
    f.write(';;; user-fields: (title website department)\n')
    for i, entry in enumerate(iter_feed(gd_client)):
         f.write("%s\n" % format_entry(entry))
         fetch_image(gd_client, entry)

def fetch_image(gd_client, entry):
  try:
    photo = gd_client.GetPhoto(entry)
  except gdata.service.RequestError:
    return # photo not found
  if photo is None:  return # Nothing to do here
  with open("%s/%s.jpg" % (image_dir,entry.title.text), "w") as f:
    f.write(photo)

def format_entry(entry):
  name = format_name(entry)
  company = format_company(entry)
  mails = format_mails(entry)
  address = format_address(entry)
  phones = format_phones(entry)
  notes = format_notes(entry)
  return "[%s %s %s %s %s ( %s ) nil]" % (name, company, phones, address, mails, notes)

def format_name(entry):
  firstname, lastname, nickname = "nil", "nil", "nil"
  if (entry.title and entry.title.text):
    match = name_re.match(entry.title.text)
    if match:
      firstname = '"%s"' % match.group(1)
      lastname = '"%s"' % match.group(2)
    else:
      firstname = '"%s"' % entry.title.text
    
  if (entry.nickname and entry.nickname.text):
    nickname = '"%s"' % entry.nickname.text
  return '%s %s %s' % (firstname, lastname, nickname)

def format_company(entry):
  company  = 'nil' 
  if entry.organization:
    if entry.organization.org_name and entry.organization.org_name.text:
      company = '"%s"' % entry.organization.org_name.text
  return company

def format_mails(entry):
  emails = [ ('"%s"' % email.address) for email in entry.email]
  if emails:
    return "( %s )" % " ".join(emails)
  else:
    return "nil"

def format_address(entry):
  address = []
  for a in entry.postal_address:
    if ( a.rel == gdata.contacts.REL_WORK ): atype = 'Work'    
    elif ( a.rel == gdata.contacts.REL_HOME ): atype = 'Home'
    else: atype = 'Other'
    adr = a.text.strip().split("\n")
    if len(adr) < 3:
      print "WARNING: address\n %s \n incomplete in record %s" % (a.text.strip(), entry.title.text)
      continue
    street = adr[0] # the first line is street and number
    m = city_re.match(adr[1]) # the second line is city, state and postcode. see whether it matches:
    if not m:
      print "WARNING: unable to read address %s in record %s" % (adr[1], entry.title.text)
      continue
    city = m.group(1)
    if m.group(2): state = m.group(2)[2:]
    else: state = ""
    postcode = m.group(3)
    country = adr[2]
    address.append('["%s" ("%s") "%s" "%s" "%s" "%s"]' % (atype, street, city, state, postcode, country))
  if address:
    return '( %s )' % " ".join(address)
  else:
    return "nil"

def format_phones(entry):    
  phones = []
  for phone in entry.phone_number:    
    if ( phone.rel == gdata.contacts.PHONE_WORK ): phonetype = 'Work'    
    elif ( phone.rel == gdata.contacts.PHONE_HOME ): phonetype = 'Home'
    elif ( phone.rel == gdata.contacts.PHONE_MOBILE ): phonetype = 'Mobile'
    else: phonetype = 'Other'
    phones.append('["%s" "%s"]' % (phonetype, phone.text))
  if phones:
    return "( %s )" % " ".join(phones)
  else:
    return "nil"

def format_notes(entry):
  notes = ""
  if entry.content and entry.content.text :
    notes_list = [('%s' % note) for note in entry.content.text.strip().split("\n")]
    notes = '(notes . "%s" )' % " ".join(notes_list)
  return notes
  

def run(user, pw):
  try:
    gd_client = create_client(user, pw)
    print 'MSG: Connection to Google OK!!!'
  except gdata.service.BadAuthentication:
    print 'Invalid user credentials given.'
    return
  contacts_to_bbdb(gd_client)  
      
##
def main():
  """Syncronizes with Google Gmail Contacts."""
 
  try:
    opts, args = getopt.getopt(sys.argv[1:], '', ['user=', 'pw='])
  except getopt.error, msg:
    print 'python syncContacts.py --user [username] --pw [password]'
    sys.exit(2)

  user = ''
  pw = ''
  # Process options
  for option, arg in opts:
    if option == '--user':
      user = arg
    elif option == '--pw':
      pw = arg

  run(user,pw)




if __name__ == '__main__':
  main()



# END
