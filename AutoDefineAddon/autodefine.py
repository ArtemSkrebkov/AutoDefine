#!/usr/bin/env python
# -*- coding: utf-8 -*-
# AutoDefine Anki Add-on
# Auto-defines words, optionally adding pronunciation and images.
#
# Copyright (c) 2014 - 2019 Robert Sanek    robertsanek.com    rsanek@gmail.com
# https://github.com/z1lc/AutoDefine                      Licensed under GPL v2

import os
from collections import namedtuple

import platform
import re
import traceback
import urllib.error
import urllib.parse
import urllib.request
from anki import version
from anki.hooks import addHook
from aqt import mw
from aqt.utils import showInfo, tooltip
from http.client import RemoteDisconnected
from urllib.error import URLError
from xml.etree import ElementTree as ET

import sys
import os
myPath = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, myPath + '/libs')
import settings
import webbrowser
import cardbuilder

# Collegiate Dictionary API XML documentation: http://goo.gl/LuD83A
# Medical Dictionary API XML documentation: https://goo.gl/akvkbB
#
# http://www.dictionaryapi.com/api/v1/references/collegiate/xml/WORD?key=KEY
# https://www.dictionaryapi.com/api/references/medical/v2/xml/WORD?key=KEY
#
# Rough XML Structure:
# <entry_list>
#   <entry id="word[1]">
#     <sound>
#       <wav>soundfile.wav</wav>
#     </sound>
#     <fl>verb</fl>
#     <def>
#       <sensb>  (medical API only)
#         <sens>  (medical API only)
#           <dt>:actual definition</dt>
#           <ssl>obsolete</ssl> (refers to next <dt>)
#           <dt>:another definition</dt>
#         </sens>  (medical API only)
#       </sensb>  (medical API only)
#     </def>
#   </entry>
#   <entry id="word[2]">
#     ... (same structure as above)
#   </entry>
# </entry_list>


def get_definition(editor,
                   force_pronounce=False,
                   force_definition=False,
                   force_phonetic_transcription=False):
    editor.saveNow(lambda: _get_definition(editor, force_pronounce, force_definition, force_phonetic_transcription))


def get_definition_force_pronunciation(editor):
    get_definition(editor, force_pronounce=True)


def get_definition_force_definition(editor):
    get_definition(editor, force_definition=True)


def get_definition_force_phonetic_transcription(editor):
    get_definition(editor, force_phonetic_transcription=True)


def validate_settings():
    # ideally, we wouldn't have to force people to individually register, but the API limit is just 1000 calls/day.

    if not settings.PREFERRED_DICTIONARY in ["COLLEGIATE", "MEDICAL", "SPANISH"]:
        message = "Setting PREFERRED_DICTIONARY must be set to COLLEGIATE, MEDICAL or SPANISH. Current setting: '%s'" \
                  % settings.PREFERRED_DICTIONARY
        showInfo(message)
        return

    if settings.PREFERRED_DICTIONARY == "MEDICAL" and settings.MERRIAM_WEBSTER_MEDICAL_API_KEY == "YOUR_KEY_HERE":
        message = "The preferred dictionary was set to MEDICAL, but no API key was provided.\n" \
                  "Please register for one at www.dictionaryapi.com."
        showInfo(message)
        webbrowser.open("https://www.dictionaryapi.com/", 0, False)
        return

    if settings.MERRIAM_WEBSTER_API_KEY == "YOUR_KEY_HERE":
        message = "AutoDefine requires use of Merriam-Webster's Collegiate Dictionary with Audio API. " \
                  "To get functionality working:\n" \
                  "1. Go to www.dictionaryapi.com and sign up for an account, requesting access to " \
                  "the Collegiate dictionary. You may also register for the Medical dictionary.\n" \
                  "2. In Anki, go to Tools > Add-Ons. Select AutoDefine, click \"Config\" on the right-hand side " \
                  "and replace YOUR_KEY_HERE with your unique API key.\n"
        showInfo(message)
        webbrowser.open("https://www.dictionaryapi.com/", 0, False)
        return


