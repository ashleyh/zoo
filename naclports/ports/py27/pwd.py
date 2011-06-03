#silly replacement pwd
from collections import namedtuple
_Pwdent = namedtuple('_Pwdent', 'pw_name pw_passwd pw_uid pw_gid pw_gecos pw_dir pw_shell')
_pwdent = _Pwdent('zoo', 'zoo', 0, 0, '', '/home/zoo/', '/bin/bash')
def getpwuid(uid): return _pwdent
def getpwname(name): return _pwdent
def getpwdall(): return [_pwdent]
