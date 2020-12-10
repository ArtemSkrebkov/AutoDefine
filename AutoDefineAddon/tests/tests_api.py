import pytest

import sys
import os

myPath = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, myPath + '/../')
sys.path.insert(0, myPath + '/../libs')

import urllib.request
import settings
import re

settings.TEST_MODE = True
settings.DEFINITION_FIELD = 1
settings.PRONUNCIATION_FIELD = 2
settings.PHONETIC_TRANSCRIPTION_FIELD = 3

# put your keys to run tests
COLLEGIATE_KEY = "YOUR_KEY"
SPANISH_KEY = "YOUR_KEY"

import cardbuilder
import autodefine

def test_empty_entries_if_url_empty():
    assert cardbuilder.get_entries_from_api("word", "") == []

def test_non_empty_entries_if_url_correct():
    word = "word"
    url = "http://www.dictionaryapi.com/api/v1/references/collegiate/xml/" + \
                     urllib.parse.quote_plus(word) + "?key=" + COLLEGIATE_KEY
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

def test_can_get_definition():
    settings.MERRIAM_WEBSTER_API_KEY = COLLEGIATE_KEY
    settings.PREFERRED_DICTIONARY = "COLLEGIATE"
    editor = MockEditor()
    word = "insert"
    editor.note.fields[0] = word
    autodefine._get_definition(editor, True, True, True)

    assert editor.note.fields[0] == word
    assert editor.note.fields[settings.DEFINITION_FIELD].find("to put or thrust") != -1
    assert editor.note.fields[settings.PRONUNCIATION_FIELD].find("insert") != -1
    assert editor.note.fields[settings.PRONUNCIATION_FIELD].find("wav") != -1
    assert editor.note.fields[settings.PHONETIC_TRANSCRIPTION_FIELD].find("in-ˈsərt") != -1


class MockCardBuilder(cardbuilder.CardBuilder):
    def __init__(self, word):
        super().__init__(word)

    def addDefinition(self):
        self._card.fields[settings.DEFINITION_FIELD] = "definition"

    def addTranscription(self):
        self._card.fields[settings.PHONETIC_TRANSCRIPTION_FIELD] = "transcription"

    def addPronunciation(self):
        self._card.fields[settings.PRONUNCIATION_FIELD] = "pronunciation"

def test_can_serialize_card():
    word = "word"
    card_builder = MockCardBuilder(word)
    card = card_builder.getCard()
    card_builder.addDefinition()
    card_builder.addTranscription()
    card_builder.addPronunciation()

    editor = MockEditor()
    card.serialize(editor)

    assert word == editor.note.fields[0]
    assert editor.note.fields[settings.DEFINITION_FIELD] == "definition"
    assert editor.note.fields[settings.PRONUNCIATION_FIELD] == "pronunciation"
    assert editor.note.fields[settings.PHONETIC_TRANSCRIPTION_FIELD] == "transcription"


@pytest.mark.parametrize("dictionary, word, expected_output", [("SPANISH", "entender", "understand"),
                                                               ("COLLEGIATE", "insert", "to put or thrust")])
def test_can_get_definition(dictionary, word, expected_output):
    settings.PREFERRED_DICTIONARY = dictionary
    card_builder = None
    if dictionary == "SPANISH":
        settings.MERRIAM_WEBSTER_API_KEY = SPANISH_KEY
        card_builder = cardbuilder.SpanishCardBuilder(word)
    else:
        settings.MERRIAM_WEBSTER_API_KEY = COLLEGIATE_KEY
        card_builder = cardbuilder.CollegiateCardBuilder(word)
    card_builder.addDefinition()
    card = card_builder.getCard()

    editor = MockEditor()
    card.serialize(editor)

    assert editor.note.fields[settings.DEFINITION_FIELD].find(expected_output) != -1


@pytest.mark.parametrize("dictionary, word, expected_output", [("SPANISH", "hombre", r"not available"),
                                                               ("SPANISH", "alto", "^http.+?alto.+?wav$"),
                                                               ("SPANISH", "entender", "^http.+?enten.+?wav$"),
                                                               ("COLLEGIATE", "insert", "^http.+?insert.+?wav$"),
                                                               ])
def test_can_get_pronunciation(dictionary, word, expected_output):
    settings.PREFERRED_DICTIONARY = dictionary
    card_builder = None
    if dictionary == "SPANISH":
        settings.MERRIAM_WEBSTER_API_KEY = SPANISH_KEY
        card_builder = cardbuilder.SpanishCardBuilder(word)
    else:
        settings.MERRIAM_WEBSTER_API_KEY = COLLEGIATE_KEY
        card_builder = cardbuilder.CollegiateCardBuilder(word)

    card_builder.addPronunciation()
    card = card_builder.getCard()

    editor = MockEditor()
    card.serialize(editor)

    assert re.match(expected_output, editor.note.fields[settings.PRONUNCIATION_FIELD])
