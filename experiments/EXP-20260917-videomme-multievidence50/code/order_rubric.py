"""Deterministic adjacent-order clauses, using ONLY original item labels and answer."""
import re
MARK=re.compile(r'\(([a-zA-Z0-9]+)\)|([①②③④⑤⑥⑦⑧⑨⑩])')
def ordered_rubric(question):
 text=question['original_question']
 if not re.search(r'\border\b|\bsequence\b|\bchronolog',text,re.I):return None
 matches=list(MARK.finditer(text))
 if len(matches)<2:return None
 items={}
 for i,m in enumerate(matches):
  key=(m.group(1) or m.group(2)).lower()
  if key in items:return None
  desc=re.sub(r'\s+',' ',text[m.end():matches[i+1].start() if i+1<len(matches) else len(text)]).strip(' .\n')
  if not desc:return None
  items[key]=desc
 order=[(m.group(1) or m.group(2)).lower() for m in MARK.finditer(question['reference_draft'])]
 if len(order)!=len(items) or len(set(order))!=len(order) or set(order)!=set(items):return None
 facts=[{'id':f'F{i+1}','fact':f'The introduction/performance of ({a}) {items[a]} occurs before ({b}) {items[b]} in the video.','endpoints':[{'id':'E1','entity':items[a]},{'id':'E2','entity':items[b]}]} for i,(a,b) in enumerate(zip(order,order[1:]))]
 return {'question':text,'required_facts':facts,'items':items,'reference_order':order,'policy':'Adjacent ordering relations from original labeled items and official permutation; no numeric ranks, exact timestamps or additional uniqueness claims.'}
