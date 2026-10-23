import pytest

from ciw2.verify.quote import check_quote


@pytest.mark.parametrize('label',['IL-31RA','IL-4Rα','IgG4','CM310','NCT00000001'])
def test_exact_alphanumeric_scientific_labels_are_not_negative_numbers(label):
    text=f'The complete source label is {label}.'
    assert check_quote(text,text,label).ok


@pytest.mark.parametrize('value',['IL-32RA','CM31','NCT0000000'])
def test_other_or_partial_identifiers_do_not_pass(value):
    text='The source labels are IL-31RA, CM310, NCT00000001.'
    assert not check_quote(text,text,value).ok


@pytest.mark.parametrize('value',[31,-31,'31','-31','1e3'])
def test_numeric_facts_do_not_borrow_digits_from_identity(value):
    text='The product is IL-31RA and its trial code is NCT1000.'
    assert not check_quote(text,text,value).ok


@pytest.mark.parametrize('label',['IL-4Rα','CM310'])
def test_identifiers_adjacent_to_chinese_words_remain_literal_source_labels(label):
    text=f'研究药物{label}用于本试验。'
    assert check_quote(text,text,label).ok
