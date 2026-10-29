from pokervision.education import readable_history, turn_lesson, card_name
from pokervision.engine import Table


def test_old_records_readable_without_changing_original():
    original = ['Luna: small blind 1', 'flop: 2s Th 4h',
                'preflop · Você: call → 10', 'river · Luna: check',
                'Showdown: Você: Par', 'Distribuição: Você +20']
    display = readable_history(original)
    assert '10 de copas' in display and '2 de espadas' in display
    assert 'aposta obrigatória menor: 1' in display
    assert 'pagou para acompanhar' in display
    assert 'Total já colocado nesta rodada: 10' in display
    assert 'passou a vez sem apostar' in display
    assert 'recebeu 20 fichas' in display
    assert original[1] == 'flop: 2s Th 4h'
    assert card_name('Qs') == 'Dama de espadas'


def test_price_explanation_uses_current_values_without_claiming_equity():
    t = Table(seed=1)
    t.start()
    text = turn_lesson(t, t.actor)
    assert 'mais 2 fichas' in text
    assert '2 ÷ 5 = 40.0%' in text
    assert 'NÃO mede a força das suas cartas' in text
    assert 'nenhuma taxa' in text


def test_free_check_and_sidepot_have_different_explanations():
    t = Table(['A','B'], [100,100], seed=1)
    t.start()
    t.act('call')
    assert 'sem pagar (check)' in turn_lesson(t, t.actor)
    assert 'Entenda o preço' not in turn_lesson(t, t.actor)
    t.act('check')
    t.act('all-in')
    text = turn_lesson(t, t.actor)
    assert 'não mostro a conta simples' in text
    assert '÷' not in text
