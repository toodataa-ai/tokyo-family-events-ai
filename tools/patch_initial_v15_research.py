from pathlib import Path

p = Path("tools/initial_v15_native_research.py")
s = p.read_text(encoding="utf-8")

old = """def prep_legacy():
 if TMP.exists(): subprocess.run(['rm','-rf',str(TMP)],check=True)
 subprocess.run(['git','clone','--depth','1','https://github.com/toodataa-ai/tokyo-weekend-events.git',str(TMP)],check=True)
 subprocess.run([sys.executable,'build_with_extra_sources.py'],cwd=TMP,check=True)"""

new = """def prep_legacy():
 import urllib.request, json
 if TMP.exists(): subprocess.run(['rm','-rf',str(TMP)],check=True)
 ddir=TMP/'site'/'data'; ddir.mkdir(parents=True,exist_ok=True)
 for w in WEEKS:
  req=urllib.request.Request(f'https://toodataa-ai.github.io/tokyo-weekend-events/data/{w}.json',headers={'User-Agent':'Mozilla/5.0 TokyoFamilyEventsAI/1.5'})
  with urllib.request.urlopen(req,timeout=30) as r: data=json.loads(r.read().decode('utf-8'))
  json.dump(data,open(ddir/f'{w}.json','w',encoding='utf8'),ensure_ascii=False)"""

if old not in s:
    raise SystemExit("prep_legacy pattern not found")
s = s.replace(old, new)

old2 = "ds=md(parts[0]); de=md(parts[-1]); area=e.get('area','');"
new2 = "ds=md(parts[0]); de=md(parts[-1]); de=(str(int(ds[:4])+1)+de[4:]) if ds and de and de<ds else de; area=e.get('area','');"
if old2 not in s:
    raise SystemExit("date rollover pattern not found")
s = s.replace(old2, new2)

p.write_text(s, encoding="utf-8")
print("patched initial v1.5 research generator")
