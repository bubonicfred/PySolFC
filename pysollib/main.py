## vim:ts=4:et:nowrap
##
##---------------------------------------------------------------------------##
##
## PySol -- a Python Solitaire game
##
## Copyright (C) 2003 Markus Franz Xaver Johannes Oberhumer
## Copyright (C) 2002 Markus Franz Xaver Johannes Oberhumer
## Copyright (C) 2001 Markus Franz Xaver Johannes Oberhumer
## Copyright (C) 2000 Markus Franz Xaver Johannes Oberhumer
## Copyright (C) 1999 Markus Franz Xaver Johannes Oberhumer
## Copyright (C) 1998 Markus Franz Xaver Johannes Oberhumer
## All Rights Reserved.
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program; see the file COPYING.
## If not, write to the Free Software Foundation, Inc.,
## 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
##
## Markus F.X.J. Oberhumer
## <markus@oberhumer.com>
## http://www.oberhumer.com/pysol
##
##---------------------------------------------------------------------------##


# imports
import sys, os, locale
import traceback
import getopt
import gettext

# PySol imports
from mfxutil import destruct, EnvError
from util import CARDSET, DataLoader
from settings import PACKAGE, TOOLKIT, VERSION, SOUND_MOD
from resource import Tile
from gamedb import GI
from app import Application
from pysolaudio import thread, pysolsoundserver
from pysolaudio import AbstractAudioClient, PysolSoundServerModuleClient
from pysolaudio import Win32AudioClient, OSSAudioClient, PyGameAudioClient

# Toolkit imports
from pysoltk import tkversion, wm_withdraw, loadImage
from pysoltk import MfxMessageDialog, MfxExceptionDialog
from pysoltk import TclError, MfxRoot
from pysoltk import PysolProgressBar


# /***********************************************************************
# //
# ************************************************************************/

def fatal_no_cardsets(app):
    app.wm_withdraw()
    d = MfxMessageDialog(app.top, title=PACKAGE + _(" installation error"),
                         text=_('''No %ss were found !!!

Main data directory is:
%s

Please check your %s installation.
''') % (CARDSET, app.dataloader.dir, PACKAGE),
                         bitmap="error", strings=(_("&Quit"),))
    ##raise Exception, "no "+CARDSET+"s found !"


# /***********************************************************************
# //
# ************************************************************************/

def parse_option(argv):
    prog_name = argv[0]
    try:
        optlist, args = getopt.getopt(argv[1:], "g:i:hD:",
                                      ["game=", "gameid=",
                                       "fg=", "foreground=",
                                       "bg=", "background=",
                                       "fn=", "font=",
                                       "theme=",
                                       "french-only",
                                       "noplugins",
                                       "nosound",
                                       "debug=",
                                       "sound-mod=",
                                       "help"])
    except getopt.GetoptError, err:
        print _("%s: %s\ntry %s --help for more information") \
              % (prog_name, err, prog_name)
        return None
    opts = {"help": False,
            "game": None,
            "gameid": None,
            "fg": None,
            "bg": None,
            "fn": None,
            "theme": None,
            "french-only": False,
            "noplugins": False,
            "nosound": False,
            "sound-mod": None,
            "debug": 0,
            }
    for i in optlist:
        if i[0] in ("-h", "--help"):
            opts["help"] = True
        elif i[0] in ("-g", "--game"):
            opts["game"] = i[1]
        elif i[0] in ("-i", "--gameid"):
            opts["gameid"] = i[1]
        elif i[0] in ("--fg", "--foreground"):
            opts["fg"] = i[1]
        elif i[0] in ("--bg", "--background"):
            opts["bg"] = i[1]
        elif i[0] in ("--fn", "--font"):
            opts["fn"] = i[1]
        elif i[0] == "--theme":
            opts["theme"] = i[1]
        elif i[0] == "--french-only":
            opts["french-only"] = True
        elif i[0] == "--noplugins":
            opts["noplugins"] = True
        elif i[0] == "--nosound":
            opts["nosound"] = True
        elif i[0] == "--sound-mod":
            assert i[1] in ('pss', 'pygame', 'oss', 'win')
            opts["sound-mod"] = i[1]
        elif i[0] in ("-D", "--debug"):
            opts["debug"] = i[1]

    if opts["help"]:
        print _("""Usage: %s [OPTIONS] [FILE]
  -g    --game=GAMENAME        start game GAMENAME
  -i    --gameid=GAMEID
        --french-only
  --fg  --foreground=COLOR     foreground color
  --bg  --background=COLOR     background color
  --fn  --font=FONT            default font
        --sound-mod=MOD
        --nosound              disable sound support
        --noplugins            disable load plugins
  -h    --help                 display this help and exit

  FILE - file name of a saved game
  MOD - one of following: pss(default), pygame, oss, win
""") % prog_name
        return None

    if len(args) > 1:
        print _("%s: too many files\ntry %s --help for more information") % (prog_name, prog_name)
        return None
    filename = args and args[0] or None
    if filename and not os.path.isfile(filename):
        print _("%s: invalid file name\ntry %s --help for more information") % (prog_name, prog_name)
        return None
    return opts, filename

