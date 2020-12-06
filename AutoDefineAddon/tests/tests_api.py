import pytest

import sys
import os

myPath = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, myPath + '/../')
sys.path.insert(0, myPath + '/../libs')

import urllib.request
import config
import cardbuilder
import autodefine

def test_empty_entries_if_url_empty():
    assert cardbuilder.get_entries_from_api("word", "") == []

def test_non_empty_entries_if_url_correct():
    word = "word"
    KEY = "47f165c1-346b-410a-b25c-a3611ac762cc"
    url = "http://www.dictionaryapi.com/api/v1/references/collegiate/xml/" + \
                     urllib.parse.quote_plus(word) + "?key=" + KEY
    assert cardbuilder.get_entries_from_api("word", url) != []

class MockNote:
    fields = ["", "", "", "", ""]

class MockEditor:
    note = MockNote()
    web = False

    def loadNote(self):
        pass

    def urlToLink(self, url):
        return url

config.DEFINITION_FIELD = 1
config.PRONUNCIATION_FIELD = 2
config.PHONETIC_TRANSCRIPTION_FIELD = 3

def test_can_serialize_xml_card():
    config.MERRIAM_WEBSTER_API_KEY = "47f165c1-346b-410a-b25c-a3611ac762cc"
    config.PREFERRED_DICTIONARY = "COLLEGIATE"
    word = "test"
    cardBuilder = cardbuilder.CollegiateCardBuilder(word)
    cardBuilder.addDefinition()
    cardBuilder.addPronunciation()
    cardBuilder.addTranscription()
    card = cardBuilder.getCard()

    editor = MockEditor()
    card.serialize(editor)

    assert word == editor.note.fields[0]
    assert editor.note.fields[config.DEFINITION_FIELD].find("to put to test or proof") != -1
    assert editor.note.fields[config.PRONUNCIATION_FIELD].find("wav") != -1
    assert editor.note.fields[config.PHONETIC_TRANSCRIPTION_FIELD].find("test") != -1

def test_can_get_definition():
    config.MERRIAM_WEBSTER_API_KEY = "47f165c1-346b-410a-b25c-a3611ac762cc"
    config.PREFERRED_DICTIONARY = "COLLEGIATE"
    editor = MockEditor()
    word = "insert"
    editor.note.fields[0] = word
    autodefine._get_definition(editor, True, True, True)

    print(editor.note.fields)

    assert editor.note.fields[0] == word
    assert editor.note.fields[config.DEFINITION_FIELD].find("to put or thrust") != -1
    assert editor.note.fields[config.PRONUNCIATION_FIELD].find("insert") != -1
    assert editor.note.fields[config.PRONUNCIATION_FIELD].find("wav") != -1
    assert editor.note.fields[config.PHONETIC_TRANSCRIPTION_FIELD].find("in-ˈsərt") != -1

def test_can_serialize_json_spanish_card():
    config.MERRIAM_WEBSTER_SPANISH_API_KEY = "01c4cc4d-6f84-41e2-9ae0-10cfd5e6277e"
    config.PREFERRED_DICTIONARY = "SPANISH"
    word = "entender"
    cardBuilder = cardbuilder.SpanishCardBuilder(word)
    cardBuilder.addDefinition()
    cardBuilder.addPronunciation()
    cardBuilder.addTranscription()
    card = cardBuilder.getCard()

    editor = MockEditor()
    card.serialize(editor)

    assert word == editor.note.fields[0]
    assert editor.note.fields[config.DEFINITION_FIELD].find("understand") != -1
    assert editor.note.fields[config.PRONUNCIATION_FIELD].find("wav") != -1
    assert editor.note.fields[config.PRONUNCIATION_FIELD].find("enten") != -1
    assert editor.note.fields[config.PHONETIC_TRANSCRIPTION_FIELD] == ""
