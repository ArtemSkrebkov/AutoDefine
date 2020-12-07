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
from aqt import mw
from http.client import RemoteDisconnected
from urllib.error import URLError
from xml.etree import ElementTree as ET
import json

import sys

myPath = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, myPath)

import settings
import webbrowser

def _abbreviate_part_of_speech(part_of_speech):
    if part_of_speech in settings.PART_OF_SPEECH_ABBREVIATION.keys():
        part_of_speech = settings.PART_OF_SPEECH_ABBREVIATION[part_of_speech]

    return part_of_speech


def get_preferred_valid_entries(word):
    collegiate_url = "http://www.dictionaryapi.com/api/v1/references/collegiate/xml/" + \
                     urllib.parse.quote_plus(word) + "?key=" + settings.MERRIAM_WEBSTER_API_KEY
    medical_url = "https://www.dictionaryapi.com/api/references/medical/v2/xml/" + \
                  urllib.parse.quote_plus(word) + "?key=" + settings.MERRIAM_WEBSTER_MEDICAL_API_KEY
    all_collegiate_entries = get_entries_from_api(word, collegiate_url)
    all_medical_entries = get_entries_from_api(word, medical_url)

    potential_unified = set()
    if settings.PREFERRED_DICTIONARY == "COLLEGIATE":
        entries = filter_entries_lower_and_potential(word, all_collegiate_entries)
        potential_unified |= entries.potential
        if not entries.valid:
            entries = filter_entries_lower_and_potential(word, all_medical_entries)
            potential_unified |= entries.potential
    else:
        entries = filter_entries_lower_and_potential(word, all_medical_entries)
        potential_unified |= entries.potential
        if not entries.valid:
            entries = filter_entries_lower_and_potential(word, all_collegiate_entries)
            potential_unified |= entries.potential

    if not entries.valid:
        potential = " Potential matches: " + ", ".join(potential_unified)
        tooltip("No entry found in Merriam-Webster dictionary for word '%s'.%s" %
                (word, potential if entries.potential else ""))

    return entries.valid


def filter_entries_lower_and_potential(word, all_entries):
    valid_entries = extract_valid_entries(word, all_entries)
    maybe_entries = set()
    if not valid_entries:
        valid_entries = extract_valid_entries(word, all_entries, True)
        if not valid_entries:
            for entry in all_entries:
                maybe_entries.add(re.sub(r'\[\d+\]$', "", entry.attrib["id"]))
    return ValidAndPotentialEntries(valid_entries, maybe_entries)


def extract_valid_entries(word, all_entries, lower=False):
    valid_entries = []
    for entry in all_entries:
        if lower:
            if entry.attrib["id"][:len(word) + 1].lower() == word.lower() + "[" \
                    or entry.attrib["id"].lower() == word.lower():
                valid_entries.append(entry)
        else:
            if entry.attrib["id"][:len(word) + 1] == word + "[" \
                    or entry.attrib["id"] == word:
                valid_entries.append(entry)
    return valid_entries


ValidAndPotentialEntries = namedtuple('Entries', ['valid', 'potential'])


def get_entries_from_api(word, url):
    if "YOUR_KEY_HERE" in url:
        return []
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:62.0)'
                                                                 ' Gecko/20100101 Firefox/62.0'})
        returned = urllib.request.urlopen(req).read()
        if "Invalid API key" in returned.decode("UTF-8"):
            showInfo("API key '%s' is invalid. Please double-check you are using the key labeled \"Key (Dictionary)\". "
                     "A web browser with the web page that lists your keys will open." % url.split("?key=")[1])
            webbrowser.open("https://www.dictionaryapi.com/account/my-keys.htm")
            return []
        if "Results not found" in returned.decode("UTF-8"):
            return []
        if url.find("xml") != -1:
            etree = ET.fromstring(returned)
            return etree.findall("entry")
        elif url.find("json") != -1:
            content = json.loads(returned)
            return content
    except URLError:
        return []
    except ValueError:
        return []
    except (ET.ParseError, RemoteDisconnected):
        showInfo("Couldn't parse API response for word '%s'. "
                 "Please submit an issue to the AutoDefine GitHub (a web browser window will open)." % word)
        webbrowser.open("https://github.com/z1lc/AutoDefine/issues/new?title=Parse error for word '%s'"
                        "&body=Anki Version: %s%%0APlatform: %s %s%%0AURL: %s%%0AStack Trace: %s"
                        % (word, version, platform.system(), platform.release(), url, traceback.format_exc()), 0, False)
