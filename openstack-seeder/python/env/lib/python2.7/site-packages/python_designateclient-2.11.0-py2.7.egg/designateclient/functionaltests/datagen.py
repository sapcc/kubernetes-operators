"""
Copyright 2015 Rackspace

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
import random
import string


def random_digits(n=8):
    return "".join([random.choice(string.digits) for _ in range(n)])


def random_tld(name='testtld'):
    return "{0}{1}".format(name, random_digits())


def random_tsigkey_name(name='testtsig'):
    return "{0}{1}".format(name, random_digits())


def random_tsigkey_secret(name='test-secret'):
    return "{0}-{1}".format(name, random_digits(254 - len(name)))


def random_zone_name(name='testdomain', tld='com'):
    return "{0}{1}.{2}.".format(name, random_digits(), tld)


def random_a_recordset_name(zone_name, recordset_name='testrecord'):
    return "{0}{1}.{2}".format(recordset_name, random_digits(), zone_name)


def random_blacklist(name='testblacklist'):
    return '{0}{1}'.format(name, random_digits())


def random_zone_file(name='testzoneimport'):
    return "$ORIGIN {0}{1}.com.\n" \
           "$TTL 300\n" \
           "{0}{1}.com. 300 IN SOA ns.{0}{1}.com. " \
           "nsadmin.{0}{1}.com. 42 42 42 42 42\n" \
           "{0}{1}.com. 300 IN NS ns.{0}{1}.com.\n" \
           "{0}{1}.com. 300 IN MX 10 mail.{0}{1}.com.\n" \
           "ns.{0}{1}.com. 300 IN A 10.0.0.1\n" \
           "mail.{0}{1}.com. 300 IN A 10.0.0.2\n".format(name, random_digits())
