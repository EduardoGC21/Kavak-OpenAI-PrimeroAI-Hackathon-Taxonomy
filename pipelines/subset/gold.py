"""Partition all existing Gold-linked listing IDs; copy native Gold rows unchanged."""
import argparse
import hashlib
import json
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq


def sha256(path):
    with Path(path).open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def build_links(con, domain, entry):
    con.execute('CREATE TEMP TABLE links(view VARCHAR,silver_id BIGINT,product_key BIGINT,cluster_id INTEGER,level INTEGER)')
    con.execute('CREATE TEMP TABLE identities(silver_id BIGINT,source_id VARCHAR,brand VARCHAR,product_key BIGINT)')
    labels_by_view, pins = {}, {}
    for view, files in entry['views'].items():
        if sha256(files['labels']) != files['labels_sha256']:
            raise ValueError(f'{domain}/{view}: original Gold checksum differs')
        labels = pq.read_table(files['labels'])
        labels_by_view[view] = labels
        con.register('labels', labels)
        con.execute('CREATE OR REPLACE TEMP TABLE assignments AS SELECT * FROM read_parquet(?)', [files['assignments']])
        hierarchies = {r[0] for r in con.sql('SELECT DISTINCT hierarchy_id FROM assignments').fetchall()}
        if hierarchies != set(labels['hierarchy_id'].to_pylist()) or len(hierarchies) != 1:
            raise ValueError(f'{domain}/{view}: hierarchy does not match original Gold')
        if view == 'listing':
            membership = 'SELECT a.id AS silver_id,NULL::BIGINT AS product_key,a.hierarchy_id,a.cluster_id,a.level FROM assignments a'
        else:
            con.execute('CREATE OR REPLACE TEMP TABLE members AS SELECT * FROM read_parquet(?)', [files['members']])
            con.execute('CREATE OR REPLACE TEMP TABLE products AS SELECT * FROM read_parquet(?)', [files['products']])
            con.execute('''INSERT INTO identities SELECT DISTINCT m.silver_id,m.source_id,p.brand_key,p.product_key
                FROM members m JOIN products p USING(product_id)''')
            membership = '''SELECT m.silver_id,p.product_key,a.hierarchy_id,a.cluster_id,a.level
                FROM members m JOIN products p USING(product_id) JOIN assignments a USING(product_key)'''
        con.execute(f'''INSERT INTO links SELECT DISTINCT ?,m.silver_id,m.product_key,m.cluster_id,m.level
            FROM ({membership}) m JOIN labels l USING(hierarchy_id,cluster_id)''', [view])
        pins[view] = {field: {'path': files.get('original_' + field, files[field]), 'sha256': sha256(files[field])}
                      for field in ('labels', 'assignments', 'members', 'products') if field in files}
        con.unregister('labels')
        print(json.dumps({'domain': domain, 'view': view, 'original_membership_loaded': True}), flush=True)
    return labels_by_view, pins