class Card():
    entries = []
    fields = ["", "", "", ""]
    def parse(self, entries) -> list:
        pass

    def getField(self, id):
        # FIXME: out of range
        return self.fields[id]

    def serialize(self, editor):
        if editor.note:
            i = 0
            for field in self.fields:
                if field.find("wav") != -1:
                    editor.note.fields[i] = editor.urlToLink(field)
                else:
                    editor.note.fields[i] = field
                editor.loadNote()
                i += 1

class CardBuilder:
    _card = Card()
    def __init__(self, word):
        self._card.fields[0] = word

    def addDefinition(self):
        self._card.fields[settings.DEFINITION_FIELD] = ""

    def addTranscription(self):
        self._card.fields[settings.PHONETIC_TRANSCRIPTION_FIELD] = ""

    def addPronunciation(self):
        self._card.fields[settings.PRONUNCIATION_FIELD] = ""

    def getCard(self) -> Card:
        return self._card

class CollegiateCardBuilder(CardBuilder):
    def __init__(self, word):
        super().__init__(word)
        self._card.entries = get_preferred_valid_entries(word)

    def addDefinition(self):
        valid_entries = self._card.entries
        insert_queue = {}
        # Add Definition
        definition_array = []
        # Extract the type of word this is
        for entry in valid_entries:
            this_def = entry.find("def")
            if entry.find("fl") is None:
                continue
            fl = entry.find("fl").text
            fl = _abbreviate_part_of_speech(fl)

            this_def.tail = "<b>" + fl + "</b>"  # save the functional label (noun/verb/etc) in the tail

            # the <ssl> tag will contain the word 'obsolete' if the term is not in use anymore. However, for some
            # reason, the tag precedes the <dt> that it is associated with instead of being a child. We need to
            # associate it here so that later we can either remove or keep it regardless.
            previous_was_ssl = False
            for child in this_def:
                # this is a kind of poor way of going about things, but the ElementTree API
                # doesn't seem to offer an alternative.
                if child.text == "obsolete" and child.tag == "ssl":
                    previous_was_ssl = True
                if previous_was_ssl and child.tag == "dt":
                    child.tail = "obsolete"
                    previous_was_ssl = False

            definition_array.append(this_def)

        to_return = ""
        for definition in definition_array:
            last_functional_label = ""
            medical_api_def = definition.findall("./sensb/sens/dt")
            # sometimes there's not a definition directly (dt) but just a usage example (un):
            if len(medical_api_def) == 1 and not medical_api_def[0].text:
                medical_api_def = definition.findall("./sensb/sens/dt/un")
            for dtTag in (definition.findall("dt") + medical_api_def):

                if dtTag.tail == "obsolete":
                    dtTag.tail = ""  # take away the tail word so that when printing it does not show up.
                    if IGNORE_ARCHAIC:
                        continue

                # We don't really care for 'verbal illustrations' or 'usage notes',
                # even though they are occasionally useful.
                for usageNote in dtTag.findall("un"):
                    dtTag.remove(usageNote)
                for verbalIllustration in dtTag.findall("vi"):
                    dtTag.remove(verbalIllustration)

                # Directional cross reference doesn't make sense for us
                for dxTag in dtTag.findall("dx"):
                    for dxtTag in dxTag.findall("dxt"):
                        for dxnTag in dxtTag.findall("dxn"):
                            dxtTag.remove(dxnTag)

                # extract raw XML from <dt>...</dt>
                to_print = ET.tostring(dtTag, "", "xml").strip().decode("utf-8")
                # attempt to remove 'synonymous cross reference tag' and replace with semicolon
                to_print = to_print.replace("<sx>", "; ")
                # attempt to remove 'Directional cross reference tag' and replace with semicolon
                to_print = to_print.replace("<dx>", "; ")
                # remove all other XML tags
                to_print = re.sub('<[^>]*>', '', to_print)
                # remove all colons, since they are usually useless and have been replaced with semicolons above
                to_print = re.sub(':', '', to_print)
                # erase space between semicolon and previous word, if exists, and strip any extraneous whitespace
                to_print = to_print.replace(" ; ", "; ").strip()
                to_print += "\n<br>"

                # add verb/noun/adjective
                if last_functional_label != definition.tail:
                    to_print = definition.tail + " " + to_print
                last_functional_label = definition.tail
                to_return += to_print

            # final cleanup of <sx> tag bs
            to_return = to_return.replace(".</b> ; ", ".</b> ")  # <sx> as first definition after "n. " or "v. "
            to_return = to_return.replace("\n; ", "\n")  # <sx> as first definition after newline
            self._card.fields[settings.DEFINITION_FIELD] = to_return

    def addTranscription(self):
        valid_entries = self._card.entries
        # extract phonetic transcriptions for each entry and label them by part of speech
        all_transcriptions = []
        for entry in valid_entries:
            if entry.find("pr") is not None:
                phonetic_transcription = entry.find("pr").text

                part_of_speech = entry.find("fl").text
                part_of_speech = _abbreviate_part_of_speech(part_of_speech)

                row = f'<b>{part_of_speech}</b> \\{phonetic_transcription}\\'
                all_transcriptions.append(row)

        to_print = "<br>".join(all_transcriptions)

        self._card.fields[settings.PHONETIC_TRANSCRIPTION_FIELD] = to_print

    def addPronunciation(self):
        valid_entries = self._card.entries
        # Parse all unique pronunciations, and convert them to URLs as per http://goo.gl/nL0vte
        all_sounds = []
        for entry in valid_entries:
            for wav in entry.findall("sound/wav"):
                raw_wav = wav.text
                # API-specific URL conversions
                if raw_wav[:3] == "bix":
                    mid_url = "bix"
                elif raw_wav[:2] == "gg":
                    mid_url = "gg"
                elif raw_wav[:1].isdigit():
                    mid_url = "number"
                else:
                    mid_url = raw_wav[:1]
                wav_url = "http://media.merriam-webster.com/soundc11/" + mid_url + "/" + raw_wav
                all_sounds.append(wav_url.strip())

        # We want to make this a non-duplicate list, so that we only get unique sound files.
        all_sounds = list(dict.fromkeys(all_sounds))
        final_pronounce_index = settings.PRONUNCIATION_FIELD
        if mw and False:
            fields = mw.col.models.fieldNames(editor.note.model())
            for field in fields:
                if '🔊' in field:
                    final_pronounce_index = fields.index(field)
                    break

        to_print = ''.join(all_sounds)

        self._card.fields[settings.PRONUNCIATION_FIELD] = to_print

