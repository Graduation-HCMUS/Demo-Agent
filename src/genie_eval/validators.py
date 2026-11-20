"""Stable structural, contract and policy findings; path-aware must-data analysis."""
from collections import deque
from .models import WORKFLOW_SCHEMA, schema_errors
from .catalog import REGISTRY


def issue(code, category, node, message):
    return dict(code=code, category=category, node_id=node, message=message)


def references(value):
    if isinstance(value, dict):
        if set(value) == {'ref'}:
            return {value['ref']}
        return set().union(*(references(v) for v in value.values())) if value else set()
    if isinstance(value, list):
        return set().union(*(references(v) for v in value)) if value else set()
    return set()


def validate(workflow, sop, contracts=True):
    errors = [issue('SCHEMA', 'structure', None, e) for e in schema_errors(workflow, WORKFLOW_SCHEMA)]
    if errors:
        return errors
    nodes = {n['id']: n for n in workflow['nodes']}
    if len(nodes) != len(workflow['nodes']):
        return [issue('DUPLICATE_ID','structure',None,'Node IDs must be unique')]
    outgoing = {id: [] for id in nodes}
    incoming = {id: [] for id in nodes}
    for e in workflow['edges']:
        if e['source'] not in nodes or e['target'] not in nodes:
            errors.append(issue('EDGE_ENDPOINT','structure',e['source'],'Unknown edge endpoint'))
        else:
            outgoing[e['source']].append(e)
            incoming[e['target']].append(e)
    starts = [n['id'] for n in nodes.values() if n['type']=='input']
    if len(starts) != 1:
        errors.append(issue('INPUT_COUNT','structure',None,'Exactly one input required'))
    if not any(n['type']=='output' for n in nodes.values()):
        errors.append(issue('OUTPUT_MISSING','structure',None,'At least one output required'))
    for id,n in nodes.items():
        ports = sorted(e['port'] for e in outgoing[id])
        wanted = ['false','true'] if n['type']=='condition' else ([] if n['type']=='output' else ['next'])
        if ports != wanted:
            errors.append(issue('EDGE_PORTS','structure',id,f'Expected outgoing ports {wanted}; got {ports}'))
        if n['type']=='input' and incoming[id]:
            errors.append(issue('INPUT_INCOMING','structure',id,'Input cannot have incoming edges'))
    degree={id:len(v) for id,v in incoming.items()}
    queue=deque(sorted(id for id,v in degree.items() if v==0)); order=[]
    while queue:
        id=queue.popleft();order.append(id)
        for e in outgoing[id]:
            degree[e['target']]-=1
            if degree[e['target']]==0:queue.append(e['target'])
    if len(order)!=len(nodes):errors.append(issue('CYCLE','structure',None,'DAG required'))
    if len(starts)==1:
        seen=set();stack=starts[:]
        while stack:
            id=stack.pop()
            if id not in seen:
                seen.add(id);stack += [e['target'] for e in outgoing[id]]
        errors += [issue('UNREACHABLE','structure',id,'Node unreachable from input') for id in nodes.keys()-seen]
    if errors or not contracts:
        return errors
    # Every predecessor must provide a value. Facts track supported equality guards,
    # rather than treating operation-name presence as proof of preconditions.
    available={};facts={}
    initial=set(sop['inputs']) | {'effects','messages'}
    for id in order:
        n=nodes[id]; conf=n['config']; pred=incoming[id]
        avs=[];fcs=[]
        for e in pred:
            parent=nodes[e['source']]; pf=set(facts[e['source']]);pc=parent['config']
            if parent['type']=='condition' and pc['operator']=='eq':
                value=pc['value']
                if e['port']=='true':pf.add((pc['field'],repr(value)))
                elif type(value) is bool:pf.add((pc['field'],repr(not value)))
            avs.append(available[e['source']]);fcs.append(pf)
        av=set.intersection(*avs) if avs else set(initial)
        fs=set.intersection(*fcs) if fcs else set()
        reads=set();produced=set()
        if n['type']=='condition':
            reads.add(conf['field'])
            if conf['operator']=='gte' and type(conf['value']) not in (int,float):
                errors.append(issue('CONDITION_ARGUMENT','contract',id,'gte requires a numeric value'))
        elif n['type']=='file':
            errors.append(issue('FILE_UNSUPPORTED','contract',id,'Metadata schema supported; file runtime unsupported'))
        elif n['type']=='custom':
            name=conf['operation'];args=conf['args'];c=REGISTRY.get(name)
            if c is None:
                errors.append(issue('UNKNOWN_OPERATION','contract',id,f'Unregistered operation {name}'))
            else:
                errors += [issue('ARGUMENT_SCHEMA','contract',id,e) for e in schema_errors(args,c['argument_schema'])]
                reads |= references(args) | set(c['required_inputs'])
                if name=='validate_fields' and isinstance(args.get('fields'),list):
                    reads |= set(args['fields'])
                    if isinstance(args.get('formats'),dict) and set(args['formats'])-set(args['fields']):
                        errors.append(issue('FORMAT_FIELD','contract',id,'Format keys must occur in fields'))
                produced |= set(c['produced_outputs'])
                for p in c['preconditions']:
                    if (p['field'],repr(p['equals'])) not in fs:
                        errors.append(issue('PRECONDITION_UNPROVEN','contract',id,f'Guard not established on every path: {p}'))
                for p in sop.get('forbidden_actions',[]):
                    if p.get('operation')!=name:continue
                    if p.get('when_args') and any(args.get(k)!=v for k,v in p['when_args'].items()):continue
                    if p['kind']=='forbid_operation':
                        errors.append(issue('POLICY_FORBIDDEN','policy',id,p['policy_id']))
                    elif p['kind']=='requires_state' and (p['field'],repr(p['equals'])) not in fs:
                        errors.append(issue('POLICY_GUARD','policy',id,p['policy_id']))
                fs={f for f in fs if f[0] not in produced}
                if name=='create_ticket':fs.add(('ticket_created',repr(True)))
        errors += [issue('DATA_DEPENDENCY','contract',id,f'Value {field!r} not available on every incoming path') for field in sorted(reads-av)]
        available[id]=av|produced;facts[id]=fs
    return errors
