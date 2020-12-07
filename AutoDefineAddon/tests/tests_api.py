import pytest

import sys
import os

myPath = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, myPath + '/../')
sys.path.insert(0, myPath + '/../libs')

import urllib.request
import settings

settings.TEST_MODE = True
settings.DEFINITION_FIELD = 1
settings.PRONUNCIATION_FIELD = 2
settings.PHONETIC_TRANSCRIPTION_FIELD = 3

COLLEGIATE_KEY = "47f165c1-346b-410a-b25c-a3611ac762cc"
SPANISH_KEY = "01c4cc4d-6f84-41e2-9ae0-10cfd5e6277e"

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


def test_can_serialize_xml_card():
    settings.MERRIAM_WEBSTER_API_KEY = COLLEGIATE_KEY
    settings.PREFERRED_DICTIONARY = "COLLEGIATE"
    word = "test"
    cardBuilder = cardbuilder.CollegiateCardBuilder(word)
    cardBuilder.addDefinition()
    cardBuilder.addPronunciation()
    cardBuilder.addTranscription()
    card = cardBuilder.getCard()

    editor = MockEditor()
    card.serialize(editor)

    assert word == editor.note.fields[0]
    assert editor.note.fields[settings.DEFINITION_FIELD].find("to put to test or proof") != -1
    assert editor.note.fields[settings.PRONUNCIATION_FIELD].find("wav") != -1
    assert editor.note.fields[settings.PHONETIC_TRANSCRIPTION_FIELD].find("test") != -1

def test_can_get_definition():
    settings.MERRIAM_WEBSTER_API_KEY = COLLEGIATE_KEY
    settings.PREFERRED_DICTIONARY = "COLLEGIATE"
    editor = MockEditor()
    word = "insert"
    editor.note.fields[0] = word
    autodefine._get_definition(editor, True, True, True)

    print(editor.note.fields)
    assert editor.note.fields[0] == word
    assert editor.note.fields[settings.DEFINITION_FIELD].find("to put or thrust") != -1
    assert editor.note.fields[settings.PRONUNCIATION_FIELD].find("insert") != -1
    assert editor.note.fields[settings.PRONUNCIATION_FIELD].find("wav") != -1
    assert editor.note.fields[settings.PHONETIC_TRANSCRIPTION_FIELD].find("in-ˈsərt") != -1

def test_can_serialize_json_spanish_card():
    settings.MERRIAM_WEBSTER_API_KEY = SPANISH_KEY
    settings.PREFERRED_DICTIONARY = "SPANISH"
    word = "entender"
    cardBuilder = cardbuilder.SpanishCardBuilder(word)
    cardBuilder.addDefinition()
    cardBuilder.addPronunciation()
    cardBuilder.addTranscription()
    card = cardBuilder.getCard()

    editor = MockEditor()
    card.serialize(editor)

    assert word == editor.note.fields[0]
    assert editor.note.fields[settings.DEFINITION_FIELD].find("understand") != -1
    assert editor.note.fields[settings.DEFINITION_FIELD].find("verb") != -1
    assert editor.note.fields[settings.PRONUNCIATION_FIELD].find("wav") != -1
    assert editor.note.fields[settings.PRONUNCIATION_FIELD].find("enten") != -1
    assert editor.note.fields[settings.PHONETIC_TRANSCRIPTION_FIELD] == ""

def test_can_get_pronunciation_hombre():
    settings.MERRIAM_WEBSTER_API_KEY = SPANISH_KEY
    settings.PREFERRED_DICTIONARY = "SPANISH"
    word = "hombre"
    cardBuilder = cardbuilder.SpanishCardBuilder(word)
    cardBuilder.addPronunciation()
    card = cardBuilder.getCard()

    editor = MockEditor()
    card.serialize(editor)

    assert word == editor.note.fields[0]
    assert editor.note.fields[settings.PRONUNCIATION_FIELD].find("not available :(") != -1

def test_can_get_pronunciation_alto():
    settings.MERRIAM_WEBSTER_API_KEY = SPANISH_KEY
    settings.PREFERRED_DICTIONARY = "SPANISH"
    word = "alto"
    cardBuilder = cardbuilder.SpanishCardBuilder(word)
    cardBuilder.addPronunciation()
    card = cardBuilder.getCard()

    editor = MockEditor()
    card.serialize(editor)

    assert word == editor.note.fields[0]
    assert editor.note.fields[settings.PRONUNCIATION_FIELD].find("alto") != -1
