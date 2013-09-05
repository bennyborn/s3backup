#!/usr/bin/python

import backup

import subprocess
import os
import sys
import shutil
from time import gmtime, strftime
from dateutil.parser import parse
import datetime

import gzip
import tarfile

import boto
import boto.s3.connection
from boto.s3.key import Key


def log( message ):
	ts = '[' + strftime("%Y-%m-%d %H:%M:%S", gmtime()) + ']'
	sys.stdout.write("\n")
	sys.stdout.write(ts)
	sys.stdout.write(' - ')
	sys.stdout.write(message)
	sys.stdout.flush()

def percent_cb(complete, total):
    sys.stdout.write('.')
    sys.stdout.flush()

def removeDir(path):
    if os.path.isdir(path):
        shutil.rmtree(path)

"""switch to scripts directory"""
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)

s3conn = boto.connect_s3(
        aws_access_key_id = backup.config.AWS_ACCESS_KEY_ID,
        aws_secret_access_key = backup.config.AWS_SECRET_ACCESS_KEY,
        host = backup.config.AWS_HOST,
        calling_format = boto.s3.connection.OrdinaryCallingFormat()
        )


date = strftime("%Y-%m-%d", gmtime())

for job in backup.config.jobs:


	log(('job "%s" has been started' % (job['name']) ))


	"""Open bucket, create if non existent"""
	try:
		bucket = s3conn.get_bucket(job['bucket'])
	except Exception:
		log(('bucket "%s" has been created' % (job['bucket']) ))
		try:
			bucket = s3conn.create_bucket(job['bucket'])
		except Exception:
			log(('ERROR could not create bucket "%s" - skipping!' % (job['bucket']) ))
			continue


	"""Find expired Backups"""
	log('searching for outdated backups...')
	rs = bucket.list()

	for key in rs:

		"""Calculate age of files"""
		modified = parse(key.last_modified[:10])
		current = datetime.datetime.now()
		age = abs((current - modified).days)

		if age > backup.config.MAX_STORAGE_DAYS:
			print "%s is %s days old and will be deleted..." % (key.name,age)
			bucket.delete_key(key)


	"""Create temporary backup directory"""
	directory = date + '/' + job['name']

	if not os.path.exists(directory):
		os.makedirs(directory)


	"""Backup directories"""
	if 'directories' in job :
		for d in job['directories']:

			rsync = 'rsync -avz '

			if 'exc' in d:
				for ex in d['exc']:
					rsync+= "--exclude '" + ex + "' "

			rsync+= '-e ' + ('ssh %s@%s:%s' % (job['user'],job['host'],d['src']))
			rsync+= ' ' + directory + '/' + d['dst']

			"""Retreive directory via rsync"""
			log(('backing up %s...' % (d['src']) ))

			fnull = open(os.devnull, 'w')
			p = subprocess.Popen( rsync, shell=True, stdout=fnull, stderr=subprocess.STDOUT )
			p.wait()


			"""Compress directory"""
			if os.path.isdir(directory + '/' + d['dst']):
				log(('compressing directory %s...' % (d['src']) ))

				tar = tarfile.open(directory + '/' + d['dst'] + ".tar.gz", "w|gz")
				tar.add(directory + '/' + d['dst'])
				tar.close()

				log('deleting uncompressed directory...')
				removeDir(directory + '/' + d['dst'])


				"""Upload compressed directory"""
				log('uploading %s' % (os.path.basename(tar.name)) )

				k = Key(bucket)
				k.key = date + '/' + os.path.basename( tar.name )
				k.set_contents_from_filename(tar.name, cb=percent_cb, num_cb=10)

				os.remove(tar.name)
				del tar
			else:
				log(('ERROR - could not retreive directory %s. skipping.' % (d['src']) ))


	"""Backup databases"""
	if 'databases' in job:
		for db in job['databases']:

			log(('dumping database %s...' % (db['name'])) )

			with open(directory + '/' + db['name']+'.sql', 'w') as rawdump:
				subprocess.call(['mysqldump', '--host='+job['host'], '--user='+db['user'], '--password='+db['pass'], db['name']], stdout=rawdump)

			"""Compress dump"""
			log('compressing dump...')

			rawdump = open(directory + '/' + db['name']+'.sql', 'rb')

			zipdump = gzip.open(directory + '/' + db['name']+'.sql.gz', 'wb')
			zipdump.writelines(rawdump)
			zipdump.close()

			rawdump.close()

			log('deleting uncompressed file...')

			os.remove(rawdump.name)
			del rawdump

			"""Upload zipped dump"""
			log('uploading %s' % (os.path.basename(zipdump.name)) )

			k = Key(bucket)
			k.key = date + '/' + os.path.basename( zipdump.name )
			k.set_contents_from_filename(zipdump.name, cb=percent_cb, num_cb=10)

			os.remove(zipdump.name)
			del zipdump

	removeDir(directory)

	log(('job "%s" completed!' % (job['name']) )+"\n")

removeDir(date)