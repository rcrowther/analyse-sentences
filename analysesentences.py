# -*- coding: utf-8 -*-
#
#  analysesentences.py - Sentence Analysis plugin for Xed
#
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor,
#  Boston, MA 02110-1301, USA.

import gi
gi.require_version('Peas', '1.0')
#gi.require_version('Xed', '3.0')
from gi.repository import GObject, Gio, Gtk, Gdk, Xed

import gettext
gettext.install("xed")

#CURLY_BRACKET_OPEN = "\u201C"
#CURLY_BRACKET_CLOSE = "\u201D"

#DIRECT_SPEECH_START = CURLY_BRACKET_OPEN
#DIRECT_SPEECH_END = CURLY_BRACKET_CLOSE


# Anybodies guess where these are defined. But they work
MENU_PATH = "/MenuBar/ToolsMenu"
#MENU_PATH = "/MenuBar/ViewMenu"


# Must be the window because we need to insert the menu item
class AnalyseSentencesPlugin(GObject.Object, Xed.WindowActivatable):
    __gtype_name__ = "AnalyseSentencesPlugin"

    window = GObject.Property(type=Xed.Window)
    
    # the tag level for each three sentences
    # can be reset when reaches end
    tagLevel = [0, 0, 1, 0, 0, 1, 0, 0, 2]
    tagLevelLen = len(tagLevel)
    
    # index 0 is default
    bracketTypes = [
        ['\u201C', '\u201D', "curly quotes"],
        ['\u0022', '\u0022', "straight quotes"],
        #  guillemet
        ['\u00AB', '\u00BB', "guillemet"]
    ]
    
    def __init__(self):
        GObject.Object.__init__(self)

    def do_activate(self):
        # Insert menu items
        self._insert_menu()
                       
        # The handler is for a signal to clear the view
        self._handlers = [
            None
            ]
            
        # instance variables
        self.countTotal = 0
        self.count9 = 0
        self.tagLevelIdx = 0
        

    def do_deactivate(self):
        # Remove any installed menu items
        self._remove_menu()

        # in case removed when analysing
        view = self.window.get_active_view()
        if view:
            for h in self._handlers:
                if h != None:
                    view.disconnect(h)
        self.handlers = None
        

    def _insert_menu(self):
        manager = self.window.get_ui_manager()

        # Create a new action group
        self._action_group = Gtk.ActionGroup(name="XedAnalyseActions")
        self._action_group.add_actions([
            ("AnalyseAction", None, _("_Analyse"),
            "<Ctrl>3", None,
            self.on_analyse_activate)
            ])
         
        # Insert the action group
        manager.insert_action_group(self._action_group)
        
        self._ui_id = manager.new_merge_id();
        
        manager.add_ui(self._ui_id,
                       MENU_PATH,
                       "AnalyseAction",
                       "AnalyseAction",
                       Gtk.UIManagerItemType.MENUITEM,
                       False)
                       
                               
    def _remove_menu(self):
        # Get the GtkUIManager
        manager = self.window.get_ui_manager()

        # Remove the ui
        manager.remove_ui(self._ui_id)

        # Remove the action group
        manager.remove_action_group(self._action_group)

        # Make sure the manager updates
        manager.ensure_update()        
                
        # Ensure memory freeing?
        self._action_group = None


    # It's not key press event, it....mouse press too
    def connect(self, view):
        #print("connect")
        self._handlers[0] = view.connect(
            #'key-press-event',
            'button-press-event',
            self.on_key_press_event
            )
            
    def disconnect(self, view):
        #print("disconnect")
        #view.disconnect(self._handlers[0])
        #self._handlers[0] = None
        for h in self._handlers:
            if (h != None):
                view.disconnect(h)
                   
    def direct_speech_magic_detection(self, buf):
        # Detect direct speech by magic. 
        # Magic means looking for the first direct speech marks, then 
        # assuming they are used consistently (since preference is too 
        # much of a battle)
        # return: [openMark, closeMark, "name of detected marks"] 
        
        i = 0
        limit = len(self.bracketTypes)
        found = None
        while (i <= limit):
            it = buf.get_start_iter()
            found = it.forward_search(
                        self.bracketTypes[i][0],
                        Gtk.TextSearchFlags.TEXT_ONLY, 
                        None
                        )
            if found:
                 break
            i = i + 1
            
        if (not found):
            i = 0
            infoText = "no quote marks detected, assuming "
        else:
            infoText = "detected "
            
        foundBracketType = self.bracketTypes[i]
        print(infoText + foundBracketType[2])
        return foundBracketType

        
    def _get_custom_tags(self, buf):
        # Ensure custon tags in place. Currently, there are 
        # three.
        tagTable = buf.get_tag_table ()
        tags = [None, None, None]
        tags[0] = tagTable.lookup (
            "narrow_mark"
            ) 
        if tags[0] == None:
            tags[0] = buf.create_tag (
                "narrow_mark",
                background= "LightSalmon"
                )
                
        tags[1] = tagTable.lookup (
            "middle_mark"
            ) 
        if tags[1] == None:
            tags[1] = buf.create_tag (
                "middle_mark",
                background= "LightSkyBlue"
                )
                
        tags[2] = tagTable.lookup (
            "wide_mark"
            ) 
        if tags[2] == None:
            tags[2] = buf.create_tag (
                "wide_mark",
                background= "Violet"
                )
        return tags

    def _textMark(self, buf, it, tags):
        # called on sentence end. Puts a mark in every 
        # nine sentences
        self.countTotal = self.countTotal + 1
        if (self.count9 >= 9):
            self.count9 = 0
        
            # Some kind of mark here
            if (self.tagLevelIdx >= self.tagLevelLen):
                self.tagLevelIdx = 0
                self.widemarkCount = self.widemarkCount + 1
                
            # only way I can think to get a new second iter                
            markStartIt = buf.get_iter_at_offset(it.get_offset() - 1)
            #print("idx: "+ str(self.tagLevel[self.tagLevelIdx]))
            buf.apply_tag(tags[ self.tagLevel[self.tagLevelIdx] ], markStartIt, it)
            self.tagLevelIdx = self.tagLevelIdx + 1

        # update the indecies
        self.count9 = self.count9 + 1
        return
            
    # Menu activate handlers
    def on_analyse_activate(self, action, user_data=None):
        view = self.window.get_active_view()
        #         active = self.view.get_editable() 
        buf = view.get_buffer()
        tags = self._get_custom_tags(buf)
        
        it = buf.get_start_iter()
        limitIt = buf.get_start_iter()
        markStartIt = buf.get_start_iter() 
        
        # init the instance level variables
        self.countTotal = 0
        self.count9 = 0
        self.tagLevelIdx = 0
        self.widemarkCount = 0
        
        # detect quote type
        quoteData = self.direct_speech_magic_detection(buf)
        DIRECT_SPEECH_START = quoteData[0]
        DIRECT_SPEECH_END = quoteData[1]
        
        ## TODO:
        # manual ellipse
        while(True):
            # find any direct speech
            # i.e. find the strech for senteence looks
            # ret form None|[startIt, endIt]
            retSpeech = it.forward_search(
                DIRECT_SPEECH_START,
                Gtk.TextSearchFlags.TEXT_ONLY, 
                None
                )
            
            # If find any, look up to there, else it's what remains
            if retSpeech:
                #print(" speech start found")
                limitIt = retSpeech[0]
            else:
                limitIt = buf.get_end_iter()

                
            ## look for sentences until at limit
            # There's an issue. at a file end, a sentence may not be 
            # found, yet the iter falls short of the endd iter. So test
            # finding return also
            found = it.forward_sentence_end()

            # if this negative, 'it' nearer than limitIt
            while((it.compare(limitIt) < 0) and found):
                self._textMark(buf, it, tags)
                found = it.forward_sentence_end()
                #print("sentence found pos: " + str(it.get_offset()) + "limiit ;" + str(limitIt.get_offset()))

                    
            ## if there was direct speech, skip to end of speech then 
            # look again
            if retSpeech:
                limitIt.forward_char()
                retSpeech = limitIt.forward_search(
                    DIRECT_SPEECH_END,
                    Gtk.TextSearchFlags.TEXT_ONLY, 
                    None
                    )
                if retSpeech:
                    # Won't handle trailing punctuation like '"bingo".'
                    # Or '"Noooo!", shee shrieked.'. But that's a 
                    # limitattion of TextView's parsing ability, too 
                    # much to fix. R.C.
                    it = retSpeech[1]
                    #print(" found speech end" + str(it.get_offset()))
                    self._textMark(buf, it, tags)
                else:
                    it = buf.get_end_iter()
            else:
                # processed until end
                break

        print("sentence count: " + str(self.countTotal))
        print("widemark count: " + str(self.widemarkCount))
        
        #xed_statusbar_flash_message (
        #    XED_STATUSBAR (searchbar->window->priv->statusbar),
        #    searchbar->window->priv->generic_message_cid,
        #    _("No matches found"));
            
        self.connect(view)    
        return Gdk.EVENT_STOP
             
    def on_analyse_deactivate(self):
        view = self.window.get_active_view()
        #         active = self.view.get_editable() 
        buf = view.get_buffer()
        tagTable = buf.get_tag_table ()
                     
        itStart = buf.get_start_iter()  
        itEnd = buf.get_end_iter() 

        tags = [None, None, None]
        tags[0] = tagTable.lookup ("narrow_mark")
        tags[1] = tagTable.lookup ("middle_mark")
        tags[2] = tagTable.lookup ("wide_mark")

        for tag in tags:
            if (tag != None):
                buf.remove_tag (
                    tag,
                    itStart,
                    itEnd 
                    )


    def on_key_press_event(self, view, event):
        #print("keypress1!!!")
        # Ignore CNTRL and ALT 
        if event.state & (Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.MOD1_MASK):
            return False
        #print("keypress2!!!")
        self.on_analyse_deactivate()
        self.disconnect(view)
        
        # the boolean return is to express propagation of this 
        # event. For this usage, I think we will allow further 
        # propagation
        return True
        
##

# ex:ts=4:et:
