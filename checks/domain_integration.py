"""Bounded combined offline construction/trace checks for the integrated domain packs."""
import argparse
import hashlib
import json
import os
from pathlib import Path

from taxo import memory
from taxo.bootstrap import construct
from taxo.core.domain import load
from taxo.core.rules import run_rules
from taxo.core.schemas import Listing, Node, Status


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--workspace', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    a = ap.parse_args()
    if a.output.exists():
        raise FileExistsError('choose a fresh output directory')
    a.output.mkdir(parents=True)
    reports, asins = {}, {}
    for name in ('clothing', 'toys', 'games'):
        folder = 'clothing' if name == 'clothing' else 'games'
        path = a.workspace / f'data/different_lines/silver/{folder}/{folder}_listings.parquet'
        os.environ[f'TAXO_{name.upper()}_LISTINGS'] = str(path)
        d = load(name)
        assert len(list(d.listings(2))) == 2 and not list(d.nodes())  # smoke before construction
        all_listings = list(d.listings())
        asins[name] = {l.fields.get('source_listing_id') or (l.fields.get('raw') or {}).get('source_listing_id')
                       or (l.fields.get('source_raw') or {}).get('asin') for l in all_listings}
        assert None not in asins[name]
        out = a.output / name
        result = construct(name, 64, out)
        manifest = json.loads((out / 'run-manifest.json').read_text())
        assert manifest['status'] == 'completed' and manifest['source_files']
        assert result['input_rows'] == 64 and result['agent_calls'] == 0 and result['accuracy'] is None
        assert result['raw_identity_tokens_preserved'] and result['unscoped_rows'] == 0
        for artifact in manifest['artifacts']:
            assert hashlib.sha256(Path(artifact['path']).read_bytes()).hexdigest() == artifact['sha256']
        nodes = {r['id']: r for r in map(json.loads, (out/'nodes.jsonl').read_text().splitlines())}
        placements = list(map(json.loads, (out/'placements.jsonl').read_text().splitlines()))
        for item in placements:
            assert item['status'] == 'proposal' and (item['node_id'] is None or item['node_id'] in nodes)
            if item['node_id'] and len(item['path']) > 1 and item['identity_partition']:
                assert nodes[item['node_id']]['fields'][name] == item['identity_partition']
        assert all(n['fields']['status'] == 'proposal' and (not n['parent_id'] or n['parent_id'] in nodes) for n in nodes.values())
        events = list(map(json.loads, (out/'rule-events.jsonl').read_text().splitlines()))
        if name == 'games':
            assert result['candidate_facts_hook'] == 'domains.games.checks' and result['identity_partitions'] > 1
            assert all('games' in e['facts'] for e in events)
            assert all(r['status'] == 'shadow' for r in result['evaluator_rules'])
        assert not memory.agentic_for(name)
        reports[name] = {'metrics':result,'manifest':str((out/'run-manifest.json').resolve()),
                         'accepted_source_rows_profiled':len(all_listings),'artifact_hashes_verified':True}
    assert not asins['toys'] & asins['games'], 'toys/games source membership conflict requires review'
    # Exercise imported toys checks through shared dispatch while actual proposals stay inert.
    l = Listing(id='synthetic:toy', domain='toys', title='Example Figure Stand')
    n = Node(id='synthetic:node', domain='toys', name='Example Figure', fields={'identity_identifiers':{'set_number':'999'},'offering_kind':'complete_toy'})
    rules = memory.rules_for('toys')
    assert not run_rules(rules,l,n,{n.id:n}).decided
    shadow = [r.model_copy(update={'status':Status.SHADOW}) for r in rules]
    outcome = run_rules(shadow,l,n,{n.id:n})
    assert not outcome.decided and {'ty-model-set-number','ty-accessory-variant-evidence'} <= {f.check for f in outcome.shadow}
    try:
        construct('clothing',0,a.output/'failure-record')
        raise AssertionError('invalid bound accepted')
    except ValueError:
        failure = json.loads((a.output/'failure-record/run-manifest.json').read_text())
        assert failure['status'] == 'failed' and (a.output/'failure-record/errors.jsonl').is_file()
    report = {'status':'PASS','domains':reports,'toys_games_asin_overlap':0,
              'logging_failure_path':'PASS','toys_shared_shadow_checks':'PASS','model_calls':0,'gold_loaded':False,
              'limitations':['Engineering checks and exploratory source screens are not human gold or accuracy.',
                             'No full taxonomy, validator/human review or model traces were produced.']}
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':'PASS','report':str(a.output/'report.json')}))


if __name__ == '__main__':
    main()
