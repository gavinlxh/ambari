#!/usr/bin/env python
"""
Licensed to the Apache Software Foundation (ASF) under one
or more contributor license agreements.  See the NOTICE file
distributed with this work for additional information
regarding copyright ownership.  The ASF licenses this file
to you under the Apache License, Version 2.0 (the
"License"); you may not use this file except in compliance
with the License.  You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

"""
import os
import sys
from resource_management.libraries.functions.version import format_stack_version
from resource_management.libraries.script.script import Script
from resource_management.libraries.functions.format import format
from resource_management.libraries.functions.default import default

import status_params
from resource_management.libraries.functions.stack_features import check_stack_feature
from resource_management.libraries.functions import StackFeature
from resource_management.libraries.functions.is_empty import is_empty

# server configurations
config = Script.get_config()
stack_root = Script.get_stack_root()
tmp_dir = Script.get_tmp_dir()

cluster_name = config['clusterName']

# security enabled
security_enabled = status_params.security_enabled

if security_enabled:
  _hostname_lowercase = config['hostname'].lower()
  _atlas_principal_name = config['configurations']['application-properties']['atlas.authentication.principal']
  atlas_jaas_principal = _atlas_principal_name.replace('_HOST',_hostname_lowercase)
  atlas_keytab_path = config['configurations']['application-properties']['atlas.authentication.keytab']

stack_name = status_params.stack_name

# New Cluster Stack Version that is defined during the RESTART of a Stack Upgrade
version = default("/commandParams/version", None)

# stack version
stack_version_unformatted = config['hostLevelParams']['stack_version']
stack_version_formatted = format_stack_version(stack_version_unformatted)

metadata_home = os.environ['METADATA_HOME_DIR'] if 'METADATA_HOME_DIR' in os.environ else format('{stack_root}/current/atlas-server')
metadata_bin = format("{metadata_home}/bin")

python_binary = os.environ['PYTHON_EXE'] if 'PYTHON_EXE' in os.environ else sys.executable
metadata_start_script = format("{metadata_bin}/atlas_start.py")
metadata_stop_script = format("{metadata_bin}/atlas_stop.py")

# metadata local directory structure
log_dir = config['configurations']['atlas-env']['metadata_log_dir']
conf_dir = status_params.conf_dir # "/etc/metadata/conf"
conf_file = status_params.conf_file

# service locations
hadoop_conf_dir = os.path.join(os.environ["HADOOP_HOME"], "conf") if 'HADOOP_HOME' in os.environ else '/etc/hadoop/conf'

# some commands may need to supply the JAAS location when running as atlas
atlas_jaas_file = format("{conf_dir}/atlas_jaas.conf")

# user and status
metadata_user = status_params.metadata_user
user_group = config['configurations']['cluster-env']['user_group']
pid_dir = status_params.pid_dir
pid_file = format("{pid_dir}/atlas.pid")

# metadata env
java64_home = config['hostLevelParams']['java_home']
env_sh_template = config['configurations']['atlas-env']['content']

# credential provider
credential_provider = format( "jceks://file@{conf_dir}/atlas-site.jceks")

# command line args
ssl_enabled = default("/configurations/application-properties/atlas.enableTLS", False)
http_port = default("/configurations/application-properties/atlas.server.http.port", 21000)
https_port = default("/configurations/application-properties/atlas.server.https.port", 21443)
if ssl_enabled:
  metadata_port = https_port
  metadata_protocol = 'https'
else:
  metadata_port = http_port
  metadata_protocol = 'http'

metadata_host = config['hostname']

# application properties
application_properties = dict(config['configurations']['application-properties'])
application_properties['atlas.server.bind.address'] = metadata_host

metadata_env_content = config['configurations']['atlas-env']['content']

metadata_opts = config['configurations']['atlas-env']['metadata_opts']
metadata_classpath = config['configurations']['atlas-env']['metadata_classpath']
data_dir = format("{stack_root}/current/atlas-server/data")
expanded_war_dir = os.environ['METADATA_EXPANDED_WEBAPP_DIR'] if 'METADATA_EXPANDED_WEBAPP_DIR' in os.environ else format("{stack_root}/current/atlas-server/server/webapp")

