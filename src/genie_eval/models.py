"""Portable JSON contracts and a validator for the exact schema subset used here."""
import hashlib
import json
import os
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def reject_constant(value):
    raise ValueError(f'Invalid JSON constant: {value}')


def parse_json(text):
    return json.loads(text,parse_constant=reject_constant)


def load(path):
    return parse_json((ROOT / path).read_text(encoding='utf-8'))

def save(path, value):
    path = Path(path)
    if not path.is_absolute():
        path = ROOT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    content=json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n'
    temporary=None
    try:
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=path.parent,delete=False) as handle:
            temporary=handle.name;handle.write(content)
        os.replace(temporary,path)
    finally:
        if temporary and os.path.exists(temporary):os.unlink(temporary)
    return str(path)

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()

def obj(properties, required=None):
    return {'type': 'object', 'properties': properties, 'required': list(properties) if required is None else required, 'additionalProperties': False}

STR = {'type': 'string', 'minLength': 1}
REF = obj({'ref': STR})
TEXT = {'oneOf': [STR, REF]}
STRINGS = {'type': 'array', 'items': STR, 'minItems': 1, 'maxItems': 32}
FIELDS = {'oneOf': [STRINGS, REF]}

def node_schema(kind, config):
    return obj({'id': STR, 'type': {'const': kind}, 'config': config})

WORKFLOW_SCHEMA = obj({
    'schema_version': {'const': '1.0'}, 'workflow_id': STR, 'name': STR,
    'nodes': {'type': 'array', 'minItems': 2, 'maxItems': 128, 'items': {'oneOf': [
        node_schema('input', obj({})), node_schema('output', obj({})),
        node_schema('condition', obj({'field': STR, 'operator': {'enum': ['eq', 'ne', 'exists', 'gte']}, 'value': {'type': ['string', 'number', 'boolean', 'null']}})),
        node_schema('custom', obj({'operation': STR, 'args': {'type': 'object'}})),
        node_schema('file', obj({'operation': {'const': 'metadata'}, 'name': STR, 'media_type': STR, 'size_bytes': {'type': 'integer', 'minimum': 0}}))]}},
    'edges': {'type': 'array', 'minItems': 1, 'maxItems': 256, 'items': obj({'source': STR, 'target': STR, 'port': {'enum': ['next', 'true', 'false']}})}
})

def schema_errors(value, schema, path='$'):
    """Not a general JSON Schema engine. Supports the keywords in our exported schemas."""
    errors = []
    if 'oneOf' in schema:
        if sum(not schema_errors(value, choice, path) for choice in schema['oneOf']) != 1:
            return [f'{path}: must match exactly one allowed shape']
    if 'const' in schema and (value != schema['const'] or type(value) is not type(schema['const'])):
        errors.append(f'{path}: expected constant {schema["const"]!r}')
    if 'enum' in schema and not any(value == x and type(value) is type(x) for x in schema['enum']):
        errors.append(f'{path}: value outside enum')
    kinds = schema.get('type', [])
    kinds = [kinds] if isinstance(kinds, str) else kinds
    checks = {'object': lambda x: isinstance(x, dict), 'array': lambda x: isinstance(x, list),
              'string': lambda x: isinstance(x, str), 'boolean': lambda x: type(x) is bool,
              'integer': lambda x: type(x) is int, 'number': lambda x: type(x) in (int, float), 'null': lambda x: x is None}
    if kinds and not any(checks[k](value) for k in kinds):
        return errors + [f'{path}: expected {kinds}']
    if isinstance(value, dict):
        props = schema.get('properties', {})
        errors += [f'{path}.{k}: required' for k in schema.get('required', []) if k not in value]
        for k, v in value.items():
            if k in props:
                errors += schema_errors(v, props[k], f'{path}.{k}')
            elif schema.get('additionalProperties') is False:
                errors.append(f'{path}.{k}: additional property')
            elif isinstance(schema.get('additionalProperties'), dict):
                errors += schema_errors(v, schema['additionalProperties'], f'{path}.{k}')
    if isinstance(value, list):
        if len(value) < schema.get('minItems', 0) or len(value) > schema.get('maxItems', float('inf')):
            errors.append(f'{path}: invalid array length')
        for i, v in enumerate(value):
            errors += schema_errors(v, schema.get('items', {}), f'{path}[{i}]')
    if isinstance(value, str) and len(value) < schema.get('minLength', 0):
        errors.append(f'{path}: string too short')
    if type(value) in (int, float) and not schema.get('minimum', float('-inf')) <= value <= schema.get('maximum', float('inf')):
        errors.append(f'{path}: outside numeric bounds')
    return errors

def cases():
    result = []
    prompts = load('data/prompts.json')
    for p in sorted((ROOT / 'data/cases').glob('*.json')):
        case = json.loads(p.read_text())
        case['user_request'] = prompts[case['prompt_id']]
        result.append(case)
    return result

def get_case(case_id):
    for case in cases():
        if case['case_id'] == case_id:
            return case
    raise ValueError(f'Unknown case {case_id!r}; use list-cases')

def sop_for(case):
    return load(f'data/sops/{case["sop_id"]}.json')

def reference(case):
    return load(f'data/reference-workflows/{case["sop_id"]}.json')

def oracle_integrity():
    lock = load('data/oracle-lock.json')
    errors = []
    for path, expected in lock['sha256'].items():
        if hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != expected:
            errors.append(path)
    return {'verdict': 'FAIL' if errors else 'PASS', 'changed_files': errors, 'lock_sha256': digest(lock)}