def _focus_zero_field(editor):
    # no idea why, but sometimes web seems to be unavailable
    if editor.web:
        editor.web.eval("focusField(%d);" % 0)


def _get_word(editor):
    word = ""
    maybe_web = editor.web
    if maybe_web:
        word = maybe_web.selectedText()

    if word is None or word == "":
        maybe_note = editor.note
        if maybe_note:
            word = maybe_note.fields[0]

    word = clean_html(word).strip()
    return word


def _get_definition(editor,
                    force_pronounce=False,
                    force_definition=False,
                    force_phonetic_transcription=False):
    validate_settings()
    word = _get_word(editor)
    if word == "":
        tooltip("AutoDefine: No text found in note fields.")
        return

    insert_queue = {}

    cardBuilder = None
    if settings.PREFERRED_DICTIONARY == "COLLEGIATE" or settings.PREFERRED_DICTIONARY == "MEDICAL":
        cardBuilder = cardbuilder.CollegiateCardBuilder(word)
    elif settings.PREFERRED_DICTIONARY == "SPANISH":
        cardBuilder = cardbuilder.SpanishCardBuilder(word)
    # Add Vocal Pronunciation
    if (not force_definition and not force_phonetic_transcription and settings.PRONUNCIATION_FIELD > -1) or force_pronounce:
        cardBuilder.addPronunciation()

    # Add Phonetic Transcription
    if (not force_definition and not force_pronounce and settings.PHONETIC_TRANSCRIPTION_FIELD > -1) or force_phonetic_transcription:
        cardBuilder.addTranscription()

    # Add Definition
    if (not force_pronounce and not force_phonetic_transcription and settings.DEFINITION_FIELD > -1) or force_definition:
        cardBuilder.addDefinition()

    card = cardBuilder.getCard()
    card.serialize(editor)
    if settings.OPEN_IMAGES_IN_BROWSER:
        webbrowser.open("https://www.google.com/search?q= " + word + "&safe=off&tbm=isch&tbs=isz:lt,islt:xga", 0, False)

    _focus_zero_field(editor)


# via https://stackoverflow.com/a/12982689
def clean_html(raw_html):
    return re.sub(re.compile('<.*?>'), '', raw_html).replace("&nbsp;", " ")


def setup_buttons(buttons, editor):
    both_button = editor.addButton(icon=os.path.join(os.path.dirname(__file__), "images", "icon16.png"),
                                   cmd="AD",
                                   func=get_definition,
                                   tip="AutoDefine Word (%s)" %
                                       ("no shortcut" if settings.PRIMARY_SHORTCUT == "" else settings.PRIMARY_SHORTCUT),
                                   toggleable=False,
                                   label="",
                                   keys=settings.PRIMARY_SHORTCUT,
                                   disables=False)
    define_button = editor.addButton(icon="",
                                     cmd="D",
                                     func=get_definition_force_definition,
                                     tip="AutoDefine: Definition only (%s)" %
                                         ("no shortcut" if settings.DEFINE_ONLY_SHORTCUT == "" else settings.DEFINE_ONLY_SHORTCUT),
                                     toggleable=False,
                                     label="",
                                     keys=settings.DEFINE_ONLY_SHORTCUT,
                                     disables=False)
    pronounce_button = editor.addButton(icon="",
                                        cmd="P",
                                        func=get_definition_force_pronunciation,
                                        tip="AutoDefine: Pronunciation only (%s)" % ("no shortcut"
                                                                                     if settings.PRONOUNCE_ONLY_SHORTCUT == ""
                                                                                     else settings.PRONOUNCE_ONLY_SHORTCUT),
                                        toggleable=False,
                                        label="",
                                        keys=settings.PRONOUNCE_ONLY_SHORTCUT,
                                        disables=False)
    phonetic_transcription_button = editor.addButton(icon="",
                                                     cmd="ə",
                                                     func=get_definition_force_phonetic_transcription,
                                                     tip="AutoDefine: Phonetic Transcription only (%s)" %
                                                         ("no shortcut"
                                                          if settings.PHONETIC_TRANSCRIPTION_ONLY_SHORTCUT == ""
                                                          else settings.PHONETIC_TRANSCRIPTION_ONLY_SHORTCUT),
                                                     toggleable=False,
                                                     label="",
                                                     keys=settings.PHONETIC_TRANSCRIPTION_ONLY_SHORTCUT,
                                                     disables=False)
    buttons.append(both_button)
    if settings.DEDICATED_INDIVIDUAL_BUTTONS:
        buttons.append(define_button)
        buttons.append(pronounce_button)
        buttons.append(phonetic_transcription_button)
    return buttons

