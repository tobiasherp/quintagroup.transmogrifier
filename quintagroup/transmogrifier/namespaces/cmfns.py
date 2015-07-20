"""
    CMF Marshall namespace is overrided here in order to fix
    LocalRolesAttribute class. It's not working in Marshall Product.
"""

from Products.Marshall.namespaces import cmfns as base


def safe_utf8(s):
    """ Return an utf-8 encoded string, or input, if it evaluates to False """
    if isinstance(s, unicode):
        return s.encode('utf-8')
    elif isinstance(s, str):
        return unicode(s, 'utf-8').encode('utf-8')
    else:
        return s


class LocalRolesAttribute(base.LocalRolesAttribute):

    def deserialize(self, instance, ns_data):
        values = ns_data.get(self.field_id)
        if not values:
            return
        for user_id, role in values:
            instance.manage_addLocalRoles(user_id, [role])


    def processXml(self, context, node):
        nsprefix = node.tag[:node.tag.find('}')+1]
        local_roles = node.findall(nsprefix+self.field_id)

        if len(local_roles) == 0:
            return

        data = context.getDataFor(self.namespace.xmlns)
        values = data.setdefault(self.field_id, [])

        for lrole in local_roles:
            values.append((lrole.get('user_id'), lrole.get('role')))

        return True

    def get(self, instance):
        """ overide local roles reader due to rare usecase of non-unicode strings in migrated Plone instances."""
        lr = getattr(instance, '__ac_local_roles__', {})
        if not lr:
            return {}
        fixed_lr = {}
        for user, roles in lr.items():
            user = safe_utf8(user)
            fixed_lr[user] = [safe_utf8(role) for role in roles]
        return fixed_lr


class WorkflowAttribute(base.WorkflowAttribute):

    def get(self, instance):
        """  """
        history = super(WorkflowAttribute, self).get(instance)

        fixed_history = {}
	for workflow, actions in history.items():
           fixed_history[workflow] = tuple(
		[{'action': action['action'],
                  'review_state': safe_utf8(action['review_state']),
                  'actor': safe_utf8(action['actor']),
                  'comments': safe_utf8(action['comments']),
                  'time': action['time']} for action in actions])
        return fixed_history


class CMF(base.CMF):

    attributes = (
        base.TypeAttribute('type'),
        WorkflowAttribute('workflow_history'),
        LocalRolesAttribute('security','local_role'),
        )