# /***********************************************************************
# //
# ************************************************************************/

def pysol_init(app, args):
    # try to create the config directory
    for d in (
        app.dn.config,
        app.dn.savegames,
        os.path.join(app.dn.config, "music"),
        ##os.path.join(app.dn.config, "screenshots"),
        os.path.join(app.dn.config, "tiles"),
        os.path.join(app.dn.config, "tiles", "stretch"),
        os.path.join(app.dn.config, "cardsets"),
        os.path.join(app.dn.config, "plugins"),
        ):
        if not os.path.exists(d):
            try: os.makedirs(d)
            except:
                traceback.print_exc()
                pass

    # init commandline options (undocumented)
    opts = parse_option(args)
    if not opts:
        return 1
        sys.exit(1)
    opts, filename = opts
    if filename:
        app.commandline.loadgame = filename
    app.commandline.game = opts['game']
    if not opts['gameid'] is None:
        try:
            app.commandline.gameid = int(opts['gameid'])
        except:
            print >> sys.stderr, 'WARNING: invalid game id:', opts['gameid']
    try:
        app.debug = int(opts['debug'])
    except:
        print >> sys.stderr, 'invalid argument for debug'

    # init games database
    import games
    if not opts['french-only']:
        #import games.contrib
        import games.ultra
        import games.mahjongg
        import games.special

    # init DataLoader
    f = os.path.join("html", "license.html")
    app.dataloader = DataLoader(args[0], f)

    # try to load plugins
    if not opts["noplugins"]:
        for dir in (os.path.join(app.dataloader.dir, "games"),
                    os.path.join(app.dataloader.dir, "plugins"),
                    app.dn.plugins):
            try:
                app.loadPlugins(dir)
            except:
                pass

    # init toolkit 1)
    top = MfxRoot(className=PACKAGE)
    app.top = top
    app.top_bg = top.cget("bg")
    app.top_palette = [None, None]       # [fg, bg]
    app.top_cursor = top.cget("cursor")

    # load options
    app.loadOptions()

    # init audio 1)
    warn_thread = 0
    warn_pysolsoundserver = 0
    app.audio = None
    sounds = {'pss':     PysolSoundServerModuleClient,
              'pygame':  PyGameAudioClient,
              'oss':     OSSAudioClient,
              'win':     Win32AudioClient}
    if opts["nosound"] or SOUND_MOD == 'none':
        app.audio = AbstractAudioClient()
    elif opts['sound-mod']:
        c = sounds[opts['sound-mod']]
        app.audio = c()
    elif SOUND_MOD == 'auto':
        for c in (PysolSoundServerModuleClient,
                  PyGameAudioClient,
                  OSSAudioClient,
                  Win32AudioClient,
                  AbstractAudioClient):
            try:
                app.audio = c()
            except:
                pass
            else:
                # success
                break
    else:
        c = sounds[SOUND_MOD]
        app.audio = c()
    app.audio.startServer()
    # update sound_mode
    if isinstance(app.audio, PysolSoundServerModuleClient):
        app.opt.sound_mode = 1
    else:
        app.opt.sound_mode = 0

    # init toolkit 2)
    top.initToolkit(app, opts['fg'], opts['bg'], opts['fn'], opts['theme'])

    # check games
    if len(app.gdb.getGamesIdSortedByName()) == 0:
        app.wm_withdraw()
        d = MfxMessageDialog(top, title=PACKAGE + _(" installation error"),
                             text=_('''
No games were found !!!

Main data directory is:
%s

Please check your %s installation.
''') % (app.dataloader.dir, PACKAGE), bitmap="error", strings=(_("&Quit"),))
        return 1

    # init cardsets
    app.initCardsets()
    cardset = None
    c = app.opt.cardset.get(0)
    if c:
        cardset = app.cardset_manager.getByName(c[0])
        if cardset and c[1]:
            cardset.updateCardback(backname=c[1])
    if not cardset:
        cardset = app.cardset_manager.get(0)
    if app.cardset_manager.len() == 0 or not cardset:
        fatal_no_cardsets(app)
        return 3

    # init tiles
    manager = app.tabletile_manager
    tile = Tile()
    tile.color = app.opt.colors['table']
    tile.name = "None"
    tile.filename = None
    manager.register(tile)
    app.initTiles()
    if app.opt.tabletile_name: ### and top.winfo_screendepth() > 8:
        for tile in manager.getAll():
            if app.opt.tabletile_name == tile.basename:
                app.tabletile_index = tile.index
                break

    # init samples and music resources
    app.initSamples()
    app.initMusic()

    # init audio 2)
    app.audio.connectServer(app)
    if not app.audio.CAN_PLAY_SOUND:
        app.opt.sound = 0
    if not opts["nosound"] and not opts['sound-mod'] and pysolsoundserver and not app.audio.connected:
        print PACKAGE + ": could not connect to pysolsoundserver, sound disabled."
        warn_pysolsoundserver = 1
    app.audio.updateSettings()
    # start up the background music
    if app.audio.CAN_PLAY_MUSIC:
        music = app.music_manager.getAll()
        if music:
            app.music_playlist = list(music)[:]
            app.miscrandom.shuffle(app.music_playlist)
            if 1: ## and not app.debug:
                for m in app.music_playlist:
                    if m.name.lower() == "bye_for_now":
                        app.music_playlist.remove(m)
                        app.music_playlist.insert(0, m)
                        break
            app.audio.playContinuousMusic(app.music_playlist)

    # prepare the progress bar
    app.loadImages1()
    if not app.progress_images:
        app.progress_images = (loadImage(app.gimages.logos[0]),
                               loadImage(app.gimages.logos[1]))
    app.wm_withdraw()

    # warn about audio problems
    if (not opts["nosound"] and os.name == "posix" and
        not app.audio and pysolsoundserver is None):
        if 1 and app.opt.sound and re.search(r"linux", sys.platform, re.I):
            warn_pysolsoundserver = 1
            if thread is None:
                warn_thread = 1
        if thread is None:
            print PACKAGE + ": Python thread module not found, sound disabled."
        else:
            print PACKAGE + ": pysolsoundserver module not found, sound disabled."
        sys.stdout.flush()
    if not opts["nosound"]:
        if warn_thread:
            top.update()
            d = MfxMessageDialog(top, title=PACKAGE + _(" installation problem"),
                                 text=_('''\
Your Python installation is compiled without thread support.

Sounds and background music will be disabled.'''),
                                 bitmap="warning", strings=(_("&OK"),))
        elif warn_pysolsoundserver:
            top.update()
            d = MfxMessageDialog(top, title=PACKAGE + _(" installation problem"),
                                 text=_('''\
The pysolsoundserver module was not found.

Sounds and background music will be disabled.'''),
                                 bitmap="warning", strings=(_("&OK"),))

    # create the progress bar
    title = _("Welcome to ") + PACKAGE
    color = app.opt.colors['table']
    if app.tabletile_index > 0:
        color = "#008200"
    app.intro.progress = PysolProgressBar(app, top, title=title, color=color,
                                          images=app.progress_images, norm=1.4)

    # prepare other images
    app.loadImages2()
    app.loadImages3()
    app.loadImages4()

    # load cardset
    progress = app.intro.progress
    if not app.loadCardset(cardset, progress=progress, update=1):
        for cardset in app.cardset_manager.getAll():
            progress.reset()
            if app.loadCardset(cardset, progress=progress, update=1):
                break
        else:
            fatal_no_cardsets(app)
            return 3

    # ok
    return 0


