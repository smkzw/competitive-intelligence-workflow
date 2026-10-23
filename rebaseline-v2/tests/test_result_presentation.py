from ciw2.render.portal import data_b, render_report
from ciw2.service import Service


def project(settings, observations):
    svc = Service(settings)
    pid = svc.create_project('试验结果', ['B'])
    tid, _ = svc.db.upsert_entity(pid, 'trial', 'NCT00000001')
    sid = svc.db.add_source(pid, 'ctgov', 'https://example.org/results', 'f' * 64)
    ids = []
    for index, changes in enumerate(observations):
        context = {'endpoint':'Clinical score', 'endpoint_key':'clinical score', 'timepoint':'Weeks 4, 8 and 12',
                   'class_title':f'Week {4 * (index + 1)}', 'category':None, 'arm':'Arm A', 'group_id':'G1',
                   'population':'ITT', 'stat_type':'mean', 'unit':'points', 'param_type':'MEAN'}
        context.update(changes.get('context', {}))
        ids.append(svc.db.add_fact({'project_id':pid, 'entity_id':tid, 'field':'result.primary.value',
            'value':changes.get('value', index), 'tier':'critical', 'status':changes.get('status', 'verified'),
            'source_id':sid, 'extracted_by':'code:ctgov', 'quote':str(changes.get('value', index)), 'context':context}))
    return svc.db, pid, ids


def test_longitudinal_instances_use_explicit_class_visits_and_keep_every_fact(settings):
    db, pid, ids = project(settings, [{}, {}, {}])
    data = data_b(db, pid)
    assert [row['class_title'] for row in data['results']] == ['Week 4','Week 8','Week 12']
    group = data['charts']['groups'][0]
    assert len(data['charts']['groups']) == 1 and group['kind'] == 'line'
    assert [point['x'] for point in group['points']] == [28,56,84]
    assert [point['fact_id'] for point in group['points']] == ids
    assert [point['value'] for point in group['points']] == [0,1,2]
    assert group['axis_unit'] == 'days'


def test_aggregate_window_is_not_assigned_to_its_first_week(settings):
    db, pid, _ = project(settings, [{'context': {'class_title':None}}, {'context': {'class_title':None}}])
    group = data_b(db,pid)['charts']['groups'][0]
    assert group['kind'] == 'bar'
    assert all(point['x'] is None for point in group['points'])


def test_conflicting_singleton_visits_are_not_a_guessed_trajectory(settings):
    db,pid,_ = project(settings,[{'context': {'class_title':'Week 4','category':'Week 8'}},
                                {'context': {'class_title':'Week 12','category':'Week 16'}}])
    groups = data_b(db,pid)['charts']['groups']
    assert all(group['kind'] == 'bar' for group in groups)
    assert sum(len(group['points']) for group in groups) == 2


def test_same_series_visit_collision_preserves_both_observations(settings):
    db,pid,ids = project(settings,[{'context':{'class_title':'Week 4'}},
                                 {'context':{'class_title':'Day 28'},'value':5},
                                 {'context':{'class_title':'Week 8'}}])
    group = data_b(db,pid)['charts']['groups'][0]
    assert group['kind'] == 'bar' and group['collision'] is True
    assert {point['fact_id'] for point in group['points']} == set(ids)
    assert group['values'] == [0,5,2]


def test_population_statistics_and_category_facets_stay_distinct(settings):
    db,pid,_ = project(settings,[{}, {'context':{'population':'PP'}},
        {'context':{'param_type':'GEOMETRIC_MEAN'}}, {'context':{'category':'Responder'}},
        {'context':{'unit':'percent'}}, {'context':{'stat_type':'median'}}])
    assert len(data_b(db,pid)['charts']['groups']) == 6


def test_months_are_not_forced_to_days_and_unknown_windows_stay_distinct(settings):
    db,pid,_=project(settings,[{'context':{'class_title':'Month 1'}},
        {'context':{'class_title':'Month 2'}}, {'context':{'class_title':None,'timepoint':'End of treatment'}},
        {'context':{'class_title':None,'timepoint':'End of follow-up'}}])
    groups=data_b(db,pid)['charts']['groups']
    lines=[group for group in groups if group['kind']=='line']
    assert len(lines)==1 and lines[0]['axis_unit']=='months'
    assert len(groups)==3


def test_more_than_twelve_endpoint_groups_remain_reachable(settings):
    db,pid,ids=project(settings,[{'context':{'endpoint':f'Complete endpoint {i}', 'endpoint_key':f'endpoint{i}'}}
                               for i in range(17)])
    groups=data_b(db,pid)['charts']['groups']
    assert len(groups)==17
    assert {point['fact_id'] for group in groups for point in group['points']}==set(ids)


def test_unknown_unverified_and_boolean_values_remain_in_table_not_numeric_axis(settings):
    db,pid,ids=project(settings,[{'value':None},{'value':4,'status':'unverified'}, {'value':True},{'value':0}])
    data=data_b(db,pid)
    assert len(data['results'])==4
    assert {point['fact_id'] for group in data['charts']['groups'] for point in group['points']}=={ids[3]}
    assert set(data['plot_exclusions'])==set(ids[:3])


def test_missing_visit_position_remains_available_to_break_line_not_fill_zero(settings):
    db,pid,ids=project(settings,[{}, {'value':None,'status':'unknown'}, {}])
    group=data_b(db,pid)['charts']['groups'][0]
    assert group['kind']=='line' and group['positions']==[28,56,84]
    assert [point['fact_id'] for point in group['points']]==[ids[0],ids[2]]


def test_template_has_one_selectable_plot_and_full_measurement_table_without_reminder_wall(settings):
    db,pid,_=project(settings,[{'context':{'endpoint':'Very long complete endpoint '*12}}])
    html=render_report(db,pid,'B')
    assert 'id="result-group"' in html and 'id="chart-result"' in html
    assert 'id="result-query"' in html and 'data-fact-id=' in html
    assert 'Week 4' in html and 'Very long complete endpoint '*12 in html
    assert '仅已核实数据；' not in html and '比例仅在同组分母明确时计算' not in html
