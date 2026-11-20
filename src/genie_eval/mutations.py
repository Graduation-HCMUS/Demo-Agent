"""Controlled edits to independently confirmed references; labels predate evaluation."""
from copy import deepcopy


def variants(workflow,case):
    result=[]
    def add(kind,description,change,valid=False):
        w=deepcopy(workflow);responsible=change(w);w['workflow_id']+='--'+kind
        result.append(dict(mutation_id=kind,introduced_error=description,expected_valid=valid,responsible=responsible,workflow=w))
    def first_condition(w):return next(n for n in w['nodes'] if n['type']=='condition')
    def swap(w):
        id=first_condition(w)['id']
        for e in w['edges']:
            if e['source']==id:e['port']='false' if e['port']=='true' else 'true'
        return [id]
    add('swapped_branches','Swap true and false destinations, preserving all operation keywords.',swap)
    def missing(w):
        desired={'intake':'create_ticket','routing':'log_ticket','approval':'send_reply','order':'reply_status','damage':'create_ticket'}[case['sop_id']]
        n=next(n for n in w['nodes'] if n['config'].get('operation')==desired)
        n['config']={'operation':'notify','args':{'template':'thanks'}};return [n['id']]
    add('missing_action','Replace a required effect with a harmless symbolic notification.',missing)
    def badarg(w):
        n=next(n for n in w['nodes'] if n['type']=='custom');n['config']['args']['unexpected']=True;return [n['id']]
    add('incorrect_arguments','Add an unsupported argument to a registered operation.',badarg)
    if case['sop_id'] in ['approval','routing']:
        def target(w):
            n=next(n for n in w['nodes'] if n['config'].get('operation')=='route');n['config']['args']['group']='human_support';return [n['id']]
        add('incorrect_routing_target','Use a registered but business-incorrect routing group.',target)
    def ordering(w):
        ops={'intake':('validate','create'),'routing':('human','log'),'approval':('ask','send'),'order':('lookup','reply'),'damage':('photo','create')}[case['sop_id']]
        a,b=[next(n for n in w['nodes'] if n['id']==id) for id in ops]
        a['config'],b['config']=b['config'],a['config'];return list(ops)
    add('invalid_ordering','Swap two action configurations so required causal ordering is violated.',ordering)
    def insert(w,n):
        # Intercept a terminal edge; a bad effect remains reachable, without a cycle.
        e=next(e for e in w['edges'] if e['target']=='out');old=e['target'];e['target']=n['id'];w['nodes'].append(n);w['edges'].append(dict(source=n['id'],target=old,port='next'));return [n['id']]
    add('forbidden_action','Insert a locally forbidden money-transfer effect; it is never authorized by these SOPs.',lambda w:insert(w,dict(id='forbidden',type='custom',config=dict(operation='issue_refund',args=dict(amount=10)))))
    add('invalid_data_dependency','Read a state field that no input or predecessor produces.',lambda w:insert(w,dict(id='missing_dependency',type='custom',config=dict(operation='request_info',args=dict(fields={'ref':'never_produced'},status=200)))))
    def equivalent(w):
        e=next(e for e in w['edges'] if e['source']=='in');target=e['target'];e['target']='identity_branch'
        w['nodes'].append(dict(id='identity_branch',type='condition',config=dict(field=next(iter(case['input_fixtures'][0]['input'])),operator='exists',value=True)))
        w['edges'] += [dict(source='identity_branch',target=target,port=p) for p in ['true','false']];return ['identity_branch']
    add('equivalent_graph','Insert a redundant branch whose two outcomes join the same successor.',equivalent,True)
    if case['sop_id']=='intake':
        def missing_field(w):
            n=next(n for n in w['nodes'] if n['config'].get('operation')=='validate_fields');n['config']['args']['fields']=['email'];return [n['id']]
        add('missing_field_metamorphic','Omit message validation; primary fixtures miss this defect, independent message-added pair exposes it.',missing_field)
    return result