class SpanishCardBuilder(CardBuilder):
    def __init__(self, word):
        super().__init__(word)
        url = "https://dictionaryapi.com/api/v3/references/spanish/json/" + word + "?key=" + settings.MERRIAM_WEBSTER_API_KEY
        entries = get_entries_from_api(word, url)
        if entries:
            self._card.entries = entries
        else:
            self._card.entries = []

    def addDefinition(self):
        entries = self._card.entries
        if entries:
            text = ""
            for entry in entries:
                word_id = entry["meta"]["id"]
                # word_id must contain word we are looking
                # otherwise this is a definition for another word
                word = self._card.fields[0]
                if word_id.find(word) == -1:
                    continue
                fl = entry["fl"]
                if fl:
                    fl = _abbreviate_part_of_speech(fl)
                    text += "<b>" + fl + "</b>\n<br>"

                definitions = []
                sseq_list = entry["def"][0]["sseq"]
                if sseq_list:
                    for sseq in sseq_list:
                        dt = sseq[0][1]["dt"]
                        for elem in dt:
                            if elem[0] == "text":
                                definition = elem[1]
                                if definition.find("sx") != -1:
                                    definition = definition.replace("{sx|", "syn:") \
                                                           .replace("}", ",", 1)

                                definition = definition.replace("{bc}", "")     \
                                                       .replace("{a_link|", "") \
                                                       .replace("}", "")        \
                                                       .replace("{sx|", "")     \
                                                       .replace("|", "")        \
                                                       .strip()
                                definitions.append(definition)
                    for definition in definitions:
                        text += definition + '\n<br>'

            self._card.fields[settings.DEFINITION_FIELD] = text


    def addPronunciation(self):
        # assumption is that it is enough to have
        # pronunciation from the first entry with pronunciation available
        isFound = False
        for entry in self._card.entries:
            if "hwi" in entry and "prs" in entry["hwi"]:
                prs = entry["hwi"]["prs"][0]
                if "sound" in prs:
                    audio = prs["sound"]["audio"]
                    self._card.fields[settings.PRONUNCIATION_FIELD] = "https://media.merriam-webster.com/audio/prons/es/me/wav/" + audio[0] + "/" + audio + ".wav"
                    isFound = True
                    break
        if not isFound:
            self._card.fields[settings.PRONUNCIATION_FIELD] = "not available :("
