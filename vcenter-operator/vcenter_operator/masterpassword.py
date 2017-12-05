import logging
import struct
from hashlib import sha256
from hmac import HMAC

import six
from enum import Enum

log = logging.getLogger(__name__)

SCRYPT_N = 32768
SCRYPT_R = 8
SCRYPT_P = 2
SCRYPT_LEN = 64

try:
    # Requires openssl 1.1
    from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
    from cryptography.hazmat.backends import default_backend


    def hash(password, salt):
        kdf = Scrypt(salt=salt,
                     length=SCRYPT_LEN,
                     n=SCRYPT_N,
                     r=SCRYPT_R,
                     p=SCRYPT_P,
                     backend=default_backend())
        return kdf.derive(password.encode('utf-8'))

except ImportError:
    try:
        from pyscrypt import shash


        def hash(password, salt):
            return shash(password=password.encode('utf-8'),
                         salt=salt,
                         N=SCRYPT_N,
                         r=SCRYPT_R,
                         p=SCRYPT_P,
                         dkLen=SCRYPT_LEN)
    except ImportError:
        from scrypt import hash as shash


        def hash(password, salt):
            return shash(password=password.encode('utf-8'),
                         salt=salt,
                         N=SCRYPT_N,
                         r=SCRYPT_R,
                         p=SCRYPT_P,
                         buflen=SCRYPT_LEN)


class Templates(Enum):
    max = ['anoxxxxxxxxxxxxxxxxx', 'axxxxxxxxxxxxxxxxxno']
    long = ['CvcvnoCvcvCvcv', 'CvcvCvcvnoCvcv', 'CvcvCvcvCvcvno', 'CvccnoCvcvCvcv', 'CvccCvcvnoCvcv', 'CvccCvcvCvcvno',
            'CvcvnoCvccCvcv', 'CvcvCvccnoCvcv', 'CvcvCvccCvcvno', 'CvcvnoCvcvCvcc', 'CvcvCvcvnoCvcc', 'CvcvCvcvCvccno',
            'CvccnoCvccCvcv', 'CvccCvccnoCvcv', 'CvccCvccCvcvno', 'CvcvnoCvccCvcc', 'CvcvCvccnoCvcc', 'CvcvCvccCvccno',
            'CvccnoCvcvCvcc', 'CvccCvcvnoCvcc', 'CvccCvcvCvccno']
    medium = ['CvcnoCvc', 'CvcCvcno']
    basic = ['aaanaaan', 'aannaaan', 'aaannaaa']
    short = ['Cvcn']
    pin = ['nnnn']


CHARACTER_CLASSES = {
    'V': 'AEIOU',
    'C': 'BCDFGHJKLMNPQRSTVWXYZ',
    'v': 'aeiou',
    'c': 'bcdfghjklmnpqrstvwxyz',
    'A': 'AEIOUBCDFGHJKLMNPQRSTVWXYZ',
    'a': 'AEIOUaeiouBCDFGHJKLMNPQRSTVWXYZbcdfghjklmnpqrstvwxyz',
    'n': '0123456789',
    'o': "@&%?,=[]_:-+*$#!'^~;()/.",
    'x': 'AEIOUaeiouBCDFGHJKLMNPQRSTVWXYZbcdfghjklmnpqrstvwxyz0123456789!@#$%^&*()'
}

DEFAULT_NAMESPACE = six.b('com.lyndir.masterpassword')


class MasterPassword(object):
    def __init__(self, name, password, namespace=None):
        self.namespace = namespace or DEFAULT_NAMESPACE
        salt = self.namespace + struct.pack('!I', len(name)) + name.encode('utf-8')
        self.key = hash(password, salt)

    def seed(self, site, counter=1):
        message = self.namespace + struct.pack('!I', len(site)) + site.encode('utf-8') + struct.pack('!I', counter)
        return HMAC(self.key, message, sha256).digest()

    def derive(self, type, site, counter=1):
        value = ""
        seed = self.seed(site, counter)
        try:
            templates = Templates[type].value
        except KeyError as e:
            log.error("Unknown key type '{}'".format(type))
            raise e
        template = templates[six.byte2int(seed[0]) % len(templates)]
        for i in range(0, len(template)):
            passChars = CHARACTER_CLASSES[template[i]]
            passChar = passChars[six.byte2int(seed[i + 1]) % len(passChars)]
            value += passChar

        return value


def main():
    import sys
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)-15s %(message)s')
    mpw = MasterPassword(sys.argv[1], sys.argv[2])
    print(mpw.derive(sys.argv[3], sys.argv[4]))
