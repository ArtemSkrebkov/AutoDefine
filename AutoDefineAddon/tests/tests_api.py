import pytest

import sys
import os

myPath = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, myPath + '/../')

import urllib.request
import autodefine

def test_empty_entries_if_url_empty():
    assert autodefine.get_entries_from_api("word", "") == []

def test_non_empty_entries_if_url_correct():
    word = "word"
    KEY = "47f165c1-346b-410a-b25c-a3611ac762cc"
    url = "http://www.dictionaryapi.com/api/v1/references/collegiate/xml/" + \
                     urllib.parse.quote_plus(word) + "?key=" + KEY
    assert autodefine.get_entries_from_api("word", url) != []

class MockNote:
    fields = ["", "", "", "", "WA"]

class MockEditor:
    note = MockNote()
    web = False

    def loadNote(self):
        print("LoadNote")

    def urlToLink(self, url):
        return url

autodefine.MERRIAM_WEBSTER_API_KEY = "47f165c1-346b-410a-b25c-a3611ac762cc"
autodefine.DEFINITION_FIELD = 1
autodefine.PRONUNCIATION_FIELD = 2
autodefine.PHONETIC_TRANSCRIPTION_FIELD = 3

autodefine.PREFERRED_DICTIONARY = "COLLEGIATE"

def test_can_serialize_xml_card():
    word = "test"
    cardBuilder = autodefine.CollegiateCardBuilder(word)
    cardBuilder.addDefinition()
    cardBuilder.addPronunciation()
    cardBuilder.addTranscription()
    card = cardBuilder.getCard()

    editor = MockEditor()
    card.serialize(editor)

    assert word == editor.note.fields[0]
    assert editor.note.fields[autodefine.DEFINITION_FIELD].find("to put to test or proof") != -1
    assert editor.note.fields[autodefine.PRONUNCIATION_FIELD].find("wav") != -1
    assert editor.note.fields[autodefine.PHONETIC_TRANSCRIPTION_FIELD].find("test") != -1

def test_can_get_definition():
    editor = MockEditor()
    word = "insert"
    editor.note.fields[0] = word
    autodefine._get_definition(editor, True, True, True)

    assert editor.note.fields[0] == word
    assert editor.note.fields[autodefine.DEFINITION_FIELD].find("to put or thrust") != -1
    assert editor.note.fields[autodefine.PRONUNCIATION_FIELD].find("insert") != -1
    assert editor.note.fields[autodefine.PRONUNCIATION_FIELD].find("wav") != -1
    assert editor.note.fields[autodefine.PHONETIC_TRANSCRIPTION_FIELD].find("in-ˈsərt") != -1