metadata_log4j_content = config['configurations']['atlas-log4j']['content']

atlas_log_level = config['configurations']['atlas-log4j']['atlas_log_level']
audit_log_level = config['configurations']['atlas-log4j']['audit_log_level']

# smoke test
smoke_test_user = config['configurations']['cluster-env']['smokeuser']
smoke_test_password = 'smoke'
smokeuser_principal =  config['configurations']['cluster-env']['smokeuser_principal_name']
smokeuser_keytab = config['configurations']['cluster-env']['smokeuser_keytab']

kinit_path_local = status_params.kinit_path_local

security_check_status_file = format('{log_dir}/security_check.status')
if security_enabled:
    smoke_cmd = format('curl --negotiate -u : -b ~/cookiejar.txt -c ~/cookiejar.txt -s -o /dev/null -w "%{{http_code}}" {metadata_protocol}://{metadata_host}:{metadata_port}/')
else:
    smoke_cmd = format('curl -s -o /dev/null -w "%{{http_code}}" {metadata_protocol}://{metadata_host}:{metadata_port}/')

# hbase
hbase_conf_dir = "/etc/hbase/conf"

atlas_search_backend = default("/configurations/application-properties/atlas.graph.index.search.backend", "")
search_backend_solr = atlas_search_backend.startswith('solr')

# logsearch solr
logsearch_solr_znode = default("/configurations/logsearch-solr-env/logsearch_solr_znode", None)
logsearch_solr_dir = '/usr/lib/ambari-logsearch-solr'
logsearch_solr_hosts = default("/clusterHostInfo/logsearch_solr_hosts", [])
logsearch_solr_replication_factor = 2 if len(logsearch_solr_hosts) > 1 else 1
atlas_solr_shards = default("/configurations/atlas-env/atlas_solr-shards", 1)
has_logsearch_solr = len(logsearch_solr_hosts) > 0

if has_logsearch_solr:
  logsearch_solr_user = config['configurations']['logsearch-solr-env']['logsearch_solr_user']
  logsearch_solr_group = config['configurations']['logsearch-solr-env']['logsearch_solr_group']

# zookeeper
zookeeper_hosts = config['clusterHostInfo']['zookeeper_hosts']
zookeeper_port = default('/configurations/zoo.cfg/clientPort', None)

# get comma separated lists of zookeeper hosts from clusterHostInfo
index = 0
zookeeper_quorum = ""
for host in zookeeper_hosts:
  zookeeper_host = host
  if zookeeper_port is not None:
    zookeeper_host = host + ":" + str(zookeeper_port)

  zookeeper_quorum += zookeeper_host
  index += 1
  if index < len(zookeeper_hosts):
    zookeeper_quorum += ","

# for create_hdfs_directory
hadoop_bin_dir = status_params.hadoop_bin_dir
namenode_host = set(default("/clusterHostInfo/namenode_host", []))
has_namenode = not len(namenode_host) == 0
hdfs_user = config['configurations']['hadoop-env']['hdfs_user'] if has_namenode else None
hdfs_user_keytab = config['configurations']['hadoop-env']['hdfs_user_keytab']  if has_namenode else None
hdfs_principal_name = config['configurations']['hadoop-env']['hdfs_principal_name'] if has_namenode else None
hdfs_site = config['configurations']['hdfs-site']
default_fs = config['configurations']['core-site']['fs.defaultFS']
dfs_type = default("/commandParams/dfs_type", "")

import functools
from resource_management.libraries.resources.hdfs_resource import HdfsResource
from resource_management.libraries.functions.get_not_managed_resources import get_not_managed_resources
#create partial functions with common arguments for every HdfsResource call
#to create hdfs directory we need to call params.HdfsResource in code

HdfsResource = functools.partial(
  HdfsResource,
  user = hdfs_user,
  hdfs_resource_ignore_file = "/var/lib/ambari-agent/data/.hdfs_resource_ignore",
  security_enabled = security_enabled,
  keytab = hdfs_user_keytab,
  kinit_path_local = kinit_path_local,
  hadoop_bin_dir = hadoop_bin_dir,
  hadoop_conf_dir = hadoop_conf_dir,
  principal_name = hdfs_principal_name,
  hdfs_site = hdfs_site,
  default_fs = default_fs,
  immutable_paths = get_not_managed_resources(),
  dfs_type = dfs_type
)

