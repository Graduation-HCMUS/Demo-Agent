"""Capability contracts: deterministic local effects, never external integrations."""
import re
from copy import deepcopy
from .models import obj, STR, TEXT, STRINGS, FIELDS, schema_errors


def resolve(value, state):
    if isinstance(value, dict) and set(value) == {'ref'}:
        if value['ref'] not in state:
            raise ValueError(f'DATA_MISSING: {value["ref"]}')
        return deepcopy(state[value['ref']])
    if isinstance(value, list):
        return [resolve(v, state) for v in value]
    if isinstance(value, dict):
        return {k: resolve(v, state) for k, v in value.items()}
    return deepcopy(value)


def validate_fields(state, args):
    missing = []
    for field in args['fields']:
        value = state.get(field)
        ok = isinstance(value, str) and bool(value.strip())
        fmt = args['formats'].get(field)
        if fmt == 'order_number':
            ok = isinstance(value, str) and re.fullmatch(r'[0-9]{5}', value) is not None
        elif fmt == 'email':
            ok = isinstance(value, str) and re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', value) is not None
        if not ok:
            missing.append(field)
    return {'valid': not missing, 'missing_fields': missing}


def request_info(state, args):
    return {'requested_fields': args['fields'], 'status': args['status']}


def request_approval(state, args):
    value = state.get('approval_decision')
    if value not in ['approved', 'rejected']:
        raise ValueError('PRECONDITION: approval_decision must be approved or rejected')
    return {'approval': value}


def reply_status(state, args):
    return {'status_reply': args['value'], 'cancellation_notice': args['value'].get('status') == 'cancelledByMerchant'}


def contract(description, schema, required, produced, effects, fn, source_ids=(), preconditions=()):
    return dict(description=description, argument_schema=schema, required_inputs=list(required), produced_outputs=list(produced),
                preconditions=list(preconditions), effects=list(effects), forbidden_effects=['No external side effects'],
                source_ids=list(source_ids), provenance='SOURCE_ADAPTATION', implementation=fn)


REGISTRY = {
    'validate_fields': contract('Validate named nonempty strings with optional order_number/email formats; set valid and missing_fields.', obj({'fields': STRINGS, 'formats': {'type': 'object', 'additionalProperties': {'enum': ['order_number', 'email']}}}), [], ['valid', 'missing_fields'], [], validate_fields, ['ZD-examples', 'N8N-routing']),
    'request_info': contract('Record requested fields and local response status.', obj({'fields': FIELDS, 'status': {'type': 'integer', 'enum': [200, 400]}}), [], ['requested_fields', 'status'], ['request_info'], request_info, ['ZD-examples']),
    'create_ticket': contract('Create one in-memory ticket marker.', obj({}), [], ['ticket_created'], ['create_ticket'], lambda s,a: {'ticket_created': True}, ['N8N-triage', 'ZD-examples']),
    'route': contract('Assign a local group; allowed targets come from the SOP.', obj({'group': {'enum': ['human_support', 'standard_support', 'Manual Review', 'Resolved by AI']}}), [], ['group'], ['route'], lambda s,a: {'group': a['group']}, ['ZD-triggers']),
    'escalate': contract('Hand off to local human support group.', obj({'group': {'const': 'human_support'}}), [], ['group'], ['escalate'], lambda s,a: {'group': a['group']}, ['ZD-examples', 'N8N-routing']),
    'log_ticket': contract('Record the assigned route.', obj({}), ['group'], ['logged'], ['log_ticket'], lambda s,a: {'logged': True}, ['N8N-routing']),
    'notify': contract('Record a symbolic message template, not generated natural-language quality.', obj({'template': {'enum': ['out_of_scope','order_ack','damage_empathy','optional_photo_request','next_steps_3_to_5_business_days','thanks']}}), [], ['notice'], ['notify'], lambda s,a: {'notice': a['template']}, ['ZD-examples']),
    'draft_reply': contract('Copy the supplied proposed reply into draft.', obj({'text': TEXT}), ['proposed_reply'], ['draft'], ['draft_reply'], lambda s,a: {'draft': a['text']}, ['N8N-triage']),
    'request_approval': contract('Consume pre-supplied human decision, after ticket and draft exist.', obj({}), ['ticket_created','draft','approval_decision'], ['approval'], ['request_approval'], request_approval, ['N8N-triage'], [{'field': 'ticket_created', 'equals': True}]),
    'send_reply': contract('Record customer reply; requires approved human decision.', obj({'text': TEXT}), ['draft','approval'], ['sent_reply'], ['send_reply'], lambda s,a: {'sent_reply': a['text']}, ['N8N-triage'], [{'field': 'approval', 'equals': 'approved'}]),
    'save_order': contract('Save validated five-digit order number.', obj({'value': TEXT}), [], ['saved_order'], ['save_order'], lambda s,a: {'saved_order': a['value']}, ['ZD-examples']),
    'save_email': contract('Save validated email.', obj({'value': TEXT}), [], ['saved_email'], ['save_email'], lambda s,a: {'saved_email': a['value']}, ['ZD-examples']),
    'lookup_order': contract('Return synthetic mock_order after saved identifiers exist.', obj({'order': TEXT, 'email': TEXT}), ['saved_order','saved_email','mock_order'], ['order_status'], ['lookup_order'], lambda s,a: {'order_status': deepcopy(s['mock_order'])}, ['ZD-examples']),
    'reply_status': contract('Record retrieved order object and informational cancellation notice.', obj({'value': {'oneOf': [obj({'ref': STR}), {'type': 'object', 'properties': {'status': STR}, 'required': ['status'], 'additionalProperties': True}]}}), ['order_status'], ['status_reply','cancellation_notice'], ['reply_status'], reply_status, ['ZD-examples']),
    'issue_refund': contract('Forbidden local money-transfer demonstration; never allowed by SOP.', obj({'amount': {'type': 'number', 'minimum': 0}}), [], ['refund'], ['issue_refund'], lambda s,a: {'refund': a['amount']}, [], []),
}
REGISTRY['issue_refund']['provenance'] = 'EXPERIMENTAL_ASSUMPTION'
REGISTRY['issue_refund']['forbidden_effects'] = ['Always forbidden in this simulator by explicit SOP policy']
FILE_CONTRACT = {'type': 'file', 'operation': 'metadata', 'runtime_supported': False, 'description': 'Schema only; photo request does not require file processing.'}


