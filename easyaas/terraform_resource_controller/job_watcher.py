# Watch terragrunt jobs
import kubernetes
import kopf

from easyaas.helpers import current_timestamp
from .consts import JOB_FINALIZER, WATCHED_RESOURCE_NAME, MANAGED_BY

class NoOwnerException(RuntimeError):
    pass

@kopf.on.event('batch/v1', 'job', labels={'managed-by': MANAGED_BY})
def watch_job(logger, meta: kopf.Meta, namespace, name, status: kopf.Status, **_):
    try:
        owner = get_owner(meta)
    except NoOwnerException:
        return
    crdapi = kubernetes.client.CustomObjectsApi()
    (group, version) = owner.get('apiVersion', "").split("/")

    status = dict(status)

    if meta.deletion_timestamp is not None:
        # If the job is being deleted, remove it from the status
        job_status = {
            name: {
                'deleted': True
            }
        }
        # Remove the finalizer
        api = kubernetes.client.BatchV1Api()
        finalizer_index = meta.get('finalizers', []).index(JOB_FINALIZER)
        logger.info('finalizer index: {}'.format(finalizer_index))
        try:
            api.patch_namespaced_job(
                name=name,
                namespace=namespace,
                body=[{
                    'op': 'remove',
                    'path': '/metadata/finalizers/{}'.format(finalizer_index)
                }]
            )
        except kubernetes.client.exceptions.ApiException:
            pass
    else:
        reason = None
        message = None
        for cond in status.get('conditions', []):
            if cond.get('type', '') == 'Failed' and cond.get('status', '') == "True":
                reason = cond.get('reason', '')
                message = cond.get('message', '')
        job_status = {
            name: {
                'job': '{}/{}'.format(namespace, name),
                'active': status.get('active', 0),
                'failed': True if status.get('failed', 0) > 0 else False,
                'reason': reason,
                'message': message,
            }
        }

    
    job_status[name]['lastTransitionTime'] = current_timestamp()

    try:
        crdapi.patch_namespaced_custom_object_status(
            group=group,
            version=version,
            plural=WATCHED_RESOURCE_NAME,
            name=owner['name'],
            namespace=namespace,
            body={
                'status': {
                    'jobs': job_status
                }
            }
        )
    except kubernetes.client.exceptions.ApiException as e:
        if e.status == 404:
            # This can happen if the parent gets deleted
            # and the garbage collection deletes the child jobs
            # It's safe to ignore it
            return
        
def get_owner(meta):
    # Get the owner resource
    owner_refs = meta.get('ownerReferences', {})
    ctrl_owners = [ owner for owner in owner_refs if owner.get('controller', False) == True ]
    if len(ctrl_owners) != 1:
        raise NoOwnerException(f"No Controller owner found on {meta['namespace']}/{meta['name']}, skipping")
    
    return ctrl_owners[0]
