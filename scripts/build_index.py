"""Build an auditable SQLite lexical index of short bilingual curated summaries.
This release does not claim to have installed or evaluated an embedding model.
"""
import sqlite3,json,argparse,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from catalog import load_catalog

def build(output):
    c=load_catalog();output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    connection=sqlite3.connect(output)
    with connection:
        connection.execute('DROP TABLE IF EXISTS evidence')
        connection.execute('CREATE TABLE evidence (id TEXT PRIMARY KEY, source_id TEXT, version TEXT, topic TEXT, locale TEXT, section TEXT, text TEXT)')
        for chunk in c['chunks']:
            for locale,text in chunk['text'].items():connection.execute('INSERT INTO evidence VALUES (?,?,?,?,?,?,?)',(chunk['id']+'.'+locale,chunk['source_id'],chunk['source_version'],chunk['topic'],locale,chunk['section'],text))
        connection.execute('CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT)')
        connection.execute('INSERT OR REPLACE INTO metadata VALUES (?,?)',('retrieval','Unicode lexical baseline; no embedding model'))
    connection.close()
    return {'chunks':len(c['chunks']),'localized_rows':len(c['chunks'])*2,'index':str(output),'embedding_model':None}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',default='data/index/navigation.sqlite');a=p.parse_args();print(json.dumps(build(a.output)))
