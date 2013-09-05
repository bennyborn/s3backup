class config:

	AWS_HOST = 's3-eu-west-1.amazonaws.com';
	AWS_ACCESS_KEY_ID = 'XXXXXXXXXXXXXXX'
	AWS_SECRET_ACCESS_KEY = 'XXXXXXXXXXXXXXX'

	MAX_STORAGE_DAYS = 30;

	jobs = [
		{
			'name'			: 'name for the backup job'
		,	'host' 			: '127.0.0.1'
		,	'user' 			: 'root'
		,	'bucket' 		: 'my-first-bucket'
		, 	'databases' 	: [
				{ 'user':'db48567494', 'pass':'specialsecret', 'name':'db-test-001' }
			]
		,	'directories'	: [
				{'src':'/home/benny', 'exc': ['tmp','.old'], 'dst':'my_home_dir'} 
			,	{'src':'/pictures', 'exc': ['.tiff'], 'dst':'precious_moments'} 
			]
		}
	]