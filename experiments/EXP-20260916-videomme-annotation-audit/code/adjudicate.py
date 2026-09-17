"""Materialize recorded, non-blind Codex audit decisions; not an automatic judge.

Decisions were made by inspecting the source frames/subtitles in this session.
Re-running this script reproduces the records, not an independent semantic audit.
"""
import collections
import copy
import json
from pathlib import Path
from prepare_audit import OUT, SOURCE, dump, sha

RECORD = Path(__file__).resolve().parents[1]

# Concrete declarative answer facts, replacing vague instructions or bundled facts.
FACTS = {
 '626-3': ['Standard Thyroid Treatment is introduced before Stress influence on the production of TSH.', 'Stress influence on the production of TSH is introduced before How to cure thyroid when you have auto-immune.'],
 '660-1': ['The elaborate architecture of the Stairway to Heaven estate is the evidence cited.'],
 '674-3': ['Example round one has the yaku Tanyao.'],
 '782-1': ['The main subject is the process and artistry of theatrical costume design.'],
 '782-3': ['William Ivey Long and Willa Kim have a teacher–student professional relationship.'],
 '806-1': ['Contestants preserve the already stacked can tower.', 'They build on that existing tower to achieve greater height.'],
 '808-2': ['Joe pounces on the table because his friends tasked him with finding all the broken tables.'],
 '816-1': ['No obvious difference other than color is discernible between the yellow and red lions in the video.'],
 '833-1': ['The dish identified is Pinakbet.'],
 '843-1': ['Gorgeous is the category containing the most outfits.'],
 '845-3': ['A necklace is being introduced when she takes off her coat.'],
 '872-2': ['The animals are described as cute.'],
 '885-3': ['In both semifinals and finals, the attacking side scores when it scores a goal.', 'In both semifinals and finals, the defending side scores when the attacking side fails to score a goal.'],
 '660-2': ['Food particles in dental plaque were analyzed.', 'That analysis revealed a diverse diet, supporting the inference of wealth.'],
 '834-1': ['The children appear in order from youngest to oldest.'],
 '843-2': ['The Nothing new category includes an outfit with a hat.', 'The other categories do not include an outfit with a hat.'],
}
ORDER = {
 '674-2': ['Different types of tiles', 'How to create a winning hand', 'Strategies to complete a winning hand quickly', 'Different types of yaku'],
 '715-1': ['Tesla', 'Coca-Cola', 'Intel'],
 '816-2': ['Unfurling a banner from their mouths', 'Catching the balls thrown by ground staff', 'Tumbling down from the high platform'],
 '821-1': ['Cutting off the tinsel', 'Wrapping the brown yarn', 'Making the white tail from a microfiber duster mop pad', 'Making and tying the lace bow'],
 '845-1': ['Engagement ring', 'Cartier bracelets', 'Tabayer earrings', 'Missoma hoops'],
}
for key, seq in ORDER.items():
    FACTS[key] = [f'{a} occurs before {b}.' for a, b in zip(seq, seq[1:])]

HOLDS = {
 '669-2': '原题英文人物指代有歧义；旧改写把持枪者的角色改成被刺杀检察官的角色。退回原题，不能凭官方选项消解指代。',
 '796-1': '题干仅问主旨，旧评分强制回答八个魔术；该数量用于区分原选项，是否应成为简答必要事实须统一校准。',
 '796-3': '去掉选项后，共同点不唯一；不能仅接受官方选项中的同一地点而排斥其他源内容支持的共同点。',
 '821-2': '去掉选项后，两件工艺品的共同点不唯一；当前单一答案规则不足以覆盖有效简答。',
 '833-1': '原帧明确标出 Pinakbet，旁白说其融合多方饮食来源；但 best 的唯一比较标准未明确。撤销错误冲突，暂不冻结单一金标。',
 '833-2': 'companion 是宽泛同行关系；去选项后其粒度和其他可接受关系需源内容校准。',
 '834-2': '原字幕支持准备者认为 Sadie 熟练并给她计时；未明确与其他孩子比较食物选择能力。采用较忠实的候选参考，等待评分规则校准。',
 '834-3': '原顺序题的三个食物来自答案选项，题干未给事件集合；删去选项后可能包含许多备餐动作，不能直接用三项答案作唯一标准。',
 '872-2': 'Cute 是评价性描述；去选项后要求任意特征却仅按可爱打分，评分空间未界定。',
}
UNSUITABLE = ['655-2', '715-2', '715-3', '796-2', '806-3']
GENERIC = ['626-3', '660-1', '674-3', '782-1', '782-3', '806-1', '808-2', '816-1', '833-1', '843-1', '845-3', '872-2', '885-3']