def write_batch(folder, links, labels_by_view, expected_ids):
    ids = sorted(set(links['silver_id'].to_pylist()))
    if ids != expected_ids:
        raise ValueError(f'{folder}: batch IDs do not match roster')
    folder.mkdir(parents=True, exist_ok=False)
    pq.write_table(links, folder / 'listing_gold_links.parquet', compression='zstd')
    keys = set(zip(links['view'].to_pylist(), links['hierarchy_id'].to_pylist(), links['cluster_id'].to_pylist()))
    gold = folder / 'gold'
    gold.mkdir()
    for view, labels in labels_by_view.items():
        positions = [i for i, (h, c) in enumerate(zip(labels['hierarchy_id'].to_pylist(), labels['cluster_id'].to_pylist()))
                     if (view, h, c) in keys]
        if positions:
            pq.write_table(labels.take(pa.array(positions, type=pa.int64())), gold / f'{view}_labels.parquet', compression='zstd')
    manifest = {'listings': len(ids), 'gold_link_rows': links.num_rows,
                'files': {str(p.relative_to(folder)): {'rows': pq.read_metadata(p).num_rows, 'sha256': sha256(p)}
                          for p in sorted(folder.rglob('*.parquet'))}}
    (folder / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    return manifest


def extract_domain(domain, entry, out, size):
    root = out / domain
    root.mkdir(parents=True)
    with duckdb.connect(config={'threads': 2, 'memory_limit': '2GB'}) as con:
        labels_by_view, pins = build_links(con, domain, entry)
        # Gold IDs define the population. Silver availability never filters it.
        idcol = 'observation_key' if domain == 'food' else 'source_record_key'
        con.execute(f'CREATE TEMP TABLE silver AS SELECT {idcol} AS silver_id,source_id FROM read_parquet(?)', [entry['silver']])
        repeated = con.sql('SELECT count(*)-count(DISTINCT silver_id) FROM silver').fetchall()[0][0]
        if repeated:
            raise ValueError('Configured unlabeled Silver source has repeated observation IDs')
        preferred = 'listing' if 'listing' in labels_by_view else 'innermost_model_v1'
        all_labels = pa.concat_tables([pa.table({'view': [view] * table.num_rows,
                                                'cluster_id': table['cluster_id'], 'label': table['label']})
                                      for view, table in labels_by_view.items()])
        con.register('all_labels', all_labels)
        conflicts = con.sql('''SELECT count(*) FROM (
            SELECT silver_id FROM identities GROUP BY 1 HAVING count(DISTINCT source_id)>1)''').fetchall()[0][0]
        if conflicts:
            raise ValueError('Original Gold memberships disagree on source identity')
        source_conflicts = con.sql('''SELECT count(*) FROM identities i JOIN silver s USING(silver_id)
            WHERE i.source_id IS DISTINCT FROM s.source_id''').fetchall()[0][0]
        if source_conflicts:
            raise ValueError('Exact Gold/Silver ID has conflicting source identity')
        con.execute('''CREATE TEMP TABLE identity AS SELECT silver_id,min(source_id) AS source_id,
            min(brand) AS brand,min(product_key) AS sort_product FROM identities GROUP BY 1''')
        con.execute('''CREATE TEMP TABLE anchor AS SELECT l.silver_id,g.label FROM links l
            JOIN all_labels g USING(view,cluster_id)
            QUALIFY row_number() OVER(PARTITION BY silver_id
                ORDER BY (view=$preferred) DESC,level DESC,view,product_key,cluster_id)=1''', {'preferred': preferred})
        con.execute('''CREATE TEMP TABLE roster AS SELECT a.silver_id,coalesce(i.source_id,s.source_id) AS source_id,
            s.silver_id IS NOT NULL AS in_current_silver,
            ((row_number() OVER(ORDER BY a.label,i.brand,i.sort_product,a.silver_id)-1)//$size+1)::INTEGER AS batch
            FROM anchor a LEFT JOIN identity i USING(silver_id) LEFT JOIN silver s USING(silver_id)''', {'size': size})
        con.execute('CREATE TEMP TABLE historical(silver_id BIGINT,source_id VARCHAR)')
        for history in entry.get('historical_sources', []):
            con.execute(f'INSERT INTO historical SELECT DISTINCT {idcol},source_id FROM read_parquet(?)', [history['path']])
        con.execute('ALTER TABLE roster ADD COLUMN in_historical_silver BOOLEAN')
        con.execute('''UPDATE roster r SET in_historical_silver=EXISTS(
            SELECT 1 FROM historical h WHERE h.silver_id=r.silver_id AND h.source_id=r.source_id)''')
        complete_count = con.sql('SELECT count(*) FROM roster').fetchall()[0][0]
        roster = con.sql('SELECT * FROM roster ORDER BY batch,silver_id').to_arrow_table()
        if roster.num_rows == 0:
            raise ValueError(f'{domain}: no Gold-linked listings')
        pq.write_table(roster, root / 'listing_index.parquet', compression='zstd')
        expected = {}
        for row in roster.to_pylist():
            expected.setdefault(row['batch'], []).append(row['silver_id'])
        hierarchy_map = pa.Table.from_pylist([{'view': view, 'hierarchy_id': table['hierarchy_id'][0].as_py()}
                                             for view, table in labels_by_view.items()])
        con.register('hierarchy_map', hierarchy_map)
        reader = con.sql('''SELECT r.batch,l.view,l.silver_id,r.source_id,l.product_key,h.hierarchy_id,l.cluster_id,l.level
            FROM links l JOIN roster r USING(silver_id) JOIN hierarchy_map h USING(view)
            ORDER BY r.batch,l.silver_id,l.view,l.product_key,l.level,l.cluster_id''').to_arrow_reader(32768)
        active, pending, batch_reports = None, [], []
        for record_batch in reader:
            table = pa.Table.from_batches([record_batch])
            for batch_id in pc.unique(table['batch']).to_pylist():
                if active is not None and active != batch_id:
                    batch_reports.append(write_batch(root / f'batch-{active:05d}', pa.concat_tables(pending), labels_by_view, expected[active]))
                    pending = []
                active = batch_id
                pending.append(table.filter(pc.equal(table['batch'], batch_id)))
        if pending:
            batch_reports.append(write_batch(root / f'batch-{active:05d}', pa.concat_tables(pending), labels_by_view, expected[active]))
        joinable = sum(roster['in_current_silver'].to_pylist())
        historical_joinable = sum(roster['in_historical_silver'].to_pylist())
        unavailable = sum(not a and not b for a,b in zip(roster['in_current_silver'].to_pylist(), roster['in_historical_silver'].to_pylist()))
        report = {'format': 'original_gold_listing_batches/v1', 'domain': domain,
            'listings': roster.num_rows, 'complete_gold_listing_population': complete_count,
            'batch_size': size, 'batches': len(batch_reports),
            'current_silver_joinable_listings': joinable, 'not_in_current_silver': roster.num_rows-joinable,
            'historical_silver_joinable_listings': historical_joinable, 'not_in_available_silver': unavailable,
            'historical_sources': [{'path': h.get('original_path', h['path']), 'sha256': sha256(h['path'])}
                                   for h in entry.get('historical_sources', [])],
            'silver_source': entry.get('original_silver', entry['silver']),
            'silver_source_sha256': sha256(entry['silver']), 'gold_release': entry['gold_release'],
            'gold_sources': pins, 'all_original_gold_columns_and_values_preserved': True,
            'selection': 'All listing IDs reached by any original Gold-labeled assignment, all views and hierarchy levels; no review, classification or Pedia filter.',
            'ordering': 'Original deepest Gold label (listing view preferred for Food, innermost model for Fragrance), then original catalog brand/product; stable Silver ID ties.',
            'identity': 'silver_id is the exact signed 64-bit observation_key (Food) or source_record_key (Fragrance); it is never a product_key or cluster ID.',
            'gold_link_rows': sum(r['gold_link_rows'] for r in batch_reports)}
        (root / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        print(json.dumps({k:v for k,v in report.items() if k != 'gold_sources'}), flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sources', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--size', default=500, type=int)
    parser.add_argument('--domain', choices=['food','fragrance','both'], default='both')
    args = parser.parse_args()
    if args.size <= 0:
        parser.error('size must be positive')
    if args.out.exists():
        parser.error('Output exists; choose a new directory')
    config = json.loads(args.sources.read_text('utf-8-sig'))
    domains = ('food','fragrance') if args.domain == 'both' else (args.domain,)
    args.out.mkdir(parents=True)
    reports = {domain: extract_domain(domain, config['domains'][domain], args.out, args.size)
               for domain in domains}
    (args.out / 'report.json').write_text(json.dumps(reports, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