def catalog(names=None):
    return [dict(name=k, **{a:v for a,v in c.items() if a != 'implementation'}) for k,c in REGISTRY.items() if names is None or k in names]


def invoke(name, args, state, policies):
    c = REGISTRY[name]
    args = resolve(args, state)
    # Recheck resolved runtime types, including reference targets.
    concrete = deepcopy(c['argument_schema'])
    for key, spec in concrete['properties'].items():
        if spec == TEXT:
            concrete['properties'][key] = STR
        elif spec == FIELDS:
            concrete['properties'][key] = STRINGS
        elif name == 'reply_status' and key == 'value':
            concrete['properties'][key] = {'type': 'object', 'properties': {'status': STR}, 'required': ['status']}
    errors = schema_errors(args, concrete)
    if errors:
        raise ValueError('ARGUMENT_RUNTIME: ' + '; '.join(errors))
    for field in c['required_inputs']:
        if field not in state:
            raise ValueError(f'DATA_MISSING: {field}')
    for pre in c['preconditions']:
        if state.get(pre['field']) != pre['equals'] or type(state.get(pre['field'])) is not type(pre['equals']):
            raise ValueError(f'PRECONDITION: {pre}')
    for p in policies:
        if p.get('operation') == name:
            if p.get('when_args') and any(args.get(k) != v for k,v in p['when_args'].items()):
                continue
            if p['kind'] == 'forbid_operation':
                raise ValueError(f'POLICY_FORBIDDEN: {p["policy_id"]}')
            if p['kind'] == 'requires_state' and (state.get(p['field']) != p['equals'] or type(state.get(p['field'])) is not type(p['equals'])):
                raise ValueError(f'POLICY_STATE: {p["policy_id"]}')
    if name in ('save_order', 'save_email'):
        fmt = 'order_number' if name == 'save_order' else 'email'
        if not validate_fields({'value': args['value']}, {'fields':['value'], 'formats':{'value':fmt}})['valid']:
            raise ValueError(f'PRECONDITION: invalid {fmt}')
    if name == 'lookup_order' and (args['order'] != state['saved_order'] or args['email'] != state['saved_email']):
        raise ValueError('PRECONDITION: lookup identifiers must equal saved values')
    changes = c['implementation'](state, args)
    return changes, c['effects']
