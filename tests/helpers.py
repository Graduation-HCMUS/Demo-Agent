"""Transport doubles only: their responses never appear as real inference evidence."""
import json
from copy import deepcopy
from genie_eval.models import get_case,sop_for,reference


def context(id='approval-en'):
    c=get_case(id);return c,sop_for(c),reference(c)


class FakeOllama:
    def __init__(self,workflow=None,responses=None,installed=True):
        self.workflow=workflow or context()[2];self.responses=list(responses or []);self.installed=installed;self.chat_calls=[];self.probes=0
    def __call__(self,host,path,payload=None,timeout=5):
        if path=='/api/tags':
            self.probes+=1
            return {'models':[dict(name=n,digest='test-digest',size=1) for n in ['test:model','test:planner','test:detail','test:judge']] if self.installed else []}
        assert path=='/api/chat';self.chat_calls.append(deepcopy(payload))
        if self.responses:
            value=self.responses.pop(0)
            if isinstance(value,Exception):raise value
        elif 'items' in payload['format'].get('properties',{}):
            content=payload['messages'][0]['content'];data=json.loads(content.split('\n',1)[1]);item=payload['format']['properties']['items']['items']['properties']
            if 'business_intent' in item:
                value={'items':[dict(id='stage-1',business_intent='Follow the requested process',required_inputs=[],expected_outputs=['ticket'],dependencies=[],candidate_capabilities=[c['name'] for c in data['capabilities']] if data['phase']=='capability_mapping' else ['create_ticket'],requirement_ids=[r['requirement_id'] for r in data['requirements']])]}
            else:
                value={'items':[dict(requirement_id=r['requirement_id'],verdict='UNKNOWN',node_ids=[],edge_refs=[],trace_refs=[],reason='No independent natural-language evidence',uncertainty=1,failure_category='insufficient_evidence') for r in data['checklist']]}
        else:value=self.workflow
        raw=value if isinstance(value,str) else json.dumps(value)
        return dict(message=dict(content=raw,thinking='SECRET_REASONING_MUST_NOT_BE_SAVED'),prompt_eval_count=111,eval_count=22,total_duration=1234,done_reason='stop')
