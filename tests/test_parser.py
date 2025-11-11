from datetime import date

from src.nlu.parser import Parser


def test_parser_extracts_entities():
    parser = Parser()
    text = """Hi,\nPlz send flt options for Mum-Del on Nov 11th from 3pm-5pm.\nAlso plz suggest a hotel in Aerocity from Nov 12-13 for 1 night. Thx"""
    result = parser.parse(text)

    assert result.want_flights is True
    assert result.want_hotels is True
    assert result.origin == "BOM"
    assert result.destination == "DEL"
    assert result.depart_date is not None
    assert result.depart_date.month == 11
    assert result.time_from.hour == 15
    assert result.time_to.hour == 17
    assert result.check_in is not None and result.check_out is not None
    assert result.landmark == "aerocity"
    assert result.selection_flights == []
    assert result.selection_hotels == []
