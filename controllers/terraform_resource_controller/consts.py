import os

JOB_FINALIZER = 'easyaas.dev/job-finalizer'

WATCHED_RESOURCE_GROUP = os.environ.get('EASYAAS_WATCHED_RESOURCE_GROUP', 'easyaas.dev')
WATCHED_RESOURCE_NAME = os.environ.get('EASYAAS_WATCHED_RESOURCE_NAME', 'ephemeralnamespaces')

MANAGED_BY = '{}.{}'.format(WATCHED_RESOURCE_NAME, WATCHED_RESOURCE_GROUP)
EASYAAS_PREFIX = MANAGED_BY