# Per-pilot result: reference truth and old-package sufficiency are separate.
PILOT = {
 '660-2': dict(result='source_supported_ai', old_package='gap_confirmed', cause=['retrieval_miss'],
   subtitle_windows=[[1465,1517]], old_frame_times=[1579.011], new_frame_times=[1467,1475,1482,1492,1501,1511],
   conclusion='1481.76–1515.52 秒旁白直接连起牙菌斑中的食物分析、丰富食谱、财富与种植园主人推断；旧包完全漏掉该段。',
   limits='语义由原始字幕支持，画面仅呈现实验室、牙齿与人物；没有独立听写校准字幕。旧 1580.012 秒引文属于 00158，不能归入 00157。'),
 '669-1': dict(result='source_supported_ai', old_package='sufficient_at_question_granularity_ai', cause=['overstrict_comparison'],
   subtitle_windows=[[15,49],[66,134],[636,642],[940,948],[1791,1803]], old_frame_times=[3.003,740.031,1790.038], new_frame_times=[],
   conclusion='主持人观看电影法律场景并逐段评论；开头说明、段落衔接、结尾和均匀概览一致。不能把主旨表述 each clip 当成逐帧全称证明要求。',
   limits='属于内容呈现形式的代表性核验，不证明每帧均为点评，也不核验电影法律陈述本身。'),
 '674-2': dict(result='source_supported_ai', old_package='order_supported_first_introduction_not_audited', cause=['overstrict_comparison','bundled_scoring_fact'],
   subtitle_windows=[[0,510]], old_frame_times=[90,220,340,503], new_frame_times=[],
   conclusion='连续读取前 510 秒字幕：78.56 秒起讲牌类，145.28 秒起讲成手，339.04 秒起讲碰吃策略，484.4 秒起定义役并讲役种。顺序 b→d→c→a。',
   limits='quickly 是题目给定章节的描述，不应在顺序答案中另要求速度证明。字幕及各节原帧可定位章节；未播放连续音频。'),
 '715-3': dict(result='short_answer_unsuitable', old_package='not_run', cause=['negative_option_dependence'],
   subtitle_windows=[], old_frame_times=[], new_frame_times=[],
   conclusion='删去候选原因集合后，未提到的原因可以无限多，无法保持原选择题任务。保留原 MCQ，不纳入当前简答轨。',
   limits='本次为适配语义复核，未核验整段视频的原因缺失。'),
 '782-1': dict(result='source_supported_ai', old_package='topic_supported_coverage_initially_sparse', cause=['generic_scoring_fact','topic_scope_guard','overstrict_reference_conflict'],
   subtitle_windows=[[78,125],[370,395],[510,535],[779,861],[924,1016],[1387,1418],[1696,1745]], old_frame_times=[73.031,516.015,1103.018], new_frame_times=[],
   conclusion='采访、服装草图、工坊与舞台作品围绕戏剧服装设计。早年布景训练是职业背景，提到布景不与服装设计主旨相矛盾。',
   limits='新增全程均匀 12 帧概览；并非连续全片观看。主旨核验不采用计数或不存在性证明标准。'),
 '806-3': dict(result='short_answer_unsuitable', old_package='not_run', cause=['negative_option_dependence'],
   subtitle_windows=[[140,480],[2709,2750]], old_frame_times=[], new_frame_times=[150,180,210,275,330,400,2715,2745],
   conclusion='前段字幕列出五件奖品并说明赢家全拿，末段 Sam 获胜；木棍不在奖品表内。但不在奖品表中的物品无限多，去选项后仍不能唯一作答。',
   limits='本轮不通过改变题干列出原选项来伪装成无选项简答；奖品字幕为上下文支持，不是逐帧全物体排查。'),
 '821-1': dict(result='source_supported_ai', old_package='order_supported_material_and_completion_undercovered', cause=['bundled_scoring_fact','window_boundary'],
   subtitle_windows=[[106,150],[211,241],[648,711],[834,861],[968,1001]], old_frame_times=[130,230,660,970], new_frame_times=[650,655,680,700,840,855,880,900,985,990,997],
   conclusion='原帧与字幕支持去亮片→绕棕纱→做白尾→制作并系蝴蝶结。652.44 秒明说 microfiber duster mop pad，约 990–997 秒可见最终蝴蝶结。',
   limits='旧包并未完整覆盖材质说明和蝴蝶结完成瞬间；顺序事实已拆为三条相邻先后关系，不将形容词的重复证明混入答题要求。'),
 '833-1': dict(result='reference_qualification_needed', old_package='name_visible_relation_supported_best_ambiguous', cause=['missed_visible_text','subtitle_entity_error','question_ambiguity'],
   subtitle_windows=[[531,573]], old_frame_times=[560,563,566], new_frame_times=[],
   conclusion='560–563 秒菜品画面直接写 Pinakbet / Squash and Okra Stew；555.96–568.72 秒字幕虽误转写 pck bet，明确描述当地海鲜、多国蔬菜及泰国虾酱。旧核验声称无菜名及指向 sisig 是误读。',
   limits='源内容支持 Pinakbet 代表融合历史，但没有明确给所有菜排名；保留 best 题干的歧义，不将该推断升级为唯一金标。'),
 '834-2': dict(result='reference_qualification_needed', old_package='motivation_clause_truncated', cause=['window_boundary','unsupported_reference_detail','unsupported_conflict'],
   subtitle_windows=[[1803,1825],[1850,1870]], old_frame_times=[1806.004,1809.007,1850.015], new_frame_times=[1806,1810,1812,1816,1819,1824],
   conclusion='1806.48–1820.34 秒准备者称 Sadie 是熟手、相信她能完成，接着提议给三分钟计时；只解释计时用途不能否定该动机。',
   limits='官方参考中的比其他孩子更会选择食物没有直接出现；修正版候选只保留熟练和信任，原参考仍保存，等待正式评分校准。'),
 '843-3': dict(result='source_supported_ai', old_package='sufficient_at_question_granularity_ai', cause=['topic_scope_guard'],
   subtitle_windows=[[0,79]], old_frame_times=[0,563,573], new_frame_times=[],
   conclusion='开头标题明确 ranking every single eras tour outfit，42.88 秒说明逐套评级；中段评级界面和新增全程概览一致。',
   limits='确认主题无需逐帧证明所有服装都被评级；不据此核验完整服装总数或最高类别。'),
 '845-2': dict(result='source_supported_ai', old_package='gap_confirmed_wrong_ring', cause=['entity_retrieval_miss'],
   subtitle_windows=[], old_frame_times=[1183,1209,1330], new_frame_times=[1235,1260],
   conclusion='1235 秒盒子写 LEON DIAMOND；1260 秒原始近景可见同一枚钻石戒指横跨两根手指。旧包落在其他戒指的展示时段。',
   limits='仅用画面和邻近实体介绍核验；该视频确实缺原始 SRT，未补做 ASR，caption 仅用于定位不作为证据。'),
 '885-2': dict(result='source_supported_ai', old_package='sufficient_at_question_granularity_ai', cause=['comparison_lost_cross_modal_relation'],
   subtitle_windows=[[196,215]], old_frame_times=[203,206,209], new_frame_times=[],
   conclusion='206 秒背面写 CHAMPION / TOP BALLER / NORTH LONDON，主持人指向背面；203.84–209.04 秒明确回忆第二期。视觉标识与旧赛事的关系在原包中可恢复。',
   limits='previous 按较早的一场理解，不证明紧邻上一场；也不要求服装所属者的额外历史身份。'),
}


