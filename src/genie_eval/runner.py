"""A bounded, deterministic, single-ticket DAG interpreter."""
from copy import deepcopy
from .catalog import invoke
from .validators import validate


def condition(config, state):
    value=state.get(config['field']);expected=config['value'];op=config['operator']
    if op=='exists':return config['field'] in state and value is not None
    if op=='eq':return type(value) is type(expected) and value==expected
    if op=='ne':return not (type(value) is type(expected) and value==expected)
    if op=='gte':
        if type(value) not in (int,float) or type(expected) not in (int,float):
            raise ValueError('CONDITION_TYPE: gte requires numbers')
        return value>=expected
    raise ValueError(f'CONDITION_OPERATOR: {op}')


def run(workflow, ticket, sop, max_steps=128):
    findings=validate(workflow,sop)
    if not isinstance(ticket,dict):
        return dict(status='INVALID',state={'effects':[],'messages':[]},trace=[],errors=[dict(code='INPUT_STATE',category='contract',node_id=None,message='Ticket state must be a JSON object')])
    state=deepcopy(ticket);state['effects']=[];state['messages']=[]
    if findings:
        return dict(status='INVALID',state=state,trace=[],errors=findings)
    nodes={n['id']:n for n in workflow['nodes']}
    id=next(n['id'] for n in nodes.values() if n['type']=='input');trace=[]
    for step in range(max_steps):
        n=nodes[id];before=deepcopy(state);conf=n['config'];selected=None;error=None
        try:
            if n['type']=='custom':
                changes,effects=invoke(conf['operation'],conf['args'],state,sop.get('forbidden_actions',[]))
                state.update(changes);state['effects'].extend(effects)
                if conf['operation']=='notify':state['messages'].append(conf['args']['template'])
            elif n['type']=='condition':
                port='true' if condition(conf,state) else 'false'
            elif n['type']=='file':
                raise ValueError('FILE_UNSUPPORTED')
            if n['type']!='output':
                selected=next(e for e in workflow['edges'] if e['source']==id and e['port']==(port if n['type']=='condition' else 'next'))
        except (ValueError,KeyError,TypeError,StopIteration) as exc:
            error=str(exc) or type(exc).__name__
        trace.append(dict(step_index=step,node_id=id,node_type=n['type'],operation=conf.get('operation',n['type']),
                          condition=deepcopy(conf) if n['type']=='condition' else None,input_snapshot=before,state_changes={k:deepcopy(v) for k,v in state.items() if k not in before or before[k]!=v},
                          selected_edge=selected,error=error))
        if error:return dict(status='ERROR',state=state,trace=trace,errors=[dict(code=error.split(':')[0],node_id=id,message=error)])
        if n['type']=='output':return dict(status='OK',state=state,trace=trace,errors=[])
        id=selected['target']
    return dict(status='ERROR',state=state,trace=trace,errors=[dict(code='STEP_LIMIT',node_id=id,message='Execution limit reached')])