# /***********************************************************************
# //
# ************************************************************************/

def pysol_exit(app):
    # clean up
    if app.audio is not None:
        app.audio.destroy()         # shut down audio
        destruct(app.audio)
    ##app.wm_withdraw()
    if app.canvas is not None:
        app.canvas.destroy()
        destruct(app.canvas)
    if app.toolbar is not None:
        app.toolbar.destroy()
        destruct(app.toolbar)
    if app.menubar is not None:
        destruct(app.menubar)
    top = app.top
    destruct(app)
    app = None
    if top is not None:
        try:
            top.destroy()
        except:
            pass
        destruct(top)


# /***********************************************************************
# // PySol main entry
# ************************************************************************/

def pysol_main(args):
    # create the application
    app = Application()
    r = pysol_init(app, args)
    if r != 0:
        return r
    # let's go - enter the mainloop
    app.mainloop()
##     try:
##         r = pysol_init(app, args)
##         if r != 0:
##             return r
##         # let's go - enter the mainloop
##         app.mainloop()
##     except KeyboardInterrupt, ex:
##         print "Exiting on SIGINT."
##         pass
##     except StandardError, ex:
##         if not app.top:
##             raise
##         t = str(ex.__class__)
##         if str(ex): t = t + ":\n" + str(ex)
##         d = MfxMessageDialog(app.top, title=PACKAGE + " internal error",
##                       text="Internal errror. Please report this bug:\n\n"+t,
##                       strings=("&Quit",), bitmap="error")
    try:
        pysol_exit(app)
    except:
        pass
    return 0


# /***********************************************************************
# // main
# ************************************************************************/

def main(args=None):

    # setup (mainly for JPython)
    if not hasattr(sys, "platform"):
        sys.platform = "unknown"
    if not hasattr(sys, "executable"):
        sys.executable = None
    if not hasattr(os, "defpath"):
        os.defpath = ""

    # check versions
    if sys.platform[:4] != "java":
        if sys.version[:5] < "1.5.2":
            print "%s needs Python 1.5.2 or better (you have %s)" % (PACKAGE, sys.version)
            return 1
    assert len(tkversion) == 4
    if TOOLKIT == "tk":
        import Tkinter
        if tkversion < (8, 0, 0, 0):
            print "%s needs Tcl/Tk 8.0 or better (you have %s)" % (PACKAGE, str(tkversion))
            return 1
        # check that Tkinter bindings are also at version 1.5.2
        if not hasattr(Tkinter.Wm, "wm_aspect") or not hasattr(Tkinter.Canvas, "tag_lower"):
            print "%s: please update the Python-Tk bindings (aka Tkinter) to version 1.5.2 or better" % (PACKAGE,)
            return 1
    # check Python
    if -1 % 13 != 12:
        raise Exception, "-1 % 13 != 12"

    # run it
    return pysol_main(args)