def facts(statements):
    return [{'id': f'F{i}', 'statement': s, 'acceptable_variants': [s]} for i,s in enumerate(statements,1)]


def main():
    inputs=json.loads((OUT/'draft_input.json').read_text())
    inspection=json.loads((OUT/'inspection_manifest.json').read_text())
    expanded=json.loads((OUT/'expanded_manifest.json').read_text())
    changes, reviews, pilots = [], [], []
    for item in inputs:
        q, original=item['question'],item['draft']
        key=q['original_id'];a=copy.deepcopy(original['annotation']);reasons=[]
        if key in FACTS:
            a['required_facts']=facts(FACTS[key])
            reasons.append('评分事实改为具体声明；顺序题按相邻关系拆分，事实级按题归一化。')
        if key in GENERIC:
            reasons.append('原 statement 仅复述任务或没有具体答案，不能直接作为事实评分规则。')
        if key in ORDER or key=='626-3':
            a['scoring_note']='Accept full sequences or unambiguous event labels from the question. Score each adjacent precedence relation semantically; do not demand word-for-word repetition of supplied event descriptions. Normalize fact score within the question. Reject contradictory order claims.'
        if key in HOLDS:
            a['adaptation_status']='needs_review'; reasons.append(HOLDS[key])
        if key=='669-2':
            a['short_question']=q['original_question']; a['required_facts']=[]
            a['reference_answer_draft']=q['reference_draft']
        if key=='885-3':
            a['reference_answer_draft']='In the semifinals and finals, the attacking side scores if it scores a goal; otherwise the defending side scores.'
        if key=='834-2':
            a['reference_answer_draft']='The food preparer regards Sadie as skilled at preparing her lunch and is confident she can do it, so she gives her a timed challenge.'
            a['required_facts']=facts(['The food preparer gives Sadie a timed challenge because she regards her as skilled at preparing her lunch.'])
            a['modality']='audio_subtitle'
        if key=='816-3':
            a['required_facts'][0]['acceptable_variants']=['They take pictures with the lion.']
            a['required_facts'][1]['acceptable_variants']=["They pet the lion's head."]
            reasons.append('删除过宽同义项：拍狮子不必然是与狮子合照；摸狮子不必然摸头。')
        if key=='843-2':
            a['evidence_scope']='global_coverage';reasons.append('与其他所有类别比较的排他性事实需要覆盖其他类别。')
        if key in ['821-2','834-3','674-2','816-1']:
            a['evidence_scope']='cross_segment';reasons.append('所问关系跨事件或对象，应记录关系覆盖，不能凭单帧成立。')
        if key in ['660-3','782-3']:
            a['modality']='audio_subtitle';reasons.append('政治含义或师生关系无法仅凭外观核实；模态标签仍待逐题源内容验证。')
        if key=='833-2':
            a['task_type']=['other'];reasons.append('静态同行关系不等于跨时间身份衔接。')
        if key=='845-3':
            a['task_type']=['single_event_recognition'];reasons.append('脱外套时识别所介绍物品，不是排列多个事件顺序。')
        if key in ['669-1','674-1','782-1','821-3','833-3','843-3','872-1']:
            a['coverage_requirement']='representative_topic_or_format'
        elif key in ['655-2','715-2','715-3','796-2','843-1','843-2']:
            a['coverage_requirement']='exhaustive_or_closed_set'
        else:
            a['coverage_requirement']='case_specific_pending_source_audit'
        if key in UNSUITABLE:
            a['adaptation_status']='unsuitable';a['required_facts']=[]
            reasons.append('否定题脱离原选项集合后不能唯一作答；保留原 MCQ，简答规则清空以避免误入评分。')
        if reasons:
            a['review_flags']=list(dict.fromkeys(a.get('review_flags',[])+reasons))
        # Explicit old/new field diff; unverified reference remains a draft.
        delta={k:{'old':original['annotation'].get(k),'new':v} for k,v in a.items() if original['annotation'].get(k)!=v}
        substantive={k:v for k,v in delta.items() if k not in ['coverage_requirement','review_flags','scoring_note']}
        review={'qid':q['qid'],'reviewer':'Codex current session, non-blind AI review','text_reviewed':True,'human_reviewed':False,
                'source_review_status':PILOT.get(key,{}).get('result','not_run'), 'adaptation_status':a['adaptation_status'],
                'substantive_change':bool(substantive),'placeholder_fact_defect':key in GENERIC,
                'notes':reasons or ['未发现明显文本转换错误；源事实尚未核验，不表示金标通过。']}
        reviews.append(review)
        if delta: changes.append({'qid':q['qid'],'substantive':bool(substantive),'fields':delta})
        revised={**original,'annotation':a,'annotation_version':'audit-v2-draft','official_question':q,
                 'source_verified':PILOT.get(key,{}).get('result')=='source_supported_ai','source_verification_kind':'non_blind_ai_review_only',
                 'human_reviewed':False,'frozen_for_evaluation':False,'audit':review}
        dump(OUT/'revised_drafts'/f"{q['qid'].replace(':','__')}.json",revised)
        if key not in PILOT: continue
        p=copy.deepcopy(PILOT[key]);vid=q['video_id']
        p.update(qid=q['qid'], video_id=vid, official_reference=q['reference_draft'], human_reviewed=False, blind_review=False,
                 audit_truth='AI adjudication, not independently calibrated gold', source_file=str(SOURCE/'run-004-source-refinement/visual'/f"{q['qid'].replace(':','__')}.json"))
        p['source_file_sha256']=sha(p['source_file'])
        source_record=json.loads(Path(p['source_file']).read_text())
        old_hints=p.pop('old_frame_times')
        new_hints=p.pop('new_frame_times')
        p['key_old_frames']=[]
        p['key_new_frames']=[]
        for hint in old_hints:
            nearest=min(source_record['frames'],key=lambda f:abs(f['actual_pts_s']-hint))
            assert abs(nearest['actual_pts_s']-hint)<0.06, (key,hint)
            p['key_old_frames'].append(nearest)
        for hint in new_hints:
            nearest=min(expanded[q['qid']]['frames'],key=lambda f:abs(f['requested_time_s']-hint))
            assert abs(nearest['requested_time_s']-hint)<0.01, (key,hint)
            p['key_new_frames'].append(nearest)
        s=json.loads((OUT/'subtitles'/f'{vid}.json').read_text())
        evidence=[x for x in s['segments'] if any(x['end_s']>lo and x['start_s']<hi for lo,hi in p['subtitle_windows'])]
        dump(OUT/'evidence_subtitles'/f'{key}.json',{'qid':q['qid'],'subtitle_member_sha256':s.get('member_sha256'),'segments':evidence})
        p['subtitle_ids']=[x['subtitle_id'] for x in evidence]
        p['subtitle_evidence_file']=str(OUT/'evidence_subtitles'/f'{key}.json')
        p['inspected_old_sheet']=inspection['sheets'].get(q['qid'],{}).get('path')
        p['inspected_expanded_sheet']=expanded.get(q['qid'],{}).get('sheet')
        p['inspected_old_frame_count']=len(inspection['sheets'].get(q['qid'],{}).get('frames',[]))
        p['inspected_new_frame_count']=len(expanded.get(q['qid'],{}).get('frames',[]))
        pilots.append(p)
    dump(RECORD/'rubric_changes.json',changes)
    (RECORD/'draft_review.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in reviews))
    dump(RECORD/'pilot_audit.json',pilots)
    summary={'drafts_reviewed':len(reviews),'substantive_draft_changes':sum(x['substantive_change'] for x in reviews),
             'eligible_drafts_with_placeholder_fact_defects':len(GENERIC),
             'adaptation_counts':dict(collections.Counter(x['adaptation_status'] for x in reviews)),
             'pilot_cases':len(pilots),'pilot_results':dict(collections.Counter(p['result'] for p in pilots)),
             'old_frames_hash_checked':600,'old_frames_visually_inspected_in_sheets':sum(p['inspected_old_frame_count'] for p in pilots),
             'new_frames_visually_inspected_in_sheets':sum(p['inspected_new_frame_count'] for p in pilots),
             'new_api_calls':0,'human_reviewed':0,'full_continuous_video_viewing':False,'test_set_frozen':False,
             'artifacts_root':str(OUT),'reviewer_session_id':'01a0aadc-0452-7903-aa67-e338744b88e0',
             'counts_are_method_performance':False}
    dump(RECORD/'summary.json',summary)
    print(json.dumps(summary,ensure_ascii=False))


if __name__=='__main__':
    main()