if not settings.TEST_MODE:
    addHook("setupEditorButtons", setup_buttons)
    if getattr(mw.addonManager, "getConfig", None):
        config = mw.addonManager.getConfig(__name__)
        if '1 required' in config and 'MERRIAM_WEBSTER_API_KEY' in config['1 required']:
            settings.MERRIAM_WEBSTER_API_KEY = config['1 required']['MERRIAM_WEBSTER_API_KEY']
        else:
            showInfo("AutoDefine: The schema of the configuration has changed in a backwards-incompatible way.\n"
                    "Please remove and re-download the AutoDefine Add-on.")

        if '2 extra' in config:
            extra = config['2 extra']
            if 'DEDICATED_INDIVIDUAL_BUTTONS' in extra:
                settings.DEDICATED_INDIVIDUAL_BUTTONS = extra['DEDICATED_INDIVIDUAL_BUTTONS']
            if 'DEFINITION_FIELD' in extra:
                settings.DEFINITION_FIELD = extra['DEFINITION_FIELD']
            if 'IGNORE_ARCHAIC' in extra:
                settings.IGNORE_ARCHAIC = extra['IGNORE_ARCHAIC']
            if 'MERRIAM_WEBSTER_MEDICAL_API_KEY' in extra:
                settings.MERRIAM_WEBSTER_MEDICAL_API_KEY = extra['MERRIAM_WEBSTER_MEDICAL_API_KEY']
            if 'OPEN_IMAGES_IN_BROWSER' in extra:
                settings.OPEN_IMAGES_IN_BROWSER = extra['OPEN_IMAGES_IN_BROWSER']
            if 'PREFERRED_DICTIONARY' in extra:
                settings.PREFERRED_DICTIONARY = extra['PREFERRED_DICTIONARY']
            if 'PRONUNCIATION_FIELD' in extra:
                settings.PRONUNCIATION_FIELD = extra['PRONUNCIATION_FIELD']
            if 'PHONETIC_TRANSCRIPTION_FIELD' in extra:
                settings.PHONETIC_TRANSCRIPTION_FIELD = extra['PHONETIC_TRANSCRIPTION_FIELD']

        if '3 shortcuts' in config:
            shortcuts = config['3 shortcuts']
            if '1 PRIMARY_SHORTCUT' in shortcuts:
                settings.PRIMARY_SHORTCUT = shortcuts['1 PRIMARY_SHORTCUT']
            if '2 DEFINE_ONLY_SHORTCUT' in shortcuts:
                settings.DEFINE_ONLY_SHORTCUT = shortcuts['2 DEFINE_ONLY_SHORTCUT']
            if '3 PRONOUNCE_ONLY_SHORTCUT' in shortcuts:
                settings.PRONOUNCE_ONLY_SHORTCUT = shortcuts['3 PRONOUNCE_ONLY_SHORTCUT']
            if '4 PHONETIC_TRANSCRIPTION_ONLY_SHORTCUT' in shortcuts:
                settings.PHONETIC_TRANSCRIPTION_ONLY_SHORTCUT = shortcuts['4 PHONETIC_TRANSCRIPTION_ONLY_SHORTCUT']