# Atlas Ranger plugin configurations
stack_supports_atlas_ranger_plugin = stack_version_formatted and check_stack_feature(StackFeature.ATLAS_RANGER_PLUGIN_SUPPORT, stack_version_formatted)
stack_supports_ranger_kerberos = stack_version_formatted and check_stack_feature(StackFeature.RANGER_KERBEROS_SUPPORT, stack_version_formatted)
retryAble = default("/commandParams/command_retry_enabled", False)

ranger_admin_hosts = default("/clusterHostInfo/ranger_admin_hosts", [])
has_ranger_admin = not len(ranger_admin_hosts) == 0
is_supported_atlas_ranger = config['configurations']['atlas-env']['is_supported_atlas_ranger']
xml_configurations_supported = config['configurations']['ranger-env']['xml_configurations_supported']
enable_ranger_atlas = False
metadata_server_host = atlas_hosts[0]
metadata_server_url = format('{metadata_protocol}://{metadata_server_host}:{metadata_port}')



if has_ranger_admin and is_supported_atlas_ranger:
  repo_name = str(config['clusterName']) + '_atlas'
  ssl_keystore_password = unicode(config['configurations']['ranger-atlas-policymgr-ssl']['xasecure.policymgr.clientssl.keystore.password'])
  ssl_truststore_password = unicode(config['configurations']['ranger-atlas-policymgr-ssl']['xasecure.policymgr.clientssl.truststore.password'])
  credential_file = format('/etc/ranger/{repo_name}/cred.jceks')
  xa_audit_hdfs_is_enabled = default('/configurations/ranger-atlas-audit/xasecure.audit.destination.hdfs', False)
  enable_ranger_atlas = config['configurations']['ranger-atlas-plugin-properties']['ranger-atlas-plugin-enabled']
  enable_ranger_atlas = not is_empty(enable_ranger_atlas) and enable_ranger_atlas.lower() == 'yes'
  policymgr_mgr_url = config['configurations']['admin-properties']['policymgr_external_url']

  downloaded_custom_connector = None
  driver_curl_source = None
  driver_curl_target = None

  ranger_env = config['configurations']['ranger-env']
  ranger_plugin_properties = config['configurations']['ranger-atlas-plugin-properties']

  ranger_atlas_audit = config['configurations']['ranger-atlas-audit']
  ranger_atlas_audit_attrs = config['configuration_attributes']['ranger-atlas-audit']
  ranger_atlas_security = config['configurations']['ranger-atlas-security']
  ranger_atlas_security_attrs = config['configuration_attributes']['ranger-atlas-security']
  ranger_atlas_policymgr_ssl = config['configurations']['ranger-atlas-policymgr-ssl']
  ranger_atlas_policymgr_ssl_attrs = config['configuration_attributes']['ranger-atlas-policymgr-ssl']

  policy_user = config['configurations']['ranger-atlas-plugin-properties']['policy_user']

  atlas_repository_configuration = {
    'username' : config['configurations']['ranger-atlas-plugin-properties']['REPOSITORY_CONFIG_USERNAME'],
    'password' : unicode(config['configurations']['ranger-atlas-plugin-properties']['REPOSITORY_CONFIG_PASSWORD']),
    'atlas.rest.address' : metadata_server_url,
    'commonNameForCertificate' : config['configurations']['ranger-atlas-plugin-properties']['common.name.for.certificate'],
    'ambari.service.check.user' : policy_user
  }
  if security_enabled:
    atlas_repository_configuration['policy.download.auth.users'] = metadata_user
    atlas_repository_configuration['tag.download.auth.users'] = metadata_user

  atlas_ranger_plugin_repo = {
    'isEnabled': 'true',
    'configs': atlas_repository_configuration,
    'description': 'atlas repo',
    'name': repo_name,
    'type': 'atlas',
    }
